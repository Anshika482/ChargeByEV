import os

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
        lines = f.readlines()
        
    out_lines = []
    skip_mode = False
    
    for i, line in enumerate(lines):
        if "import streamlit as st" in line:
            out_lines.append(line)
            out_lines.append(import_injection)
            continue
            
        # Strip the local load_data function entirely
        if "@st.cache_data" in line and i+1 < len(lines) and "def load_data():" in lines[i+1]:
            skip_mode = "load_data"
            continue
            
        if skip_mode == "load_data":
            if line.startswith("try:"):
                skip_mode = False
            else:
                continue
                
        # Replace the try block
        if line.startswith("try:") and (i+1 < len(lines) and "load_data()" in lines[i+1]):
            # Inject new block
            out_lines.append("try:\n")
            out_lines.append("    stations, chargers, sessions, fs = filters.apply_global_filters()\n")
            out_lines.append("    f_city = fs.get('f_city', 'All')\n")
            out_lines.append("    f_stn = fs.get('f_stn', 'All Network')\n")
            out_lines.append("    date_range = fs.get('date_range', [])\n")
            out_lines.append("    f_ses = sessions.copy()\n")
            skip_mode = "try_block"
            continue
            
        if skip_mode == "try_block":
            if line.startswith("except Exception"):
                out_lines.append(line)
                skip_mode = False
            continue
            
        # Eliminate all sidebar elements so they don't overwrite our globals
        if "st.sidebar" in line:
            continue
            
        # Eliminate any manual date filtering logic 
        if "if len(date_range) == 2:" in line or "f_ses = f_ses[(f_ses['date']" in line or "min_d =" in line or "max_d =" in line:
            continue
            
        # Eliminate any manual city filtering logic that overwrites f_ses
        if "f_ses = f_ses[f_ses['city'] ==" in line or "f_stn_ids =" in line or "f_ses = f_ses[f_ses['station_id'].isin(f_stn_ids)]" in line:
            continue
            
        # Eliminate f_ses = sessions.copy() if it appears later in the file
        if "f_ses = sessions.copy()" in line and skip_mode == False:
            continue
            
        # Eliminate duplicate cities and stn_list definitions
        if 'cities = ["All"] +' in line or 'stn_list = ["All Network"] +' in line or 'stn_list = ["All"] +' in line:
            continue
            
        out_lines.append(line)
        
    with open(os.path.join('pages', dst), 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

print("Final patch applied.")
