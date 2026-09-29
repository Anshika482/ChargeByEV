import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Demand Intelligence", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    .kpi-card { background-color: #1E1E1E; padding: 15px; border-radius: 5px; border-left: 4px solid #00BCD4; margin-bottom: 10px; }
    .compare-table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 16px; }
    .compare-table th, .compare-table td { border: 1px solid #333; padding: 12px; text-align: left; }
    .compare-table th { background-color: #222; color: #00BCD4; }
    .compare-table tr:nth-child(even) { background-color: #1a1a1a; }
    </style>
""", unsafe_allow_html=True)

st.title("📈 Demand Intelligence Module")
st.markdown("Analyze network demand patterns, peak windows, and spatial-temporal charging behavior.")

@st.cache_data
def load_data():
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    
    sessions['start_time'] = pd.to_datetime(sessions['start_time'])
    sessions['end_time'] = pd.to_datetime(sessions['end_time'])
    sessions['date'] = sessions['start_time'].dt.date
    sessions['hour'] = sessions['start_time'].dt.hour
    sessions['day_of_week'] = sessions['start_time'].dt.day_name()
    sessions['month'] = sessions['start_time'].dt.month_name()
    sessions['is_weekend'] = sessions['start_time'].dt.dayofweek >= 5
    
    return stations, chargers, sessions

try:
    stations, chargers, sessions = load_data()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

sessions = sessions.merge(stations[['station_id', 'city']], on='station_id', how='left')

# --- SIDEBAR FILTERS ---
st.sidebar.header("Global Filters")
min_d = sessions['date'].min()
max_d = sessions['date'].max()

date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)

stn_list = ["All Network"] + sorted(stations['station_id'].unique().tolist())
f_stn = st.sidebar.selectbox("Filter by Station", stn_list)

# Apply filters
if len(date_range) == 2:
    start_d, end_d = date_range
    f_ses = sessions[(sessions['date'] >= start_d) & (sessions['date'] <= end_d)]
else:
    f_ses = sessions

if f_stn != "All Network":
    f_ses = f_ses[f_ses['station_id'] == f_stn]

if len(f_ses) == 0:
    st.warning("No data available for these filters.")
    st.stop()

# --- TOP KPI METRICS ---
hourly_counts = f_ses.groupby('hour').size()
peak_hour = hourly_counts.idxmax() if not hourly_counts.empty else 0

day_counts = f_ses.groupby('day_of_week').size()
peak_day = day_counts.idxmax() if not day_counts.empty else "N/A"

if f_stn == "All Network":
    stn_counts = f_ses.groupby('station_id').size()
    peak_station = stn_counts.idxmax() if not stn_counts.empty else "N/A"
else:
    peak_station = f_stn
    
city_counts = f_ses.groupby('city').size()
peak_city = city_counts.idxmax() if not city_counts.empty else "N/A"

total_hours = (f_ses['start_time'].max() - f_ses['start_time'].min()).total_seconds() / 3600
if total_hours <= 0: total_hours = 1
avg_sessions_per_hour = len(f_ses) / total_hours

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.markdown(f"<div class='kpi-card'><b>Peak Hour</b><br><span style='font-size:24px; color:#fff;'>{peak_hour}:00</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='kpi-card'><b>Peak Day</b><br><span style='font-size:24px; color:#fff;'>{peak_day}</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='kpi-card'><b>Peak Station</b><br><span style='font-size:24px; color:#fff;'>{peak_station}</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='kpi-card'><b>Peak City</b><br><span style='font-size:24px; color:#fff;'>{peak_city}</span></div>", unsafe_allow_html=True)
with c5: st.markdown(f"<div class='kpi-card'><b>Avg Sessions / Hr</b><br><span style='font-size:24px; color:#fff;'>{avg_sessions_per_hour:.1f}</span></div>", unsafe_allow_html=True)

st.divider()

# --- IDENTIFY PEAK DEMAND WINDOW (Statistical Rule) ---
hourly_avg = f_ses.groupby('hour').size().reset_index(name='count')
mean_vol = hourly_avg['count'].mean()
std_vol = hourly_avg['count'].std()
threshold = mean_vol + std_vol

peak_hours = hourly_avg[hourly_avg['count'] > threshold]['hour'].tolist()

blocks = []
if peak_hours:
    peak_hours.sort()
    current_block = [peak_hours[0]]
    for h in peak_hours[1:]:
        if h == current_block[-1] + 1:
            current_block.append(h)
        else:
            blocks.append(current_block)
            current_block = [h]
    blocks.append(current_block)

block_strs = []
for b in blocks:
    if len(b) > 1:
        block_strs.append(f"{b[0]}:00-{b[-1]+1}:00")
    else:
        block_strs.append(f"{b[0]}:00-{b[0]+1}:00")

peak_window_str = ", ".join(block_strs) if block_strs else "No peaks detected"

st.subheader("Statistical Peak Demand Windows")

p1, p2, p3, p4 = st.columns(4)
p1.metric("Peak Demand Window(s)", peak_window_str)
p2.metric("Peak Demand Day", peak_day)
p3.metric("Peak Demand Station", peak_station)
p4.metric("Peak Demand Hour", f"{peak_hour}:00")

with st.expander("ℹ️ Transparency: Statistical Rule for Peak Window Identification"):
    st.markdown(f"""
    **Algorithm:** A "Peak Demand Window" is defined as any continuous block of hours where the charging session volume strictly exceeds the **Mean + 1 Standard Deviation**.
    
    - **Mean Hourly Volume:** {mean_vol:.1f} sessions
    - **Standard Deviation:** {std_vol:.1f} sessions
    - **Calculated Threshold:** > {threshold:.1f} sessions
    
    *Any hour crossing {threshold:.1f} sessions is flagged as Peak.*
    """)

st.divider()

# --- HEATMAP ---
st.subheader("Interactive Demand Heatmap")
heatmap_data = f_ses.groupby(['day_of_week', 'hour']).size().reset_index(name='sessions')
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
heatmap_data['day_of_week'] = pd.Categorical(heatmap_data['day_of_week'], categories=days_order, ordered=True)
heatmap_data = heatmap_data.sort_values(['day_of_week', 'hour'])

fig_heat = px.density_heatmap(
    heatmap_data, x="hour", y="day_of_week", z="sessions", 
    color_continuous_scale="Inferno", nbinsx=24,
    labels={'hour': 'Hour of Day (0-23)', 'day_of_week': 'Day of Week', 'sessions': 'Sessions'}
)
fig_heat.update_layout(yaxis={'categoryorder':'array', 'categoryarray':days_order[::-1]})
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# --- DIMENSIONAL ANALYSIS ---
st.subheader("Dimensional Demand Analysis")
tab1, tab2, tab3 = st.tabs(["Weekday vs Weekend", "Vehicle Type", "Monthly Trend"])

with tab1:
    wd_we = f_ses.groupby('is_weekend').size().reset_index(name='count')
    wd_we['Type'] = wd_we['is_weekend'].map({False: 'Weekday', True: 'Weekend'})
    fig_wd = px.pie(wd_we, values='count', names='Type', hole=0.5, color_discrete_sequence=['#4CAF50', '#00BCD4'])
    st.plotly_chart(fig_wd, use_container_width=True)

with tab2:
    veh = f_ses.groupby('vehicle_type').size().reset_index(name='count').sort_values('count', ascending=True)
    fig_v = px.bar(veh, y='vehicle_type', x='count', orientation='h', color_discrete_sequence=['#9C27B0'])
    st.plotly_chart(fig_v, use_container_width=True)
    
with tab3:
    monthly = f_ses.groupby(f_ses['start_time'].dt.to_period("M")).size().reset_index(name='count')
    monthly['start_time'] = monthly['start_time'].astype(str)
    fig_m = px.line(monthly, x='start_time', y='count', markers=True, color_discrete_sequence=['#E91E63'])
    st.plotly_chart(fig_m, use_container_width=True)

st.divider()

# --- PEAK VS OFF-PEAK COMPARISON ---
st.subheader("Peak vs Off-Peak Operational Pressure")

f_ses['is_peak'] = f_ses['hour'].isin(peak_hours)

peak_ses = f_ses[f_ses['is_peak']]
off_ses = f_ses[~f_ses['is_peak']]

active_c = chargers[chargers['charger_status'] == 'Active']
if f_stn != "All Network":
    active_c = active_c[active_c['station_id'] == f_stn]
num_chargers = len(active_c)
if num_chargers == 0: num_chargers = 1

days_in_period = (f_ses['date'].max() - f_ses['date'].min()).days if len(f_ses) > 0 else 1
if days_in_period <= 0: days_in_period = 1

peak_hours_per_day = len(peak_hours) if len(peak_hours) > 0 else 0
off_hours_per_day = 24 - peak_hours_per_day

peak_capacity_minutes = num_chargers * days_in_period * peak_hours_per_day * 60
off_capacity_minutes = num_chargers * days_in_period * off_hours_per_day * 60

peak_util = (peak_ses['duration_minutes'].sum() / peak_capacity_minutes * 100) if peak_capacity_minutes > 0 else 0
off_util = (off_ses['duration_minutes'].sum() / off_capacity_minutes * 100) if off_capacity_minutes > 0 else 0

comp_data = {
    'Metric': ['Total Sessions', 'Energy Consumed', 'Total Revenue', 'Average Hardware Utilization', 'Avg Session Duration'],
    'Peak Hours': [
        f"{len(peak_ses):,}", 
        f"{peak_ses['energy_kwh'].sum():,.1f} kWh", 
        f"${peak_ses['revenue'].sum():,.2f}", 
        f"{peak_util:.2f}%", 
        f"{peak_ses['duration_minutes'].mean():.1f} min" if len(peak_ses)>0 else "0.0 min"
    ],
    'Off-Peak Hours': [
        f"{len(off_ses):,}", 
        f"{off_ses['energy_kwh'].sum():,.1f} kWh", 
        f"${off_ses['revenue'].sum():,.2f}", 
        f"{off_util:.2f}%", 
        f"{off_ses['duration_minutes'].mean():.1f} min" if len(off_ses)>0 else "0.0 min"
    ]
}

comp_df = pd.DataFrame(comp_data)
st.markdown("""
<table class="compare-table">
    <tr>
        <th>Operational Metric</th>
        <th>Peak Windows <span style="font-weight:normal; color:#aaa;">(Statistically flagged hours)</span></th>
        <th>Off-Peak Windows</th>
    </tr>
""", unsafe_allow_html=True)

for i, row in comp_df.iterrows():
    st.markdown(f"<tr><td><b>{row['Metric']}</b></td><td>{row['Peak Hours']}</td><td>{row['Off-Peak Hours']}</td></tr>", unsafe_allow_html=True)

st.markdown("</table>", unsafe_allow_html=True)
