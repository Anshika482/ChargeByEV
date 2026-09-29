import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Capacity Expansion Simulator", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    .state-card { background-color: #1a1a1a; padding: 20px; border-radius: 8px; border: 1px solid #333; height: 100%; }
    .header-current { color: #FF9800; margin-top: 0; }
    .header-scenario { color: #4CAF50; margin-top: 0; }
    .metric-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #333; font-size: 16px; }
    .metric-row:last-child { border-bottom: none; }
    .cpi-badge { background-color: #333; padding: 4px 8px; border-radius: 4px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏗️ Capacity Expansion Simulator")
st.markdown("Stress-test hardware expansion scenarios against historical operational pressure.")

@st.cache_data
def load_data():
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    
    sessions['start_time'] = pd.to_datetime(sessions['start_time'])
    sessions['date'] = sessions['start_time'].dt.date
    sessions['hour'] = sessions['start_time'].dt.hour
    
    return stations, chargers, sessions

try:
    stations, chargers, sessions = load_data()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

# Aggregate parameters
days_in_period = (sessions['start_time'].max() - sessions['start_time'].min()).days if len(sessions)>0 else 30
if days_in_period <= 0: days_in_period = 1

stn_agg = sessions.groupby('station_id').agg(
    total_sessions=('session_id', 'count'),
    revenue=('revenue', 'sum'),
    duration=('duration_minutes', 'sum'),
    failed=('session_status', lambda x: (x=='Failed').sum())
).reset_index()

active_chg = chargers[chargers['charger_status'] == 'Active'].groupby('station_id').size().reset_index(name='active_chargers')
merged = stations.merge(stn_agg, on='station_id', how='left').fillna(0)
merged = merged.merge(active_chg, on='station_id', how='left').fillna({'active_chargers': 0})

st.sidebar.header("Scenario Controls")
stn_list = sorted(merged['station_id'].unique().tolist())
selected_stn = st.sidebar.selectbox("Select Station to Simulate", stn_list)

add_chargers = st.sidebar.slider("Add Chargers to Station (+)", 1, 5, 2)

if not selected_stn:
    st.stop()
    
stn_data = merged[merged['station_id'] == selected_stn].iloc[0]
stn_sessions = sessions[sessions['station_id'] == selected_stn]

curr_chargers = max(1, stn_data['active_chargers'])
curr_util = (stn_data['duration'] / (curr_chargers * days_in_period * 24 * 60)) * 100

hourly = stn_sessions.groupby('hour').size()
busiest = hourly.max() if not hourly.empty else 0
avg_hour = hourly.mean() if not hourly.empty else 1
peak_ratio = busiest / avg_hour if avg_hour > 0 else 0

daily_dur = stn_sessions.groupby('date')['duration_minutes'].sum()
peak_dur = daily_dur.max() if not daily_dur.empty else 0
curr_peak_util = (peak_dur / (curr_chargers * 24 * 60)) * 100

curr_sessions_per_chg = stn_data['total_sessions'] / curr_chargers
curr_fail_rate = (stn_data['failed'] / stn_data['total_sessions'] * 100) if stn_data['total_sessions'] > 0 else 0
curr_queue_proxy = stn_data['total_sessions'] / (curr_chargers * days_in_period)

def calc_cpi(util, p_ratio, q_proxy, fail_rate):
    u_p = min(100, (util / 25.0) * 100)
    p_p = min(100, (p_ratio / 3.0) * 100)
    q_p = min(100, (q_proxy / 10.0) * 100)
    f_p = min(100, (fail_rate / 5.0) * 100)
    return int((u_p * 0.35) + (p_p * 0.25) + (q_p * 0.20) + (f_p * 0.20))

curr_cpi = calc_cpi(curr_util, peak_ratio, curr_queue_proxy, curr_fail_rate)
max_rev_cap = stn_data['revenue'] / (curr_util/100) if curr_util > 0 else 0

st.subheader(f"Simulating: {stn_data['station_name']} ({selected_stn})")

# --- SCENARIO CALCS ---
scen_chargers = curr_chargers + add_chargers
scen_util = (stn_data['duration'] / (scen_chargers * days_in_period * 24 * 60)) * 100
scen_peak_util = (peak_dur / (scen_chargers * 24 * 60)) * 100
scen_queue_proxy = stn_data['total_sessions'] / (scen_chargers * days_in_period)
scen_sessions_per_chg = stn_data['total_sessions'] / scen_chargers
scen_cpi = calc_cpi(scen_util, peak_ratio, scen_queue_proxy, curr_fail_rate)
scen_rev_cap = max_rev_cap * (scen_chargers / curr_chargers)

def format_diff(curr, scen, inverse=False):
    diff = scen - curr
    color = "green"
    if diff > 0 and inverse: color = "red"
    if diff < 0 and not inverse: color = "red"
    if diff == 0: color = "gray"
    sign = "+" if diff > 0 else ""
    return f"<span style='color:{color}; font-size:14px; margin-left: 8px;'>({sign}{diff:,.1f})</span>"

col1, col2 = st.columns(2)

with col1:
    st.markdown("<div class='state-card'>", unsafe_allow_html=True)
    st.markdown("<h3 class='header-current'>Historical Baseline</h3>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Total Chargers</span><b>{int(curr_chargers)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Average Utilization</span><b>{curr_util:.1f}%</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Peak Daily Utilization</span><b>{curr_peak_util:.1f}%</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Est. Queue Proxy (Sessions/Day)</span><b>{curr_queue_proxy:.1f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Total Sessions per Charger</span><b>{curr_sessions_per_chg:,.0f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Revenue Capacity (Max)</span><b>${max_rev_cap:,.0f}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Charging Pressure Index (CPI)</span><b class='cpi-badge'>{curr_cpi}</b></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
with col2:
    st.markdown("<div class='state-card'>", unsafe_allow_html=True)
    st.markdown("<h3 class='header-scenario'>Scenario Estimate (+" + str(add_chargers) + " Chargers)</h3>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Total Chargers</span><b>{int(scen_chargers)} {format_diff(curr_chargers, scen_chargers)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Average Utilization</span><b>{scen_util:.1f}% {format_diff(curr_util, scen_util, inverse=True)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Peak Daily Utilization</span><b>{scen_peak_util:.1f}% {format_diff(curr_peak_util, scen_peak_util, inverse=True)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Est. Queue Proxy (Sessions/Day)</span><b>{scen_queue_proxy:.1f} {format_diff(curr_queue_proxy, scen_queue_proxy, inverse=True)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Total Sessions per Charger</span><b>{scen_sessions_per_chg:,.0f} {format_diff(curr_sessions_per_chg, scen_sessions_per_chg, inverse=True)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Revenue Capacity (Max)</span><b>${scen_rev_cap:,.0f} {format_diff(max_rev_cap, scen_rev_cap)}</b></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-row'><span>Charging Pressure Index (CPI)</span><b class='cpi-badge' style='color:#4CAF50;'>{scen_cpi} {format_diff(curr_cpi, scen_cpi, inverse=True)}</b></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.write("")
with st.expander("ℹ️ Transparency: Simulation Assumptions & Limitations"):
    st.markdown("""
    **IMPORTANT:** This simulation strictly outputs a mathematically deterministic "Scenario Estimate." It does **NOT** attempt to predict actual future human behavior, elasticity of demand, localized grid constraints, or competitor pricing responses. 
    
    The recalculations are based entirely on the following fixed assumptions:
    
    1. **Static Demand Model:** Total session volume and gross energy consumption remain completely constant. We assume adding hardware primarily relieves existing queue pressure rather than instantly inducing new baseline traffic.
    2. **Linear Load Balancing:** All newly simulated chargers instantly inherit an exactly equal share of the station's historical traffic (simulating 100% efficient load balancing).
    3. **Constant Hardware Reliability:** The historical hardware failure rate is projected forward as a static percentage (it is not modeled to improve or degrade).
    4. **Queue Proxy:** Calculated strictly as `Total Sessions / (Active Chargers * Days)`. It represents raw turnover velocity/friction, not a literal real-time queuing time of cars waiting.
    5. **Revenue Capacity:** Calculated as a linear theoretical projection of current revenue scaled to 100% hardware uptime (this is a mathematical ceiling, not a realistic financial forecast).
    """)
