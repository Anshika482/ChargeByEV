import streamlit as st

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import timedelta

st.set_page_config(page_title="ChargeByEV Command Center", layout="wide", page_icon="🌐")

# Custom CSS for dark NOC feel
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E1E1E;
        color: #E0E0E0;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 15px;
    }
    .metric-card.negative { border-left-color: #F44336; }
    .metric-card.neutral { border-left-color: #FFC107; }
    .alert-card {
        color: #E0E0E0 !important;
        background-color: #2b1111; color: #E0E0E0 !important;
        padding: 10px;
        border-radius: 5px;
        border-left: 4px solid #F44336;
        margin-bottom: 10px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🌐 ChargeByEV Network Command Center")
st.markdown("Global Network Operations & Telemetry")

try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs.get('f_city', 'All')
    f_stn = fs.get('f_stn', 'All Network')
    date_range = fs.get('date_range', [])
    f_ses = sessions.copy()
except Exception as e:
    st.error(f"Data files not found. Error: {str(e)}")
    st.stop()

# --- Date Filtering for Periods ---
max_date = sessions['start_time'].max()
current_start = max_date - timedelta(days=30)
prev_start = current_start - timedelta(days=30)

current_sessions = sessions[(sessions['start_time'] > current_start) & (sessions['start_time'] <= max_date)]
prev_sessions = sessions[(sessions['start_time'] > prev_start) & (sessions['start_time'] <= current_start)]

# Metrics Calculation
def calc_metrics(df, stns, chgrs):
    metrics = {}
    metrics['Total Charging Sessions'] = len(df)
    metrics['Total Energy Consumed (kWh)'] = df['energy_kwh'].sum()
    metrics['Total Revenue'] = df['revenue'].sum()
    
    completed = df[df['session_status'] == 'Completed']
    metrics['Average Session Duration'] = completed['duration_minutes'].mean() if len(completed)>0 else 0
    metrics['Average Energy per Session'] = completed['energy_kwh'].mean() if len(completed)>0 else 0
    
    failed = df[df['session_status'] == 'Failed']
    metrics['Session Failure Rate'] = (len(failed) / len(df)) * 100 if len(df)>0 else 0
    
    active_chargers = len(chgrs[chgrs['charger_status'] == 'Active'])
    days_in_period = (df['start_time'].max() - df['start_time'].min()).days if len(df) > 0 else 30
    if days_in_period == 0: days_in_period = 1
    total_possible_hours = active_chargers * days_in_period * 24
    total_used_hours = df['duration_minutes'].sum() / 60
    metrics['Network Utilization Rate'] = (total_used_hours / total_possible_hours) * 100 if total_possible_hours > 0 else 0
    
    active_station_ids = chgrs[chgrs['charger_status'] == 'Active']['station_id'].unique()
    metrics['Active Stations'] = len(stns[stns['station_id'].isin(active_station_ids)])
    metrics['Active Chargers'] = active_chargers
    
    return metrics

curr_m = calc_metrics(current_sessions, stations, chargers)
prev_m = calc_metrics(prev_sessions, stations, chargers)

# Helper to render metric
def render_metric(label, curr, prev, format_str, invert_color=False):
    pct_change = ((curr - prev) / prev) * 100 if prev != 0 else 0
    
    if pct_change > 0:
        indicator = "🟢" if not invert_color else "🔴"
        color_class = "positive" if not invert_color else "negative"
        arrow = "↑"
    elif pct_change < 0:
        indicator = "🔴" if not invert_color else "🟢"
        color_class = "negative" if not invert_color else "positive"
        arrow = "↓"
    else:
        indicator = "⚪"
        color_class = "neutral"
        arrow = "-"
        
    st.markdown(f"""
    <div class="metric-card {color_class}">
        <div style="color:#A0A0A0; font-size:14px; text-transform:uppercase;">{label}</div>
        <div style="font-size:24px; font-weight:bold; color:#FFFFFF;">{format_str.format(curr)}</div>
        <div style="font-size:12px; margin-top:5px; color:#B0BEC5;">
            {indicator} {abs(pct_change):.1f}% {arrow} vs prev 30d ({format_str.format(prev)})
        </div>
    </div>
    """, unsafe_allow_html=True)

# Layout KPIs
st.subheader("OVERVIEW (Last 30 Days)")
c1, c2, c3, c4, c5 = st.columns(5)
with c1: render_metric("Total Sessions", curr_m['Total Charging Sessions'], prev_m['Total Charging Sessions'], "{:,.0f}")
with c2: render_metric("Energy (kWh)", curr_m['Total Energy Consumed (kWh)'], prev_m['Total Energy Consumed (kWh)'], "{:,.0f}")
with c3: render_metric("Revenue", curr_m['Total Revenue'], prev_m['Total Revenue'], "${:,.2f}")
with c4: render_metric("Avg Duration (m)", curr_m['Average Session Duration'], prev_m['Average Session Duration'], "{:.1f}")
with c5: render_metric("Avg Energy (kWh)", curr_m['Average Energy per Session'], prev_m['Average Energy per Session'], "{:.1f}")

c1, c2, c3, c4, c5 = st.columns(5)
with c1: render_metric("Utilization Rate", curr_m['Network Utilization Rate'], prev_m['Network Utilization Rate'], "{:.2f}%")
with c2: render_metric("Failure Rate", curr_m['Session Failure Rate'], prev_m['Session Failure Rate'], "{:.2f}%", invert_color=True)
with c3: render_metric("Active Stations", curr_m['Active Stations'], prev_m['Active Stations'], "{:,.0f}")
with c4: render_metric("Active Chargers", curr_m['Active Chargers'], prev_m['Active Chargers'], "{:,.0f}")
with c5: 
    # NETWORK HEALTH SCORE
    fail_penalty = curr_m['Session Failure Rate'] * 5
    util = curr_m['Network Utilization Rate']
    util_penalty = (util - 80) if util > 80 else (5 if util < 2 else 0)
    
    offline_chg = len(chargers[chargers['charger_status'] == 'Offline'])
    offline_penalty = (offline_chg / len(chargers)) * 100 if len(chargers) > 0 else 0
    
    health_score = max(0, 100 - fail_penalty - util_penalty - offline_penalty)
    
    if health_score >= 90: h_color, h_text = "#4CAF50", "EXCELLENT"
    elif health_score >= 75: h_color, h_text = "#FFC107", "FAIR"
    else: h_color, h_text = "#F44336", "CRITICAL"
    
    st.markdown(f"""
    <div style="background-color: #1a1a1a; color: #E0E0E0 !important; color: #E0E0E0; border: 1px solid #333; padding: 15px; border-radius: 8px; text-align:center;">
        <div style="color:#A0A0A0; font-size:12px;">NETWORK HEALTH SCORE</div>
        <div style="font-size:32px; font-weight:bold; color:{h_color}">{health_score:.1f}/100</div>
        <div style="font-size:12px; color:{h_color}">{h_text}</div>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("ℹ️ Health Formula"):
        st.caption("100 (Base) - (Failure Rate × 5) - (Utilization Penalty) - (% Offline Chargers)")

st.divider()

# Visualizations
st.subheader("TREND ANALYSIS")

trend_start = max_date - timedelta(days=90)
trend_data = sessions[sessions['start_time'] >= trend_start]
daily = trend_data.groupby('date').agg(
    revenue=('revenue', 'sum'),
    energy=('energy_kwh', 'sum'),
    sessions=('session_id', 'count'),
    duration=('duration_minutes', 'sum')
).reset_index()

active_c = len(chargers[chargers['charger_status'] == 'Active'])
daily['utilization'] = (daily['duration'] / (active_c * 24 * 60)) * 100

t1, t2 = st.columns(2)
with t1:
    fig1 = px.area(daily, x='date', y='revenue', title="1. Daily Revenue Trend (Last 90d)", color_discrete_sequence=['#4CAF50'])
    st.plotly_chart(fig1, use_container_width=True)
with t2:
    fig2 = px.bar(daily, x='date', y='energy', title="2. Daily Energy Consumption (kWh)", color_discrete_sequence=['#2196F3'])
    st.plotly_chart(fig2, use_container_width=True)

t3, t4 = st.columns(2)
with t3:
    fig3 = px.line(daily, x='date', y='sessions', title="3. Charging Sessions Trend", color_discrete_sequence=['#FF9800'])
    st.plotly_chart(fig3, use_container_width=True)
with t4:
    fig4 = px.line(daily, x='date', y='utilization', title="4. Network Utilization Trend (%)", color_discrete_sequence=['#9C27B0'])
    st.plotly_chart(fig4, use_container_width=True)

t5, t6 = st.columns(2)

sessions['hour'] = sessions['start_time'].dt.hour
sessions['dow'] = sessions['start_time'].dt.day_name()
days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

with t5:
    hourly = sessions.groupby('hour').size().reset_index(name='count')
    fig5 = px.bar(hourly, x='hour', y='count', title="5. Sessions by Hour of Day", color_discrete_sequence=['#00BCD4'])
    st.plotly_chart(fig5, use_container_width=True)
with t6:
    dow = sessions.groupby('dow').size().reindex(sessions.groupby('dow').size().index.astype(pd.CategoricalDtype(categories=days_order, ordered=True))).sort_index().reset_index(name='count')
    fig6 = px.bar(dow, x='dow', y='count', title="6. Sessions by Day of Week", color_discrete_sequence=['#E91E63'])
    st.plotly_chart(fig6, use_container_width=True)


st.divider()

# CRITICAL ALERTS
st.subheader("🚨 CRITICAL ALERTS")

stn_curr = current_sessions.groupby('station_id').agg(
    total_sessions=('session_id', 'count'),
    failed_sessions=('session_status', lambda x: (x=='Failed').sum()),
    duration=('duration_minutes', 'sum')
).reset_index()
stn_curr['failure_rate'] = (stn_curr['failed_sessions'] / stn_curr['total_sessions']) * 100

chg_count = chargers[chargers['charger_status'] == 'Active'].groupby('station_id').size().reset_index(name='active_chargers')
stn_curr = stn_curr.merge(chg_count, on='station_id', how='left').fillna(0)
stn_curr['utilization'] = (stn_curr['duration'] / (stn_curr['active_chargers'] * 30 * 24 * 60)) * 100

col_alert1, col_alert2 = st.columns(2)

with col_alert1:
    st.markdown("**High Failure-Rate Stations (>3%)**")
    high_fail = stn_curr[stn_curr['failure_rate'] > 3.0].merge(stations[['station_id', 'station_name']], on='station_id')
    for _, row in high_fail.head(5).iterrows():
        st.markdown(f"<div class='alert-card'>🔴 <b>{row['station_name']}</b>: {row['failure_rate']:.1f}% failure rate ({row['failed_sessions']} failed)</div>", unsafe_allow_html=True)
    if high_fail.empty: st.success("No stations with high failure rate.")
    if len(high_fail) > 5: st.caption(f"+ {len(high_fail)-5} more...")

    st.markdown("**Overloaded Stations (>15% avg util)**") 
    overloaded = stn_curr[stn_curr['utilization'] > 15.0].merge(stations[['station_id', 'station_name']], on='station_id')
    for _, row in overloaded.head(5).iterrows():
        st.markdown(f"<div class='alert-card' style='border-left-color:#FF9800;'>🔥 <b>{row['station_name']}</b>: {row['utilization']:.1f}% utilization</div>", unsafe_allow_html=True)
    if overloaded.empty: st.success("No overloaded stations.")
    if len(overloaded) > 5: st.caption(f"+ {len(overloaded)-5} more...")

with col_alert2:
    st.markdown("**Underutilized Stations (<1% avg util)**")
    underutil = stn_curr[(stn_curr['utilization'] < 1.0) & (stn_curr['active_chargers']>0)].merge(stations[['station_id', 'station_name']], on='station_id')
    for _, row in underutil.head(5).iterrows():
        st.markdown(f"<div class='alert-card' style='border-left-color:#03A9F4;'>🧊 <b>{row['station_name']}</b>: {row['utilization']:.1f}% utilization</div>", unsafe_allow_html=True)
    if underutil.empty: st.success("No severely underutilized stations.")
    if len(underutil) > 5: st.caption(f"+ {len(underutil)-5} more...")

    st.markdown("**Abnormal Chargers (Hardware Fault Risk)**")
    abnormals = current_sessions[current_sessions['session_status'] == 'Abnormal'].groupby(['station_id', 'charger_id']).size().reset_index(name='incidents')
    abnormals = abnormals.merge(stations[['station_id', 'station_name']], on='station_id').sort_values('incidents', ascending=False)
    for _, row in abnormals.head(5).iterrows():
        st.markdown(f"<div class='alert-card' style='border-left-color:#9C27B0;'>🔧 <b>{row['charger_id']}</b> at {row['station_name']}: {row['incidents']} abnormal sessions</div>", unsafe_allow_html=True)
    if abnormals.empty: st.success("No abnormal chargers detected.")
    if len(abnormals) > 5: st.caption(f"+ {len(abnormals)-5} more...")
