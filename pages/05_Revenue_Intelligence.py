import streamlit as st

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Revenue Intelligence", layout="wide", page_icon="💰")

st.markdown("""
    <style>
    .metric-card { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 4px solid #FF9800; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("💰 Revenue Intelligence Module")
st.markdown("Analyze charging revenue streams, operational efficiency, and financial matrix performance.")

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


if len(f_ses) == 0:
    st.warning("No data.")
    st.stop()

# --- KPI CALCULATIONS ---
total_rev = f_ses['revenue'].sum()
total_energy = f_ses['energy_kwh'].sum()
total_sessions = len(f_ses)
successful_sessions = len(f_ses[f_ses['session_status'] == 'Completed'])

rev_per_session = total_rev / total_sessions if total_sessions > 0 else 0
avg_tx_value = total_rev / successful_sessions if successful_sessions > 0 else 0
rev_per_kwh = total_rev / total_energy if total_energy > 0 else 0

active_chargers = len(f_ses['charger_id'].unique())
rev_per_charger = total_rev / active_chargers if active_chargers > 0 else 0

active_stations = len(f_ses['station_id'].unique())
rev_per_station = total_rev / active_stations if active_stations > 0 else 0

operating_hours = f_ses['duration_minutes'].sum() / 60
rev_per_op_hour = total_rev / operating_hours if operating_hours > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Total Revenue</div><div style='font-size:24px; font-weight:bold;'>${total_rev:,.2f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Revenue / Station</div><div style='font-size:24px; font-weight:bold;'>${rev_per_station:,.2f}</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Total Energy (kWh)</div><div style='font-size:24px; font-weight:bold;'>{total_energy:,.1f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Revenue / Charger</div><div style='font-size:24px; font-weight:bold;'>${rev_per_charger:,.2f}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Average Transaction Value</div><div style='font-size:24px; font-weight:bold;'>${avg_tx_value:,.2f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Revenue / Session</div><div style='font-size:24px; font-weight:bold;'>${rev_per_session:,.2f}</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Revenue / kWh</div><div style='font-size:24px; font-weight:bold;'>${rev_per_kwh:,.2f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='metric-card'><div style='color:#aaa;'>Revenue / Operating Hour</div><div style='font-size:24px; font-weight:bold;'>${rev_per_op_hour:,.2f}</div></div>", unsafe_allow_html=True)

st.divider()

# --- REVENUE MATRIX (Utilization vs Revenue) ---
st.subheader("Station Performance Matrix (Utilization vs Revenue)")

days_in_period = (f_ses['date'].max() - f_ses['date'].min()).days
if days_in_period <= 0: days_in_period = 1

stn_agg = f_ses.groupby(['station_id', 'station_name']).agg(
    rev=('revenue', 'sum'),
    dur=('duration_minutes', 'sum'),
    chg_count=('charger_id', 'nunique')
).reset_index()

stn_agg['util'] = (stn_agg['dur'] / (stn_agg['chg_count'] * days_in_period * 24 * 60)) * 100

# Quadrants based on medians
med_rev = stn_agg['rev'].median()
med_util = stn_agg['util'].median()

def get_quadrant(r, u):
    if u >= med_util and r >= med_rev: return 'High Util / High Rev'
    if u >= med_util and r < med_rev: return 'High Util / Low Rev'
    if u < med_util and r >= med_rev: return 'Low Util / High Rev'
    return 'Low Util / Low Rev'

stn_agg['Quadrant'] = stn_agg.apply(lambda row: get_quadrant(row['rev'], row['util']), axis=1)

color_map = {
    'High Util / High Rev': '#4CAF50',
    'Low Util / High Rev': '#2196F3',
    'High Util / Low Rev': '#FF9800',
    'Low Util / Low Rev': '#9E9E9E'
}

fig_scatter = px.scatter(
    stn_agg, x='util', y='rev', color='Quadrant', hover_name='station_name',
    labels={'util': 'Hardware Utilization (%)', 'rev': 'Total Revenue ($)'},
    color_discrete_map=color_map, title="7. Station Matrix (Quadrants generated via dataset medians)"
)

# Add quadrant lines
fig_scatter.add_vline(x=med_util, line_width=1, line_dash="dash", line_color="#888")
fig_scatter.add_hline(y=med_rev, line_width=1, line_dash="dash", line_color="#888")

st.plotly_chart(fig_scatter, use_container_width=True)

with st.expander("ℹ️ Operational Context: Interpreting the Quadrants"):
    st.markdown("""
    **High Utilization / High Revenue**
    *Operational Indication:* Core network anchors. Highly efficient assets performing exactly as designed. Potential candidates for capacity expansion to capture overflow demand.

    **Low Utilization / High Revenue**
    *Operational Indication:* High-margin sites. Often correlates with high-power DC Fast Chargers serving quick, expensive bursts of energy. Indicates strong pricing power or premium locations.

    **High Utilization / Low Revenue**
    *Operational Indication:* Frictional bottlenecks. Often indicates "campers" (long durations without drawing power), broken Level 2 chargers, or low-margin, high-turnover behavior. Review pricing structures (e.g., idle fees).

    **Low Utilization / Low Revenue**
    *Operational Indication:* Underperforming assets. Potential visibility, location, or hardware reliability issues. Investigate for marketing, relocation, or hardware maintenance needs.
    """)

st.divider()

# --- REVENUE VISUALIZATIONS ---
st.subheader("Financial Dimensions")

t1, t2 = st.columns(2)
with t1:
    daily_rev = f_ses.groupby('date')['revenue'].sum().reset_index()
    fig1 = px.line(daily_rev, x='date', y='revenue', title="1. Revenue Trend (Daily)")
    st.plotly_chart(fig1, use_container_width=True)
with t2:
    stn_rev = f_ses.groupby('station_name')['revenue'].sum().reset_index().sort_values('revenue', ascending=False).head(10)
    fig2 = px.bar(stn_rev, x='revenue', y='station_name', orientation='h', title="2. Top 10 Stations by Revenue")
    st.plotly_chart(fig2, use_container_width=True)

t3, t4 = st.columns(2)
with t3:
    city_rev = f_ses.groupby('city')['revenue'].sum().reset_index()
    fig3 = px.pie(city_rev, values='revenue', names='city', hole=0.4, title="3. Revenue Distribution by City")
    st.plotly_chart(fig3, use_container_width=True)
with t4:
    chg_rev = f_ses.groupby('charger_type')['revenue'].sum().reset_index()
    fig4 = px.pie(chg_rev, values='revenue', names='charger_type', hole=0.4, title="4. Revenue by Charger Type")
    st.plotly_chart(fig4, use_container_width=True)

t5, t6 = st.columns(2)
with t5:
    veh_rev = f_ses.groupby('vehicle_type')['revenue'].sum().reset_index().sort_values('revenue', ascending=False)
    fig5 = px.bar(veh_rev, x='vehicle_type', y='revenue', title="5. Revenue by Vehicle Type")
    st.plotly_chart(fig5, use_container_width=True)
with t6:
    hr_rev = f_ses.groupby('hour')['revenue'].sum().reset_index()
    fig6 = px.bar(hr_rev, x='hour', y='revenue', title="6. Revenue Yield by Hour of Day")
    st.plotly_chart(fig6, use_container_width=True)
