import os
import re
import shutil

# Files to migrate and clean
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

if not os.path.exists("pages"):
    os.makedirs("pages")

for src, dst in modules:
    if not os.path.exists(src):
        continue
    
    with open(src, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Inject import
    content = content.replace("import streamlit as st", "import streamlit as st" + import_injection)
    
    # 2. Find and replace the local data loading functions and the entire try/except block
    # Remove the def load_data(): block
    content = re.sub(r"@st\.cache_data.*?def load_data\(\):.*?(?=\ntry:)", "", content, flags=re.DOTALL)
    
    # Replace the try/except block cleanly
    replacement = """
try:
    stations, chargers, sessions, fs = filters.apply_global_filters()
    f_city = fs['f_city']
    f_stn = fs['f_stn']
    date_range = fs['date_range']
    f_ses = sessions.copy()
except Exception as e:
    st.error(f"Data loading error: {str(e)}")
    st.stop()
"""
    # Replace standard 3 variable unpack
    content = re.sub(r"try:\n.*?stations, chargers, sessions = load_data\(\).*?st\.stop\(\)\n", replacement, content, flags=re.DOTALL)
    # Replace 1 variable unpack
    content = re.sub(r"try:\n.*?sessions = load_data\(\).*?st\.stop\(\)\n", replacement, content, flags=re.DOTALL)

    # 3. Strip out the local UI sidebar filter elements, but LEAVE the variables intact 
    # so we don't break local page logic that relies on them!
    
    # Remove the sidebar headers
    content = re.sub(r"st\.sidebar\.header\(\"Global Filters\"\)\n?", "", content)
    content = re.sub(r"st\.sidebar\.header\(\"Filters\"\)\n?", "", content)
    content = re.sub(r"st\.sidebar\.header\(\"Spatial Filters\"\)\n?", "", content)
    
    # Remove date range inputs
    content = re.sub(r"min_d = .*?\n", "", content)
    content = re.sub(r"max_d = .*?\n", "", content)
    content = re.sub(r"date_range = st\.sidebar\.date_input\([^)]*\)\n?", "", content)
    
    # Remove city inputs
    content = re.sub(r"cities = \[\"All.*?\]\n", "", content)
    content = re.sub(r"f_city = st\.sidebar\.selectbox\(\"City\", cities\)\n?", "", content)
    content = re.sub(r"f_city = st\.sidebar\.selectbox\(\"City\", \[\"All.*?\]\)\n?", "", content)
    
    # Remove station inputs
    content = re.sub(r"stn_list = \[\"All.*?\]\n", "", content)
    content = re.sub(r"f_stn = st\.sidebar\.selectbox\(\"Station\", stn_list\)\n?", "", content)

    # Remove the manual date filtering loops
    content = re.sub(r"if len\(date_range\) == 2:.*?\n\s+f_ses = f_ses\[.*?\]\n", "", content, flags=re.DOTALL)
    content = re.sub(r"f_ses = sessions\.copy\(\)\n?", "", content)
    content = re.sub(r"if f_city != \"All\" and f_city != \"All Network\":.*?\n\s+f_ses = f_ses\[.*?\]\n", "", content, flags=re.DOTALL)
    
    # Fix empty check block
    content = re.sub(r"if len\(f_ses\) == 0:\n\s*st\.warning\([^)]*\)\n\s*st\.stop\(\)", "if len(f_ses) == 0:\\n    st.warning('No data matches the global filters.')\\n    st.stop()", content)

    # Write output to pages
    with open(os.path.join('pages', dst), 'w', encoding='utf-8') as f:
        f.write(content)

print("Clean refactor completed successfully.")
