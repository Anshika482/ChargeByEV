import streamlit as st

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Customer & Vehicle Intelligence", layout="wide", page_icon="👥")

st.markdown("""
    <style>
    .kpi-card { background-color: #1E1E1E; padding: 15px; border-radius: 8px; border-left: 4px solid #E91E63; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

st.title("👥 Customer & Vehicle Intelligence")
st.markdown("Analyze transactional behavior to understand customer segmentation and vehicle demand.")

try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs.get('f_city', 'All')
    f_stn = fs.get('f_stn', 'All Network')
    date_range = fs.get('date_range', [])
    f_ses = sessions.copy()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

days_in_period = (sessions['date'].max() - sessions['date'].min()).days
if days_in_period <= 0: days_in_period = 1

# --- CUSTOMER AGGREGATIONS ---
cust_agg = sessions.groupby('customer_id').agg(
    total_sessions=('session_id', 'count'),
    total_energy=('energy_kwh', 'sum'),
    total_revenue=('revenue', 'sum'),
    avg_duration=('duration_minutes', 'mean')
).reset_index()

# Overall KPIs
unique_customers = len(cust_agg)
avg_sessions_per_cust = cust_agg['total_sessions'].mean()
avg_energy_per_cust = cust_agg['total_energy'].mean()
avg_revenue_per_cust = cust_agg['total_revenue'].mean()
avg_session_duration = cust_agg['avg_duration'].mean()

repeat_customers = len(cust_agg[cust_agg['total_sessions'] > 1])
repeat_rate = (repeat_customers / unique_customers) * 100 if unique_customers > 0 else 0

avg_charging_frequency = avg_sessions_per_cust / (days_in_period / 30.0) # sessions per month

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Unique Customers</div><div style='font-size:24px; font-weight:bold;'>{unique_customers:,.0f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Repeat Customer Rate</div><div style='font-size:24px; font-weight:bold;'>{repeat_rate:.1f}%</div></div>", unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Sessions / Customer</div><div style='font-size:24px; font-weight:bold;'>{avg_sessions_per_cust:.1f}</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Avg Charging Freq (per month)</div><div style='font-size:24px; font-weight:bold;'>{avg_charging_frequency:.1f}</div></div>", unsafe_allow_html=True)
with c3:
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Avg Energy / Customer</div><div style='font-size:24px; font-weight:bold;'>{avg_energy_per_cust:,.1f} kWh</div></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Avg Session Duration</div><div style='font-size:24px; font-weight:bold;'>{avg_session_duration:.1f} min</div></div>", unsafe_allow_html=True)
with c4:
    st.markdown(f"<div class='kpi-card'><div style='color:#aaa;'>Avg Revenue / Customer</div><div style='font-size:24px; font-weight:bold;'>${avg_revenue_per_cust:,.2f}</div></div>", unsafe_allow_html=True)
    
st.divider()

# --- CUSTOMER SEGMENTATION (Strictly Transactional) ---
# Calculate thresholds (75th percentiles)
rev_p75 = cust_agg['total_revenue'].quantile(0.75)
freq_p75 = cust_agg['total_sessions'].quantile(0.75)
eng_p75 = cust_agg['total_energy'].quantile(0.75)

def assign_segment(row):
    # Mutually exclusive, prioritized by value
    if row['total_revenue'] >= rev_p75:
        return 'High Revenue'
    elif row['total_sessions'] >= freq_p75:
        return 'High Frequency'
    elif row['total_energy'] >= eng_p75:
        return 'High Energy'
    else:
        return 'Occasional'

cust_agg['Segment'] = cust_agg.apply(assign_segment, axis=1)

seg_summary = cust_agg.groupby('Segment').agg(
    Customers=('customer_id', 'count'),
    Total_Revenue=('total_revenue', 'sum'),
    Total_Energy=('total_energy', 'sum'),
    Avg_Sessions=('total_sessions', 'mean')
).reset_index()

seg_summary['% of Total Customers'] = (seg_summary['Customers'] / unique_customers * 100)
seg_summary['% of Total Revenue'] = (seg_summary['Total_Revenue'] / cust_agg['total_revenue'].sum() * 100)

st.subheader("Customer Behavioral Segmentation")
with st.expander("ℹ️ Transparency: Transactional Segmentation Logic"):
    st.markdown(f"""
    Customers are segmented exclusively based on their observable charging behavior. No demographic data is inferred.
    
    1. **High Revenue:** Top 25% of customers by lifetime revenue (> ${rev_p75:.2f}).
    2. **High Frequency:** Top 25% of customers by total sessions (> {freq_p75:.0f} sessions). *(Excludes High Revenue)*
    3. **High Energy:** Top 25% of customers by total energy consumed (> {eng_p75:.1f} kWh). *(Excludes High Rev & High Freq)*
    4. **Occasional:** Customers falling below the 75th percentile across all behavioral metrics.
    """)

sc1, sc2 = st.columns(2)
with sc1:
    fig_seg_c = px.pie(seg_summary, values='Customers', names='Segment', title="Customer Base by Segment", hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
    st.plotly_chart(fig_seg_c, use_container_width=True)
with sc2:
    fig_seg_r = px.pie(seg_summary, values='Total_Revenue', names='Segment', title="Revenue Generation by Segment", hole=0.4, color_discrete_sequence=px.colors.qualitative.Bold)
    st.plotly_chart(fig_seg_r, use_container_width=True)

st.dataframe(seg_summary[['Segment', 'Customers', '% of Total Customers', 'Total_Revenue', '% of Total Revenue', 'Avg_Sessions']].style.format({
    '% of Total Customers': '{:.1f}%',
    'Total_Revenue': '${:,.2f}',
    '% of Total Revenue': '{:.1f}%',
    'Avg_Sessions': '{:.1f}'
}), use_container_width=True, hide_index=True)

st.divider()

# --- VEHICLE INTELLIGENCE ---
st.subheader("Vehicle Intelligence")

veh_agg = sessions.groupby('vehicle_type').agg(
    Sessions=('session_id', 'count'),
    Energy_Consumption=('energy_kwh', 'sum'),
    Revenue=('revenue', 'sum'),
    Total_Duration=('duration_minutes', 'sum')
).reset_index()

veh_agg['Avg_kWh_per_Session'] = veh_agg['Energy_Consumption'] / veh_agg['Sessions']
veh_agg['Avg_Duration'] = veh_agg['Total_Duration'] / veh_agg['Sessions']
veh_agg['Avg_Revenue'] = veh_agg['Revenue'] / veh_agg['Sessions']

# Sorting for display
veh_agg = veh_agg.sort_values(by='Sessions', ascending=False)

vc1, vc2 = st.columns(2)
with vc1:
    fig_v1 = px.bar(veh_agg, x='Sessions', y='vehicle_type', orientation='h', title="Total Sessions by Vehicle Type", color='Sessions', color_continuous_scale="Viridis")
    fig_v1.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_v1, use_container_width=True)
with vc2:
    fig_v2 = px.bar(veh_agg, x='Avg_kWh_per_Session', y='vehicle_type', orientation='h', title="Average Energy (kWh) per Session", color='Avg_kWh_per_Session', color_continuous_scale="Magma")
    fig_v2.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_v2, use_container_width=True)

st.dataframe(veh_agg[['vehicle_type', 'Sessions', 'Energy_Consumption', 'Revenue', 'Total_Duration', 'Avg_kWh_per_Session']].style.format({
    'Energy_Consumption': '{:,.1f} kWh',
    'Revenue': '${:,.2f}',
    'Total_Duration': '{:,.0f} min',
    'Avg_kWh_per_Session': '{:.1f} kWh'
}), use_container_width=True, hide_index=True)
