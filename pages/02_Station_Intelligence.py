import streamlit as st

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta

st.set_page_config(page_title="Station Intelligence", layout="wide", page_icon="🏢")

# Custom CSS
st.markdown("""
    <style>
    .kpi-box {
        background-color: #1E1E1E;
        color: #E0E0E0;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 10px;
        border: 1px solid #333;
    }
    .cpi-box {
        background-color: #151515;
        padding: 20px;
        border-radius: 8px;
        border: 1px solid #444;
        margin-bottom: 20px;
    }
    .cpi-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid #333; }
    .cpi-row:last-child { border-bottom: none; }
    
    .cat-Low { color: #4CAF50; font-weight: bold; }
    .cat-Moderate { color: #FFC107; font-weight: bold; }
    .cat-High { color: #FF9800; font-weight: bold; }
    .cat-Critical { color: #F44336; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏢 Station Intelligence Module")
st.markdown("Station-level analytical interface and telemetry profiling.")

try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs.get('f_city', 'All')
    f_stn = fs.get('f_stn', 'All Network')
    date_range = fs.get('date_range', [])
    f_ses = sessions.copy()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

# --- FILTERS ---

# Filter logic
f_stn = stations.copy()
if f_city != "All": f_stn = f_stn[f_stn['city'] == f_city]

f_ses = sessions.copy()
days_in_period = (f_ses['date'].max() - f_ses['date'].min()).days if len(f_ses) > 0 else 1
if days_in_period <= 0: days_in_period = 1

# --- AGGREGATIONS ---
stn_agg = f_ses.groupby('station_id').agg(
    Sessions=('session_id', 'count'),
    Revenue=('revenue', 'sum'),
    Energy_Consumed=('energy_kwh', 'sum'),
    duration=('duration_minutes', 'sum'),
    failed=('session_status', lambda x: (x=='Failed').sum()),
    completed=('session_status', lambda x: (x=='Completed').sum())
).reset_index()

merged = f_stn.merge(stn_agg, on='station_id', how='left').fillna(0)

# Calculations
merged['Failure_Rate'] = (merged['failed'] / merged['Sessions'] * 100).fillna(0)
merged['Avg_Session_Duration'] = (merged['duration'] / merged['completed']).fillna(0)
merged['Avg_Revenue_per_Session'] = (merged['Revenue'] / merged['completed']).fillna(0)

active_chg = chargers[chargers['charger_status'] == 'Active'].groupby('station_id').size().reset_index(name='active_chargers')
merged = merged.merge(active_chg, on='station_id', how='left').fillna({'active_chargers': 0})

merged['Utilization_Rate'] = (merged['duration'] / (merged['active_chargers'] * days_in_period * 24 * 60)) * 100
merged['Utilization_Rate'] = merged['Utilization_Rate'].replace([np.inf, -np.inf], 0).fillna(0)

# --- CPI CALCULATION LOGIC ---
# Calculate peak hour demand
def calc_cpi(row, ses_df):
    stn_sessions = ses_df[ses_df['station_id'] == row['station_id']]
    
    if len(stn_sessions) == 0 or row['active_chargers'] == 0:
        return 0, 0, 0, 0, 0, 'Low Pressure'
        
    # 1. Utilization Pressure (0-100) -> 25% avg utilization scales to 100 pressure
    util_pressure = min(100, (row['Utilization_Rate'] / 25.0) * 100)
    
    # 2. Peak-hour demand pressure (0-100)
    # Find busiest hour volume vs average hour volume
    hourly = stn_sessions.groupby('hour').size()
    busiest = hourly.max() if not hourly.empty else 0
    avg_hour = hourly.mean() if not hourly.empty else 1
    # If peak hour is 3x the average, pressure is 100
    peak_ratio = (busiest / avg_hour) if avg_hour > 0 else 0
    peak_pressure = min(100, (peak_ratio / 3.0) * 100)
    
    # 3. Queue/Session pressure (0-100)
    # Measured by raw sessions per charger per day (high volume = turnover = queue risk)
    # 10 sessions per charger per day = 100 pressure
    sessions_per_charger_day = row['Sessions'] / (row['active_chargers'] * days_in_period)
    queue_pressure = min(100, (sessions_per_charger_day / 10.0) * 100)
    
    # 4. Failure pressure (0-100)
    # 5% failure rate = 100 pressure
    fail_pressure = min(100, (row['Failure_Rate'] / 5.0) * 100)
    
    # Weighted CPI Formula
    cpi = (util_pressure * 0.35) + (peak_pressure * 0.25) + (queue_pressure * 0.20) + (fail_pressure * 0.20)
    
    # Categorization
    if cpi <= 25: cat = 'Low Pressure'
    elif cpi <= 50: cat = 'Moderate Pressure'
    elif cpi <= 75: cat = 'High Pressure'
    else: cat = 'Critical Pressure'
        
    return int(util_pressure), int(peak_pressure), int(queue_pressure), int(fail_pressure), int(cpi), cat

cpi_results = merged.apply(lambda r: calc_cpi(r, f_ses), axis=1)
merged['Util_Pres'] = [x[0] for x in cpi_results]
merged['Peak_Pres'] = [x[1] for x in cpi_results]
merged['Queue_Pres'] = [x[2] for x in cpi_results]
merged['Fail_Pres'] = [x[3] for x in cpi_results]
merged['CPI'] = [x[4] for x in cpi_results]
merged['CPI_Category'] = [x[5] for x in cpi_results]


# --- STATION PERFORMANCE TABLE ---
st.subheader("Station Performance Table")
display_cols = ['station_id', 'station_name', 'total_chargers', 'Sessions', 'Revenue', 'Energy_Consumed', 'Utilization_Rate', 'Avg_Session_Duration', 'Failure_Rate', 'CPI', 'CPI_Category']

styled_df = merged[display_cols].copy()
styled_df.columns = ['ID', 'Name', 'Chargers', 'Sessions', 'Revenue ($)', 'Energy (kWh)', 'Util (%)', 'Avg Dur (min)', 'Fail Rate (%)', 'CPI Score', 'Pressure Category']

def color_cpi(val):
    if val == 'Low Pressure': return 'color: #4CAF50; font-weight: bold;'
    if val == 'Moderate Pressure': return 'color: #FFC107; font-weight: bold;'
    if val == 'High Pressure': return 'color: #FF9800; font-weight: bold;'
    if val == 'Critical Pressure': return 'color: #F44336; font-weight: bold;'
    return ''

st.dataframe(styled_df.style.format({
    'Revenue ($)': '${:,.2f}',
    'Energy (kWh)': '{:,.1f}',
    'Util (%)': '{:.1f}%',
    'Avg Dur (min)': '{:.1f}',
    'Fail Rate (%)': '{:.1f}%'
}).map(color_cpi, subset=['Pressure Category']), use_container_width=True, hide_index=True)


st.divider()

# --- STATION PROFILE DEEP DIVE ---
st.subheader("🔍 Detailed Station Profile")
selected_stn = st.selectbox("Select a Station to profile", merged['station_id'].sort_values().tolist())

if selected_stn:
    profile = merged[merged['station_id'] == selected_stn].iloc[0]
    stn_sessions = f_ses[f_ses['station_id'] == selected_stn]
    
    busiest_hour = stn_sessions['start_time'].dt.hour.mode()
    busiest_hour = busiest_hour[0] if len(busiest_hour) > 0 else "N/A"
    
    busiest_day = stn_sessions['start_time'].dt.day_name().mode()
    busiest_day = busiest_day[0] if len(busiest_day) > 0 else "N/A"
        
    class_html_class = f"cat-{profile['CPI_Category'].split()[0]}"

    st.markdown(f"""
    <div style='background-color:#1E1E1E; padding: 25px; border-radius:10px; border-left: 5px solid #888;'>
        <h2 style='margin-top:0;'>{profile['station_name']} ({profile['station_id']})</h2>
        <p style='color:#bbb;'>{profile['city']}, {profile['area']} &nbsp;|&nbsp; Lat: {profile['latitude']}, Lon: {profile['longitude']} &nbsp;|&nbsp; Type: {profile['station_type']}</p>
        <p>Operational Status: <b>Active</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    
    # CPI BLOCK
    cc1, cc2 = st.columns([1, 2])
    with cc1:
        st.markdown(f"""
        <div class='cpi-box'>
            <div style='color:#aaa; font-size: 14px; text-transform:uppercase;'>Charging Pressure Index (CPI)</div>
            <div style='font-size: 48px; font-weight: bold;'>{profile['CPI']} <span style='font-size:16px; font-weight:normal; color:#A0A0A0;'>/100</span></div>
            <div class='{class_html_class}' style='font-size:18px;'>{profile['CPI_Category']}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with cc2:
        st.markdown("<div class='cpi-box'>", unsafe_allow_html=True)
        st.markdown(f"<div class='cpi-row'><span>Utilization Pressure</span><b>{profile['Util_Pres']}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cpi-row'><span>Peak Demand Pressure</span><b>{profile['Peak_Pres']}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cpi-row'><span>Queue/Session Pressure</span><b>{profile['Queue_Pres']}</b></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='cpi-row'><span>Failure Pressure</span><b>{profile['Fail_Pres']}</b></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        with st.expander("CPI Calculation Formula"):
            st.code("""
# Normalized out of 100:
Utilization Pressure = min(100, (Average Utilization / 25%) * 100)
Peak Demand Pressure = min(100, (Peak Hour Volume / Average Hour Volume) / 3 * 100)
Queue Pressure       = min(100, (Sessions per Charger per Day) / 10 * 100)
Failure Pressure     = min(100, (Failure Rate / 5%) * 100)

CPI = (Util * 0.35) + (Peak * 0.25) + (Queue * 0.20) + (Failure * 0.20)

Categories:
0-25:   Low Pressure
26-50:  Moderate Pressure
51-75:  High Pressure
76-100: Critical Pressure
            """)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
        st.metric("Total Chargers", f"{profile['total_chargers']} ({profile['active_chargers']} Active)")
        st.metric("Total Sessions", f"{profile['Sessions']:,.0f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
        st.metric("Total Revenue", f"${profile['Revenue']:,.2f}")
        st.metric("Avg Rev/Session", f"${profile['Avg_Revenue_per_Session']:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
        st.metric("Energy Consumed", f"{profile['Energy_Consumed']:,.1f} kWh")
        st.metric("Avg Session Duration", f"{profile['Avg_Session_Duration']:.1f} min")
        st.markdown("</div>", unsafe_allow_html=True)
    with c4:
        st.markdown("<div class='kpi-box'>", unsafe_allow_html=True)
        st.metric("Average Utilization", f"{profile['Utilization_Rate']:.2f}%")
        st.metric("Failure Rate", f"{profile['Failure_Rate']:.2f}%")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("### Temporal Demand")
    u1, u2, u3 = st.columns(3)
    
    # Calculate peak daily utilization for this station
    if len(stn_sessions) > 0:
        daily_dur = stn_sessions.groupby('date')['duration_minutes'].sum()
        peak_dur = daily_dur.max()
        peak_util = (peak_dur / (profile['active_chargers'] * 24 * 60)) * 100 if profile['active_chargers'] > 0 else 0
    else:
        peak_util = 0
        
    u1.metric("Peak Daily Utilization", f"{peak_util:.2f}%")
    u2.metric("Busiest Hour of Day", f"{busiest_hour}:00" if busiest_hour != "N/A" else "N/A")
    u3.metric("Busiest Day of Week", busiest_day)
