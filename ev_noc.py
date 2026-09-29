import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from datetime import datetime, timedelta

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="EV NOC", layout="wide", page_icon="⚡")
st.title("⚡ EV Charging Network Operations Center (NOC)")
st.markdown("Transforming raw charging-session data into actionable operational intelligence.")

# --- 0. DATA INGESTION (Simulated for standalone demo) ---
@st.cache_data
def load_data():
    np.random.seed(42)
    
    # Generate 50 Stations
    stations_df = pd.DataFrame({
        "station_id": [f"ST-{i:03d}" for i in range(1, 51)],
        "lat": np.random.uniform(33.0, 39.0, 50),
        "lon": np.random.uniform(-122.0, -117.0, 50),
        "chargers_count": np.random.randint(2, 10, 50),
        "status": np.random.choice(["Online", "Offline", "Degraded"], 50, p=[0.85, 0.05, 0.10])
    })
    
    # Generate 15,000 charging sessions over the last 30 days
    end_date = datetime.now()
    sessions = []
    
    for _ in range(15000):
        station = stations_df.sample(1).iloc[0]
        # Simulate demand curve (peak in afternoon)
        hour = int(np.random.normal(14, 4)) % 24
        days_ago = np.random.randint(0, 30)
        session_time = end_date - timedelta(days=days_ago, hours=24-hour, minutes=np.random.randint(0, 60))
        
        duration_hrs = max(0.2, np.random.normal(1.5, 0.8))
        
        # Inject anomalous behaviors
        anomaly_chance = np.random.random()
        if anomaly_chance < 0.02: 
            # Camper: Long duration, almost no energy
            energy_kwh = duration_hrs * np.random.uniform(1, 3) 
        elif anomaly_chance > 0.98: 
            # Hardware fault: Massive energy spike in zero time
            energy_kwh = duration_hrs * np.random.uniform(200, 350) 
        else:
            # Normal charging curve
            energy_kwh = duration_hrs * np.random.normal(50, 10)
            
        sessions.append({
            "session_id": f"S-{np.random.randint(100000, 999999)}",
            "station_id": station["station_id"],
            "start_time": session_time,
            "day_of_week": session_time.strftime("%A"),
            "hour_of_day": session_time.hour,
            "duration_hrs": duration_hrs,
            "energy_kwh": energy_kwh,
            "revenue": energy_kwh * 0.35 # Flat $0.35 per kWh
        })
    
    return stations_df, pd.DataFrame(sessions)

stations_df, sessions_df = load_data()

# --- SIDEBAR: GLOBAL FILTERS ---
st.sidebar.header("NOC Controls")
selected_stations = st.sidebar.multiselect("Filter by Station", options=stations_df["station_id"].tolist(), default=[])

filtered_sessions = sessions_df.copy()
if selected_stations:
    filtered_sessions = filtered_sessions[filtered_sessions["station_id"].isin(selected_stations)]

# =====================================================================
# Q1. How is the entire charging network performing?
# =====================================================================
st.header("1. Network Performance Overview")
col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Sessions (30d)", f"{len(filtered_sessions):,}")
col2.metric("Energy Delivered (MWh)", f"{filtered_sessions['energy_kwh'].sum() / 1000:,.1f}")
col3.metric("Network Revenue", f"${filtered_sessions['revenue'].sum():,.2f}")

active_stations = stations_df[stations_df['status'] == 'Online'].shape[0]
col4.metric("Active Stations", f"{active_stations} / {len(stations_df)}")

# Daily Trend
daily_energy = filtered_sessions.set_index("start_time").resample("D")["energy_kwh"].sum().reset_index()
fig_ts = px.area(daily_energy, x="start_time", y="energy_kwh", title="Daily Energy Delivered (kWh)", markers=True)
st.plotly_chart(fig_ts, use_container_width=True)

st.divider()

# =====================================================================
# Q2. Which stations are healthy, overloaded, underutilized, or risky?
# =====================================================================
st.header("2. Station Health & Risk Analysis")

# Aggregate station data
station_stats = filtered_sessions.groupby("station_id").agg(
    total_sessions=("session_id", "count"),
    total_energy=("energy_kwh", "sum")
).reset_index()

station_health = pd.merge(stations_df, station_stats, on="station_id", how="left").fillna(0)

