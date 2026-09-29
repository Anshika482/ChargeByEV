import streamlit as st
import pandas as pd
import filters

st.set_page_config(page_title="ChargeByEV NOC", layout="wide", page_icon="⚡")

# Custom CSS for the landing page
st.markdown("""
    <style>
    .hero-container {
        padding: 3rem 0;
        text-align: center;
        background: linear-gradient(180deg, rgba(30,30,30,1) 0%, rgba(18,18,18,1) 100%);
        border-radius: 12px;
        border-bottom: 2px solid #00BCD4;
        margin-bottom: 2rem;
    }
    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #00BCD4, #2196F3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        color: #B0BEC5;
        font-size: 1.2rem;
        font-weight: 400;
    }
    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 1.5rem;
        margin-bottom: 3rem;
    }
    .stat-card {
        background-color: #1E1E1E;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #333;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 24px rgba(0, 188, 212, 0.15);
        border-color: #00BCD4;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #FFFFFF;
        margin: 0.5rem 0;
    }
    .stat-label {
        color: #90A4AE;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .module-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.5rem;
    }
    .module-card {
        background-color: #1E1E1E;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        height: 100%;
    }
    .module-card h4 {
        margin-top: 0;
        color: #E0E0E0;
    }
    .module-card p {
        color: #9E9E9E;
        font-size: 0.95rem;
        line-height: 1.4;
    }
    </style>
""", unsafe_allow_html=True)

# Fetch high-level data directly to display network-wide stats (ignoring filters for the landing page)
try:
    stations, chargers, sessions = filters.load_all_data()
    total_stations = len(stations)
    total_revenue = sessions['revenue'].sum()
    total_sessions = len(sessions)
    total_energy = sessions['energy_kwh'].sum()
except Exception:
    total_stations, total_revenue, total_sessions, total_energy = 0, 0, 0, 0

# --- HERO SECTION ---
st.markdown("""
<div class="hero-container">
    <div class="hero-title">⚡ ChargeByEV NOC</div>
    <div class="hero-subtitle">Unified Operations & Intelligence Platform</div>
</div>
""", unsafe_allow_html=True)

# --- NETWORK STATS ---
st.markdown(f"""
<div class="metric-grid">
    <div class="stat-card">
        <div class="stat-label">Active Network Sites</div>
        <div class="stat-value">{total_stations:,}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Total Sessions Handled</div>
        <div class="stat-value">{total_sessions:,}</div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Total Energy Dispensed</div>
        <div class="stat-value">{total_energy:,.0f} <span style="font-size:1.2rem; color:#888;">kWh</span></div>
    </div>
    <div class="stat-card">
        <div class="stat-label">Cumulative Revenue</div>
        <div class="stat-value"><span style="font-size:1.5rem; color:#00BCD4;">$</span>{total_revenue:,.0f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

st.markdown("### 🗺️ Intelligence Directory")
st.markdown("<span style='color:#B0BEC5;'>Select a module from the sidebar to begin deep-dive analysis. All modules are contextually linked to your Global Filter state.</span>", unsafe_allow_html=True)
st.write("")

# --- MODULE DIRECTORY ---
modules = [
    ("📊 Network Command", "High-level macro KPIs, network-wide health, and core operational metrics overview.", "#00BCD4"),
    ("🏢 Station Intelligence", "Micro-level profiling of individual sites, including real-time Charging Pressure Index (CPI).", "#4CAF50"),
    ("📉 Demand Intelligence", "Temporal load profiling, statistical peak window detection, and demand heatmaps.", "#FF9800"),
    ("⚙️ Charger Health", "Hardware reliability profiling, automated anomaly detection, and IQR-based failure flagging.", "#F44336"),
    ("💰 Revenue Intelligence", "Financial yield analysis, including the 4-quadrant Utilization vs Revenue matrix.", "#9C27B0"),
    ("🗺️ Geo Intelligence", "Spatial mapping, geographic performance clustering, and regional demand visualization.", "#2196F3"),
    ("⚡ Capacity Simulator", "Deterministic stress-testing sandbox to simulate hardware expansion scenarios.", "#FFEB3B"),
    ("👥 Customer Intelligence", "Transactional segmentation classifying behavior into High Frequency, Occasional, and High Value cohorts.", "#009688"),
    ("🛡️ Data Quality", "Automated relational integrity scans to ensure dataset validity and pinpoint orphaned records.", "#607D8B"),
    ("🤖 Executive Insights", "Automated, non-hallucinating deterministic observations summarizing critical network states.", "#E91E63")
]

# Generate grid layout
for i in range(0, len(modules), 3):
    cols = st.columns(3)
    for j in range(3):
        if i + j < len(modules):
            title, desc, color = modules[i+j]
            cols[j].markdown(f"""
            <div class="module-card" style="border-left-color: {color};">
                <h4 style="color: {color}; margin-bottom: 10px;">{title}</h4>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)
    st.write("") # Vertical spacing

st.markdown("<br><center><p style='color:#666; font-size:14px;'>ChargeByEV OS v1.0.0 • Data Analyst Portfolio Grade</p></center>", unsafe_allow_html=True)
