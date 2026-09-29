import os
import re

# 1. Update filters.py to return enriched data and filter state
filters_code = '''import streamlit as st
import pandas as pd

@st.cache_data
def load_all_data():
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    sessions['start_time'] = pd.to_datetime(sessions['start_time'])
    sessions['end_time'] = pd.to_datetime(sessions['end_time'])
    sessions['date'] = sessions['start_time'].dt.date
    sessions['hour'] = sessions['start_time'].dt.hour
    if 'day_of_week' not in sessions.columns:
        sessions['day_of_week'] = sessions['start_time'].dt.day_name()
    if 'month' not in sessions.columns:
        sessions['month'] = sessions['start_time'].dt.month_name()
    if 'is_weekend' not in sessions.columns:
        sessions['is_weekend'] = sessions['start_time'].dt.dayofweek >= 5
    
    # Enrich sessions for all downstream tasks
    if 'station_name' not in sessions.columns:
        sessions = sessions.merge(stations[['station_id', 'station_name', 'city']], on='station_id', how='left', suffixes=('', '_drop'))
        sessions = sessions.loc[:, ~sessions.columns.str.endswith('_drop')]
    if 'charger_type' not in sessions.columns:
        sessions = sessions.merge(chargers[['charger_id', 'charger_type']], on='charger_id', how='left', suffixes=('', '_drop'))
        sessions = sessions.loc[:, ~sessions.columns.str.endswith('_drop')]

    return stations, chargers, sessions

def apply_global_filters():
    stations, chargers, sessions = load_all_data()

    st.sidebar.header("🌍 Global Filters")
    
    if st.sidebar.button("Reset Filters"):
        for key in ['f_date', 'f_city', 'f_stn', 'f_ctype', 'f_vtype', 'f_sstatus']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    min_d = sessions['date'].min()
    max_d = sessions['date'].max()
    
    date_range = st.sidebar.date_input("Date Range", [min_d, max_d], min_value=min_d, max_value=max_d, key='f_date')
    
    cities = ["All"] + sorted(stations['city'].unique().tolist())
    f_city = st.sidebar.selectbox("City", cities, key='f_city')
    
    stn_list = ["All Network"] + sorted(stations['station_id'].unique().tolist())
    f_stn = st.sidebar.selectbox("Station", stn_list, key='f_stn')
    
    ctypes = ["All"] + sorted(chargers['charger_type'].unique().tolist())
    f_ctype = st.sidebar.selectbox("Charger Type", ctypes, key='f_ctype')
    
    vtypes = ["All"] + sorted(sessions['vehicle_type'].unique().tolist())
    f_vtype = st.sidebar.selectbox("Vehicle Type", vtypes, key='f_vtype')
    
    statuses = ["All"] + sorted(sessions['session_status'].unique().tolist())
    f_sstatus = st.sidebar.selectbox("Session Status", statuses, key='f_sstatus')

    st.sidebar.markdown("### Active Filter State:")
    d_str = f"{date_range[0]} to {date_range[1]}" if len(date_range) == 2 else str(date_range[0])
    st.sidebar.info(f"""
    **Date:** {d_str}\\n
    **City:** {f_city}\\n
    **Station:** {f_stn}\\n
    **Charger:** {f_ctype}\\n
    **Vehicle:** {f_vtype}\\n
    **Status:** {f_sstatus}
    """)
    
    f_ses = sessions.copy()
    if len(date_range) == 2:
        f_ses = f_ses[(f_ses['date'] >= date_range[0]) & (f_ses['date'] <= date_range[1])]
    if f_city != "All":
        f_ses = f_ses[f_ses['city'] == f_city]
    if f_stn != "All Network" and f_stn != "All":
        f_ses = f_ses[f_ses['station_id'] == f_stn]
    if f_ctype != "All":
        f_ses = f_ses[f_ses['charger_type'] == f_ctype]
    if f_vtype != "All":
        f_ses = f_ses[f_ses['vehicle_type'] == f_vtype]
    if f_sstatus != "All":
        f_ses = f_ses[f_ses['session_status'] == f_sstatus]
        
    fs = {
        'date_range': date_range,
        'f_city': f_city,
        'f_stn': f_stn,
        'f_ctype': f_ctype,
        'f_vtype': f_vtype,
        'f_sstatus': f_sstatus
    }
    return stations, chargers, f_ses, fs
'''

