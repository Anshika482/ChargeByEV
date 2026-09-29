import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Executive Insights", layout="wide", page_icon="🧠")

st.markdown("""
    <style>
    .insight-box { background-color: #1a1a1a; padding: 20px; border-radius: 8px; border-left: 4px solid #00BCD4; margin-bottom: 15px; font-size: 16px;}
    .insight-box b { color: #fff; }
    </style>
""", unsafe_allow_html=True)

st.title("🧠 Executive Insights Engine")
st.markdown("Automated, deterministic data-driven observations generated strictly from network telemetry.")

@st.cache_data
def load_data():
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    
    sessions['start_time'] = pd.to_datetime(sessions['start_time'])
    sessions['date'] = sessions['start_time'].dt.date
    sessions['hour'] = sessions['start_time'].dt.hour
    sessions['day_of_week'] = sessions['start_time'].dt.day_name()
    
    return stations, chargers, sessions

try:
    stations, chargers, sessions = load_data()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

# --- FILTERS ---
st.sidebar.header("Global Filters")
min_d = sessions['date'].min()
max_d = sessions['date'].max()

date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d)
cities = ["All Network"] + sorted(stations['city'].unique().tolist())
f_city = st.sidebar.selectbox("City", cities)

f_ses = sessions.copy()
if len(date_range) == 2:
    f_ses = f_ses[(f_ses['date'] >= date_range[0]) & (f_ses['date'] <= date_range[1])]

if f_city != "All Network":
    f_stn_ids = stations[stations['city'] == f_city]['station_id'].tolist()
    f_ses = f_ses[f_ses['station_id'].isin(f_stn_ids)]
    
if len(f_ses) == 0:
    st.warning("No data in this range.")
    st.stop()

st.subheader("Data-Driven Observations")

insights = []
days_in_period = (f_ses['date'].max() - f_ses['date'].min()).days
if days_in_period <= 0: days_in_period = 1

# --- AGGREGATIONS ---
stn_agg = f_ses.groupby('station_id').agg(
    total_sessions=('session_id', 'count'),
    revenue=('revenue', 'sum'),
    duration=('duration_minutes', 'sum'),
    failed=('session_status', lambda x: (x=='Failed').sum())
).reset_index()

active_chg = chargers[chargers['charger_status'] == 'Active'].groupby('station_id').size().reset_index(name='active_chargers')
stn_agg = stn_agg.merge(active_chg, on='station_id', how='left').fillna({'active_chargers': 0})
stn_agg = stn_agg.merge(stations[['station_id', 'station_name']], on='station_id', how='left')

stn_agg['utilization'] = (stn_agg['duration'] / (stn_agg['active_chargers'] * days_in_period * 24 * 60)) * 100
stn_agg['failure_rate'] = (stn_agg['failed'] / stn_agg['total_sessions']) * 100

net_avg_util = stn_agg['utilization'].mean()
net_avg_fail = stn_agg['failure_rate'].mean()

# --- INSIGHT 1: Peak Capacity Pressure ---
if len(stn_agg) > 0:
    max_util_stn = stn_agg.loc[stn_agg['utilization'].idxmax()]
    if max_util_stn['utilization'] > (net_avg_util * 1.5):
        insights.append(f"Station **{max_util_stn['station_name']}** ({max_util_stn['station_id']}) recorded **{max_util_stn['utilization']:.1f}%** average hardware utilization, compared with the baseline network average of **{net_avg_util:.1f}%**, indicating substantially higher baseline capacity pressure.")

# --- INSIGHT 2: Revenue Concentration ---
total_rev = stn_agg['revenue'].sum()
stn_agg = stn_agg.sort_values(by='revenue', ascending=False)
top_10_pct_count = max(1, int(len(stn_agg) * 0.10))
top_10_rev = stn_agg.head(top_10_pct_count)['revenue'].sum()
if total_rev > 0:
    pct_rev = (top_10_rev / total_rev) * 100
    if pct_rev > 15:
        insights.append(f"Network revenue is highly concentrated: The top **10%** of stations (representing {top_10_pct_count} sites) generated **{pct_rev:.1f}%** (${top_10_rev:,.0f}) of all gross revenue, demonstrating asymmetric geographic financial yield.")

# --- INSIGHT 3: Extreme Hardware Failure Rate ---
if len(stn_agg) > 0:
    max_fail_stn = stn_agg.loc[stn_agg['failure_rate'].idxmax()]
    if max_fail_stn['failure_rate'] > 3.0 and max_fail_stn['failure_rate'] > (net_avg_fail * 2):
        insights.append(f"Station **{max_fail_stn['station_name']}** ({max_fail_stn['station_id']}) experienced a **{max_fail_stn['failure_rate']:.1f}%** hardware failure rate across {max_fail_stn['total_sessions']} sessions, vastly exceeding the baseline average of **{net_avg_fail:.1f}%**, signaling acute operational risk.")

# --- INSIGHT 4: Stranded Capital / Underutilization ---
if len(stn_agg) > 0:
    # Look for stations with > 0 chargers but lowest utilization
    min_util_stn = stn_agg[stn_agg['active_chargers'] > 0].sort_values(by='utilization').iloc[0]
    if min_util_stn['utilization'] < 2.0 and net_avg_util > 5.0:
        insights.append(f"Station **{min_util_stn['station_name']}** ({min_util_stn['station_id']}) remains heavily underutilized, recording only **{min_util_stn['utilization']:.1f}%** utilization versus the **{net_avg_util:.1f}%** network baseline, identifying highly inefficient hardware deployment.")

# --- INSIGHT 5: Temporal Demand Concentration ---
hourly_counts = f_ses.groupby('hour').size()
busiest_hour = hourly_counts.idxmax()
avg_hour = hourly_counts.mean()
peak_ratio = (hourly_counts.max() / avg_hour) if avg_hour > 0 else 0
if peak_ratio > 1.3:
    insights.append(f"Network demand peaks intensely at **{busiest_hour}:00**, where transaction volume is **{peak_ratio:.1f}x** higher than the standard hourly average, defining the primary temporal window for queue formation.")

# --- INSIGHT 6: Abnormal Charger Behavior (Campers) ---
abnormal_sessions = f_ses[(f_ses['duration_minutes'] > 240) & (f_ses['energy_kwh'] < 2.0)]
if len(abnormal_sessions) > 50:
    insights.append(f"The network detected **{len(abnormal_sessions):,}** anomalous 'Camper' sessions (duration > 4 hours but < 2 kWh delivered), indicating vehicles occupying physical hardware bays without actively charging.")

# --- RENDER ---
if insights:
    for insight in insights:
        st.markdown(f"<div class='insight-box'>{insight}</div>", unsafe_allow_html=True)
else:
    st.info("No statistically significant outliers detected in this subset of data.")
    
st.write("")
with st.expander("ℹ️ Transparency: Insight Generation Methodology"):
    st.markdown("""
    These executive insights are algorithmically generated using rigid, deterministic rule-sets evaluated against the raw telemetry dataset. 
    
    The engine strictly abides by the following constraints:
    
    1. **No AI Hallucinations:** Every claim maps directly to a mathematical aggregate calculation present in the active dataset. 
    2. **No Invented Causation:** The engine observes correlations and statistical realities, but does not invent narratives explaining *why* they occurred.
    3. **No Unprompted Recommendations:** The engine identifies operational asymmetry (e.g., 'inefficient hardware deployment') but does not generate unsupported business recommendations (e.g., 'You should relocate this charger').
    4. **Baseline Comparisons:** Every anomaly or insight is explicitly anchored against a broader network average or baseline to establish statistical significance.
    """)
