import streamlit as st

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="Geo Intelligence", layout="wide", page_icon="🗺️")

st.markdown("""
    <style>
    .cluster-card { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 10px; }
    .cluster-card.risk { border-left-color: #F44336; }
    .cluster-card.pressure { border-left-color: #FF9800; }
    .cluster-card.underutil { border-left-color: #2196F3; }
    </style>
""", unsafe_allow_html=True)

st.title("🗺️ Geo Intelligence Module")
st.markdown("Spatial analysis of network demand, hardware utilization, and operational pressure.")

try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs.get('f_city', 'All')
    f_stn = fs.get('f_stn', 'All Network')
    date_range = fs.get('date_range', [])
    f_ses = sessions.copy()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

# --- AGGREGATIONS & METRICS ---
days_in_period = (sessions['date'].max() - sessions['date'].min()).days if len(sessions) > 0 else 30
if days_in_period <= 0: days_in_period = 1

stn_agg = sessions.groupby('station_id').agg(
    Sessions=('session_id', 'count'),
    Revenue=('revenue', 'sum'),
    duration=('duration_minutes', 'sum'),
    failed=('session_status', lambda x: (x=='Failed').sum())
).reset_index()

merged = stations.merge(stn_agg, on='station_id', how='left').fillna(0)
merged['Failure_Rate'] = (merged['failed'] / merged['Sessions'] * 100).fillna(0)

active_chg = chargers[chargers['charger_status'] == 'Active'].groupby('station_id').size().reset_index(name='active_chargers')
merged = merged.merge(active_chg, on='station_id', how='left').fillna({'active_chargers': 0})

merged['Utilization'] = (merged['duration'] / (merged['active_chargers'] * days_in_period * 24 * 60)) * 100
merged['Utilization'] = merged['Utilization'].replace([np.inf, -np.inf], 0).fillna(0)

# Simplified CPI calculation for Geo Module
def calc_cpi(row):
    stn_sessions = sessions[sessions['station_id'] == row['station_id']]
    if len(stn_sessions) == 0 or row['active_chargers'] == 0: return 0
    util_pressure = min(100, (row['Utilization'] / 25.0) * 100)
    hourly = stn_sessions.groupby('hour').size()
    busiest = hourly.max() if not hourly.empty else 0
    avg_hour = hourly.mean() if not hourly.empty else 1
    peak_pressure = min(100, ((busiest / avg_hour) / 3.0) * 100) if avg_hour > 0 else 0
    queue_pressure = min(100, ((row['Sessions'] / (row['active_chargers'] * days_in_period)) / 10.0) * 100)
    fail_pressure = min(100, (row['Failure_Rate'] / 5.0) * 100)
    return int((util_pressure * 0.35) + (peak_pressure * 0.25) + (queue_pressure * 0.20) + (fail_pressure * 0.20))

merged['CPI'] = merged.apply(calc_cpi, axis=1)

# --- FILTERS ---



f_util = 0
f_rev = 0
f_fail = 0
f_cpi = 0
f_data = merged.copy()
if f_city != "All": f_data = f_data[f_data['city'] == f_city]
f_data = f_data[f_data['Utilization'] >= f_util]
f_data = f_data[f_data['Revenue'] >= f_rev]
f_data = f_data[f_data['Failure_Rate'] >= f_fail]
f_data = f_data[f_data['CPI'] >= f_cpi]

size_var = 'Utilization'

if len(f_data) == 0:
    st.warning("No stations match these geospatial constraints.")
    st.stop()

# --- INTERACTIVE MAP ---
st.subheader("Network Geography Map")

fig = px.scatter_map(
    f_data, lat="latitude", lon="longitude", size=size_var, color="CPI",
    hover_name="station_name", 
    hover_data={
        "latitude": False, "longitude": False,
        "Sessions": ":,.0f",
        "Revenue": ":$,.2f",
        "Utilization": ":.1f%",
        "Failure_Rate": ":.1f%",
        "CPI": True
    },
    map_style="carto-darkmatter", zoom=5,
    color_continuous_scale="Inferno", size_max=25
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- GEOGRAPHIC SUMMARY (CLUSTERS) ---
st.subheader("Geographic Area Summary")
st.markdown("Macro-level analysis based exclusively on network telemetry limits.")

# Aggregate by Area (which acts as our geographic cluster)
area_agg = merged.groupby('area').agg(
    total_stn=('station_id', 'count'),
    total_ses=('Sessions', 'sum'),
    avg_util=('Utilization', 'mean'),
    avg_cpi=('CPI', 'mean'),
    avg_fail=('Failure_Rate', 'mean')
).reset_index()

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Highest-Demand Areas (Volume & Util)**")
    high_demand = area_agg.sort_values(by='total_ses', ascending=False).head(3)
    for _, row in high_demand.iterrows():
        st.markdown(f"<div class='cluster-card'>📍 <b>{row['area']}</b>: {row['total_ses']:,.0f} sessions | {row['avg_util']:.1f}% Avg Util</div>", unsafe_allow_html=True)
        
    st.markdown("**High-Pressure Areas (CPI > 50)**")
    high_pressure = area_agg[area_agg['avg_cpi'] > 50].sort_values(by='avg_cpi', ascending=False).head(3)
    if not high_pressure.empty:
        for _, row in high_pressure.iterrows():
            st.markdown(f"<div class='cluster-card pressure'>🔥 <b>{row['area']}</b>: Avg CPI {row['avg_cpi']:.1f} | {row['avg_util']:.1f}% Avg Util</div>", unsafe_allow_html=True)
    else:
        st.success("No areas currently exhibiting sustained high pressure.")

with col2:
    st.markdown("**Underutilized Areas (< 2% Avg Util)**")
    underutil = area_agg[area_agg['avg_util'] < 2.0].sort_values(by='avg_util', ascending=True).head(3)
    if not underutil.empty:
        for _, row in underutil.iterrows():
            st.markdown(f"<div class='cluster-card underutil'>🧊 <b>{row['area']}</b>: {row['avg_util']:.1f}% Avg Util | {row['total_ses']:,.0f} sessions</div>", unsafe_allow_html=True)
    else:
        st.success("No severely underutilized areas detected.")
        
    st.markdown("**Operational-Risk Clusters (Failure Rate > 3%)**")
    risk = area_agg[area_agg['avg_fail'] > 3.0].sort_values(by='avg_fail', ascending=False).head(3)
    if not risk.empty:
        for _, row in risk.iterrows():
            st.markdown(f"<div class='cluster-card risk'>🚨 <b>{row['area']}</b>: {row['avg_fail']:.1f}% Avg Failure Rate</div>", unsafe_allow_html=True)
    else:
        st.success("No clustered operational risks detected.")