with open('filters.py', 'w', encoding='utf-8') as f:
    f.write(filters_code)


modules = [
    ("command_center.py", "01_Network_Command_Center.py"),
    ("station_intelligence.py", "02_Station_Intelligence.py"),
    ("demand_intelligence.py", "03_Demand_Intelligence.py"),
    ("charger_anomaly_monitor.py", "04_Charger_Health.py"),
    ("revenue_intelligence.py", "05_Revenue_Intelligence.py"),
    ("geo_intelligence.py", "06_Geo_Intelligence.py"),
    ("capacity_simulator.py", "07_Capacity_Simulator.py"),
    ("customer_intelligence.py", "08_Customer_Intelligence.py"),
    ("executive_insights.py", "10_Executive_Insights.py")
]

import_injection = """
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import filters
"""

for src, dst in modules:
    if not os.path.exists(src):
        continue
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Inject import
    content = content.replace("import streamlit as st", "import streamlit as st" + import_injection)
    
    # 2. Remove local load_data block completely
    content = re.sub(r"@st\.cache_data.*?def load_data\(\):.*?(?=\ntry:)", "", content, flags=re.DOTALL)
    
    # 3. Replace try/except load_data block with the filters unpack
    replacement = """
try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs['f_city']
    f_stn = fs['f_stn']
    date_range = fs['date_range']
    f_ses = sessions.copy()
"""
    content = re.sub(r"try:\n.*?stations, chargers, sessions = load_data\(\).*?st\.stop\(\)\n", replacement, content, flags=re.DOTALL)
    
    # Some modules just used: sessions = load_data()
    content = re.sub(r"try:\n.*?sessions = load_data\(\).*?st\.stop\(\)\n", replacement, content, flags=re.DOTALL)
    
    # 4. Remove ONLY the sidebar logic, but leave everything else alone.
    content = re.sub(r"st\.sidebar\.header\(\"Global Filters\"\).*?(?=\n\w|\n# ---)", "", content, flags=re.DOTALL)
    content = re.sub(r"st\.sidebar\.header\(\"Filters\"\).*?(?=\n\w|\n# ---)", "", content, flags=re.DOTALL)
    content = re.sub(r"st\.sidebar\.header\(\"Spatial Filters\"\).*?(?=\n\w|\n# ---)", "", content, flags=re.DOTALL)
    
    # Specific targeted removals for the date and basic filters
    content = re.sub(r"min_d = sessions\['date'\].min\(\)\nmax_d = sessions\['date'\].max\(\)\n", "", content)
    content = re.sub(r"date_range = st\.sidebar\.date_input\([^)]*\)\n", "", content)
    content = re.sub(r"cities = \[.*?\]\n", "", content)
    content = re.sub(r"f_city = st\.sidebar\.selectbox\([^)]*\)\n", "", content)
    content = re.sub(r"f_stn = st\.sidebar\.selectbox\([^)]*\)\n", "", content)
    content = re.sub(r"f_stn = st\.sidebar\.selectbox\([^)]*\)", "", content)

    # Some custom removals for local filtering logic that applied f_ses = ...
    content = re.sub(r"f_ses = sessions\.copy\(\)\nif len\(date_range\) == 2:.*?f_ses = f_ses\[f_ses\['station_id'\].*?\]\n", "", content, flags=re.DOTALL)
    content = re.sub(r"f_ses = sessions\.copy\(\)\nif len\(date_range\) == 2:.*?f_ses = sessions\n", "", content, flags=re.DOTALL)
    content = re.sub(r"if len\(date_range\) == 2:.*?f_ses = f_ses\[f_ses\['station_id'\].*?\]\n", "", content, flags=re.DOTALL)

    # Clean up empty data stops
    content = re.sub(r"if len\(f_ses\) == 0:\n\s*st\.warning\([^)]*\)\n\s*st\.stop\(\)", "if len(f_ses) == 0:\n    st.warning('No data in this range.')\n    st.stop()", content)

    with open(os.path.join('pages', dst), 'w', encoding='utf-8') as f:
        f.write(content)

print("Fix completed.")
