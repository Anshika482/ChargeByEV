import streamlit as st
import pandas as pd
import numpy as np
from datetime import timedelta

st.set_page_config(page_title="Charger Health & Anomaly Monitor", layout="wide", page_icon="🔧")

st.markdown("""
    <style>
    .severity-High { color: #F44336; font-weight: bold; }
    .severity-Medium { color: #FF9800; font-weight: bold; }
    .severity-Low { color: #FFEB3B; font-weight: bold; }
    .metric-card { background-color: #1E1E1E; padding: 15px; border-radius: 5px; border-left: 4px solid #9C27B0; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

st.title("🔧 Charger Health & Anomaly Monitor")
st.markdown("Analyze charger-level hardware behavior and proactively flag statistical outliers.")

@st.cache_data
def load_data():
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    
    sessions['start_time'] = pd.to_datetime(sessions['start_time'])
    sessions['end_time'] = pd.to_datetime(sessions['end_time'])
    sessions['date'] = sessions['start_time'].dt.date
    
    return stations, chargers, sessions

try:
    stations, chargers, sessions = load_data()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

days_in_dataset = (sessions['start_time'].max() - sessions['start_time'].min()).days
if days_in_dataset <= 0: days_in_dataset = 1

# --- CHARGER AGGREGATIONS ---
chg_agg = sessions.groupby(['station_id', 'charger_id']).agg(
    total_sessions=('session_id', 'count'),
    successful_sessions=('session_status', lambda x: (x == 'Completed').sum()),
    failed_sessions=('session_status', lambda x: (x == 'Failed').sum()),
    interrupted_sessions=('session_status', lambda x: (x == 'Cancelled').sum()),
    duration=('duration_minutes', 'sum'),
    avg_duration=('duration_minutes', 'mean'),
    avg_energy=('energy_kwh', 'mean'),
    avg_revenue=('revenue', 'mean')
).reset_index()

chg_agg['failure_rate'] = (chg_agg['failed_sessions'] / chg_agg['total_sessions']) * 100
chg_agg['interruption_rate'] = (chg_agg['interrupted_sessions'] / chg_agg['total_sessions']) * 100
chg_agg['utilization'] = (chg_agg['duration'] / (days_in_dataset * 24 * 60)) * 100

chg_master = chargers.merge(chg_agg, on=['station_id', 'charger_id'], how='left').fillna(0)


# --- EXPLAINABLE ANOMALY DETECTION ENGINE (IQR / Rolling Diff) ---
anomalies = []

# 1. Unusually long sessions / 2. Unusually low energy
dur_q1, dur_q3 = sessions['duration_minutes'].quantile([0.25, 0.75])
dur_iqr = dur_q3 - dur_q1
dur_upper = dur_q3 + 3 * dur_iqr  # Extreme Outlier

abnormal_sessions = sessions[(sessions['duration_minutes'] > dur_upper) | ((sessions['duration_minutes'] > dur_q3) & (sessions['energy_kwh'] < 2.0))]

# Add a representative sample of these session-level anomalies
for _, row in abnormal_sessions.head(300).iterrows(): 
    if row['duration_minutes'] > dur_upper:
        anomalies.append({
            'timestamp': row['start_time'].strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': row['station_id'],
            'anomaly_type': 'Unusually Long Session',
            'metric': 'Duration (min)',
            'observed_value': f"{row['duration_minutes']:.1f}",
            'expected_range': f"<= {dur_upper:.1f}",
            'severity': 'Medium'
        })
    elif row['duration_minutes'] > dur_q3 and row['energy_kwh'] < 2.0:
        anomalies.append({
            'timestamp': row['start_time'].strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': row['station_id'],
            'anomaly_type': 'Unusually Low Energy (Camper)',
            'metric': 'Energy (kWh)',
            'observed_value': f"{row['energy_kwh']:.2f}",
            'expected_range': f"> 2.0",
            'severity': 'High'
        })

# 3. High failure rate
fr_q1, fr_q3 = chg_master['failure_rate'].quantile([0.25, 0.75])
fr_upper = fr_q3 + 1.5 * (fr_q3 - fr_q1)
if fr_upper < 1.0: fr_upper = 2.0 # Minimum threshold

for _, row in chg_master[chg_master['failure_rate'] > fr_upper].iterrows():
    if row['total_sessions'] > 15: 
        anomalies.append({
            'timestamp': sessions['start_time'].max().strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': row['station_id'],
            'anomaly_type': 'High Failure Rate',
            'metric': 'Failure Rate (%)',
            'observed_value': f"{row['failure_rate']:.1f}%",
            'expected_range': f"<= {fr_upper:.1f}%",
            'severity': 'High'
        })

# 4. & 5. Sudden Drops in Revenue or Utilization
d_max = sessions['date'].max()
period_2_start = d_max - timedelta(days=15)
period_1_start = period_2_start - timedelta(days=15)

p2_df = sessions[(sessions['date'] > period_2_start) & (sessions['date'] <= d_max)]
p1_df = sessions[(sessions['date'] > period_1_start) & (sessions['date'] <= period_2_start)]

p2_agg = p2_df.groupby('charger_id').agg(rev=('revenue', 'sum'), dur=('duration_minutes', 'sum')).reset_index()
p1_agg = p1_df.groupby('charger_id').agg(rev=('revenue', 'sum'), dur=('duration_minutes', 'sum')).reset_index()

trend = p1_agg.merge(p2_agg, on='charger_id', suffixes=('_p1', '_p2'))
trend['rev_drop'] = ((trend['rev_p2'] - trend['rev_p1']) / trend['rev_p1']) * 100
trend['dur_drop'] = ((trend['dur_p2'] - trend['dur_p1']) / trend['dur_p1']) * 100

for _, row in trend.iterrows():
    chg_info = chg_master[chg_master['charger_id'] == row['charger_id']].iloc[0]
    
    if row['rev_p1'] > 100 and row['rev_drop'] < -60: 
        anomalies.append({
            'timestamp': d_max.strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': chg_info['station_id'],
            'anomaly_type': 'Sudden Revenue Drop',
            'metric': 'Revenue Change (%)',
            'observed_value': f"{row['rev_drop']:.1f}%",
            'expected_range': "> -25.0%",
            'severity': 'High'
        })
    if row['dur_p1'] > 500 and row['dur_drop'] < -60: 
        anomalies.append({
            'timestamp': d_max.strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': chg_info['station_id'],
            'anomaly_type': 'Sudden Utilization Drop',
            'metric': 'Utilization Change (%)',
            'observed_value': f"{row['dur_drop']:.1f}%",
            'expected_range': "> -25.0%",
            'severity': 'Medium'
        })

# 6. Abnormal Session Frequency
sf_q1, sf_q3 = chg_master['total_sessions'].quantile([0.25, 0.75])
sf_iqr = sf_q3 - sf_q1
sf_upper = sf_q3 + 1.5 * sf_iqr
sf_lower = max(1, sf_q1 - 1.5 * sf_iqr)

for _, row in chg_master.iterrows():
    if row['total_sessions'] > sf_upper:
        anomalies.append({
            'timestamp': sessions['start_time'].max().strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': row['station_id'],
            'anomaly_type': 'Abnormally High Frequency',
            'metric': 'Total Sessions',
            'observed_value': f"{row['total_sessions']}",
            'expected_range': f"<= {sf_upper:.0f}",
            'severity': 'Low'
        })
    elif row['total_sessions'] < sf_lower and row['charger_status'] == 'Active':
        anomalies.append({
            'timestamp': sessions['start_time'].max().strftime('%Y-%m-%d %H:%M'),
            'charger': row['charger_id'],
            'station': row['station_id'],
            'anomaly_type': 'Abnormally Low Frequency',
            'metric': 'Total Sessions',
            'observed_value': f"{row['total_sessions']}",
            'expected_range': f">= {sf_lower:.0f}",
            'severity': 'Low'
        })

anomaly_df = pd.DataFrame(anomalies)

st.sidebar.header("Anomaly Filters")
f_sev = st.sidebar.multiselect("Severity Filter", ['High', 'Medium', 'Low'], default=['High', 'Medium', 'Low'])
if not anomaly_df.empty and len(f_sev) > 0:
    anomaly_df = anomaly_df[anomaly_df['severity'].isin(f_sev)]
elif len(f_sev) == 0:
    anomaly_df = pd.DataFrame() # hide if nothing selected

# --- UI RENDERING ---

st.subheader("Charger Hardware & Utilization Statistics")
c_display = chg_master[['charger_id', 'station_id', 'charger_type', 'power_kw', 'charger_status', 'total_sessions', 'successful_sessions', 'failed_sessions', 'failure_rate', 'interruption_rate', 'avg_duration', 'avg_energy', 'utilization', 'avg_revenue']]
c_display.columns = ['Charger ID', 'Station ID', 'Type', 'Power (kW)', 'Status', 'Total Sessions', 'Successful', 'Failed', 'Failure Rate', 'Interrupt Rate', 'Avg Duration (m)', 'Avg Energy (kWh)', 'Utilization', 'Avg Revenue']

st.dataframe(c_display.style.format({
    'Failure Rate': '{:.2f}%',
    'Interrupt Rate': '{:.2f}%',
    'Avg Duration (m)': '{:.1f}',
    'Avg Energy (kWh)': '{:.1f}',
    'Utilization': '{:.2f}%',
    'Avg Revenue': '${:.2f}'
}), use_container_width=True)

st.divider()

st.subheader("🚨 Potential Anomaly Detection Log")
with st.expander("ℹ️ Transparency: Statistical Detection Methodology (IQR & Rolling Diff)"):
    st.markdown("""
    All anomalies detected below are strictly labeled as **"Potential Anomalies"** and do not represent confirmed hardware failures. They are identified using Explainable Statistical methodologies, specifically the **Interquartile Range (IQR)** method to find outliers in network distributions.
    
    1. **Unusually Long Sessions:** Duration exceeds Q3 + 3*IQR of network baseline.
    2. **Unusually Low Energy:** Duration exceeds Q3, but Energy Delivered is < 2.0 kWh (Likely a parked/camped vehicle).
    3. **High Failure Rate:** Charger's hardware failure rate exceeds Q3 + 1.5*IQR of the network average.
    4. & 5. **Sudden Revenue/Utilization Drop:** Compares trailing 15 days vs preceding 15 days. Flags drops worse than -60%.
    6. **Abnormal Session Frequency:** Volume exceeds Q3 + 1.5*IQR or falls below Q1 - 1.5*IQR.
    """)

if not anomaly_df.empty:
    def color_sev(val):
        if val == 'High': return 'color: #F44336; font-weight: bold;'
        if val == 'Medium': return 'color: #FF9800; font-weight: bold;'
        if val == 'Low': return 'color: #FFEB3B; font-weight: bold;'
        return ''
    
    anomaly_df = anomaly_df.sort_values(by='severity', key=lambda x: x.map({'High':0, 'Medium':1, 'Low':2}))
    st.dataframe(anomaly_df.style.map(color_sev, subset=['severity']), use_container_width=True, hide_index=True)
else:
    st.success("No anomalies detected matching the selected filters.")
