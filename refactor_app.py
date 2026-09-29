import os
import re
import shutil

if not os.path.exists("pages"):
    os.makedirs("pages")

# Create filters.py
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
    
    stn_list = ["All"] + sorted(stations['station_id'].unique().tolist())
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
    **Date:** {d_str}  
    **City:** {f_city}  
    **Station:** {f_stn}  
    **Charger:** {f_ctype}  
    **Vehicle:** {f_vtype}  
    **Status:** {f_sstatus}
    """)
    
    f_ses = sessions.copy()
    if len(date_range) == 2:
        f_ses = f_ses[(f_ses['date'] >= date_range[0]) & (f_ses['date'] <= date_range[1])]
    if f_city != "All":
        valid_stns = stations[stations['city'] == f_city]['station_id']
        f_ses = f_ses[f_ses['station_id'].isin(valid_stns)]
    if f_stn != "All":
        f_ses = f_ses[f_ses['station_id'] == f_stn]
    if f_ctype != "All":
        valid_chg = chargers[chargers['charger_type'] == f_ctype]['charger_id']
        f_ses = f_ses[f_ses['charger_id'].isin(valid_chg)]
    if f_vtype != "All":
        f_ses = f_ses[f_ses['vehicle_type'] == f_vtype]
    if f_sstatus != "All":
        f_ses = f_ses[f_ses['session_status'] == f_sstatus]
        
    return stations, chargers, f_ses
'''
with open('filters.py', 'w', encoding='utf-8') as f:
    f.write(filters_code)

# Create main entrypoint app.py
app_code = '''import streamlit as st
st.set_page_config(page_title="ChargeByEV NOC", layout="wide", page_icon="⚡")

st.title("⚡ ChargeByEV Network Operations Center")
st.markdown("""
Welcome to the unified ChargeByEV Operations Platform.
Please select a module from the sidebar to begin analyzing the network.

All modules share a unified global filter state!
""")
'''
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(app_code)

modules = [
    ("command_center.py", "01_Command_Center.py"),
    ("station_intelligence.py", "02_Station_Intelligence.py"),
    ("demand_intelligence.py", "03_Demand_Intelligence.py"),
    ("charger_anomaly_monitor.py", "04_Charger_Anomaly_Monitor.py"),
    ("revenue_intelligence.py", "05_Revenue_Intelligence.py"),
    ("geo_intelligence.py", "06_Geo_Intelligence.py"),
    ("capacity_simulator.py", "07_Capacity_Simulator.py"),
    ("customer_intelligence.py", "08_Customer_Intelligence.py"),
    ("executive_insights.py", "09_Executive_Insights.py")
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

    # We need to replace the @st.cache_data load_data() block and the try/except block.
    # And replace it with our global filter fetch.
    
    # 1. Inject import
    content = content.replace("import streamlit as st", "import streamlit as st" + import_injection)
    
    # 2. Find and replace load_data block
    # This regex is a bit tricky, let's just use string slicing
    
    # Let's try to remove everything between @st.cache_data and st.stop()
    # or just find "try:" and remove until "st.stop()\n"
    import re
    # Remove load_data def
    content = re.sub(r"@st\.cache_data.*?def load_data\(\):.*?(?=\ntry:)", "", content, flags=re.DOTALL)
    
    # Remove try/except block
    content = re.sub(r"try:.*?st\.stop\(\)\n", "stations, chargers, sessions = filters.apply_global_filters()\nf_ses = sessions.copy()\n", content, flags=re.DOTALL)
    
    # Remove any sidebar.header("Global Filters") and anything date related
    content = re.sub(r"st\.sidebar\.header\(\"Global Filters\"\).*?(?=\n#|\nst\.)", "", content, flags=re.DOTALL)
    content = re.sub(r"st\.sidebar\.header\(\"Filters\"\).*?(?=\n#|\nst\.)", "", content, flags=re.DOTALL)
    content = re.sub(r"st\.sidebar\.header\(\"Spatial Filters\"\).*?(?=\n#|\nst\.)", "", content, flags=re.DOTALL)
    content = re.sub(r"min_d = .*?f_ses = f_ses\[f_ses.*?\n", "", content, flags=re.DOTALL)
    content = re.sub(r"if len\(date_range\).*?else:\n\s*f_ses = sessions\n", "", content, flags=re.DOTALL)

    # Some files use `sessions` directly instead of `f_ses` for the rest of the code, so we should map sessions back to f_ses if they do.
    # Or just globally rename `f_ses` back to `sessions` if they used `sessions` originally.
    
    with open(os.path.join('pages', dst), 'w', encoding='utf-8') as f:
        f.write(content)
        
print("Migration completed.")