# Calculate Utilization % (Sessions / Max theoretical sessions assuming 1hr avg turnaround)
station_health["utilization_pct"] = (station_health["total_sessions"] / (station_health["chargers_count"] * 24 * 30)) * 100

def categorize_health(row):
    if row["status"] == "Offline": return "Critical (Offline)"
    if row["utilization_pct"] > 60: return "Overloaded"
    if row["utilization_pct"] < 5: return "Underutilized"
    if row["status"] == "Degraded": return "Risky (Degraded)"
    return "Healthy"

station_health["health_category"] = station_health.apply(categorize_health, axis=1)

# Display Data Table
st.dataframe(
    station_health[["station_id", "status", "chargers_count", "utilization_pct", "health_category"]]
    .style.background_gradient(subset=["utilization_pct"], cmap="RdYlGn_r"),
    use_container_width=True
)

st.divider()

# =====================================================================
# Q3. When and where does charging demand occur?
# =====================================================================
st.header("3. Spatiotemporal Demand")
col_map, col_heat = st.columns(2)

with col_map:
    st.subheader("Geographic Demand Map")
    fig_map = px.scatter_map(
        station_health, lat="lat", lon="lon", size="total_sessions", color="health_category",
        hover_name="station_id", map_style="carto-positron", zoom=4.5,
        color_discrete_map={"Healthy": "#2ca02c", "Overloaded": "#d62728", "Underutilized": "#1f77b4", "Critical (Offline)": "#000000", "Risky (Degraded)": "#ff7f0e"}
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col_heat:
    st.subheader("Temporal Demand (Day vs. Hour)")
    heatmap_data = filtered_sessions.groupby(["day_of_week", "hour_of_day"]).size().reset_index(name="count")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    heatmap_data['day_of_week'] = pd.Categorical(heatmap_data['day_of_week'], categories=days, ordered=True)
    heatmap_data = heatmap_data.sort_values("day_of_week")
    
    fig_heat = px.density_heatmap(heatmap_data, x="hour_of_day", y="day_of_week", z="count", color_continuous_scale="Viridis")
    st.plotly_chart(fig_heat, use_container_width=True)

st.divider()

# =====================================================================
# Q4. Which chargers show abnormal operational behavior?
# =====================================================================
st.header("4. Abnormal Charger Behavior (Anomaly Detection)")
st.markdown("Identifies *Campers* (vehicles plugged in long but not charging) and *Faults* (impossible energy draws).")

# Z-score based anomaly detection logic
filtered_sessions["duration_z"] = (filtered_sessions["duration_hrs"] - filtered_sessions["duration_hrs"].mean()) / filtered_sessions["duration_hrs"].std()
filtered_sessions["energy_z"] = (filtered_sessions["energy_kwh"] - filtered_sessions["energy_kwh"].mean()) / filtered_sessions["energy_kwh"].std()

filtered_sessions["behavior"] = "Normal"
filtered_sessions.loc[(filtered_sessions["duration_z"] > 2) & (filtered_sessions["energy_z"] < -1), "behavior"] = "Camper Detected"
filtered_sessions.loc[(filtered_sessions["duration_z"] < -0.5) & (filtered_sessions["energy_z"] > 2.5), "behavior"] = "Hardware Fault Risk"

fig_scatter = px.scatter(
    filtered_sessions, x="duration_hrs", y="energy_kwh", color="behavior",
    hover_data=["station_id", "session_id"],
    color_discrete_map={"Normal": "#7f7f7f", "Camper Detected": "#ff7f0e", "Hardware Fault Risk": "#d62728"},
    title="Session Duration vs Energy Delivered"
)
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# =====================================================================
# Q5. Where should the operator consider adding charging capacity?
# =====================================================================
st.header("5. Capacity Expansion Recommendations")
st.markdown("Stations consistently operating above utilization thresholds require immediate CapEx review to prevent customer churn.")

expansion_candidates = station_health[station_health["health_category"] == "Overloaded"].sort_values(by="utilization_pct", ascending=False)

if not expansion_candidates.empty:
    st.error(f"⚠️ Action Required: Identified {len(expansion_candidates)} stations facing severe capacity limits.")
    st.dataframe(expansion_candidates[["station_id", "chargers_count", "total_sessions", "utilization_pct"]].style.format({"utilization_pct": "{:.1f}%"}), use_container_width=True)
else:
    st.success("✅ Current capacity is sufficient across the network. No immediate expansions recommended.")
