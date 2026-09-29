import os

# 06_Geo_Intelligence.py
with open('pages/06_Geo_Intelligence.py', 'r', encoding='utf-8') as f:
    c = f.read()
if 'f_util = 0' not in c:
    c = c.replace('f_data = merged.copy()', 'f_util = 0\nf_rev = 0\nf_fail = 0\nf_data = merged.copy()')
with open('pages/06_Geo_Intelligence.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 04_Charger_Health.py
with open('pages/04_Charger_Health.py', 'r', encoding='utf-8') as f:
    c = f.read()
if "f_sev = ['Critical', 'High', 'Moderate']" not in c:
    c = c.replace('if not anomaly_df.empty and len(f_sev) > 0:', "f_sev = ['Critical', 'High', 'Moderate']\nif not anomaly_df.empty and len(f_sev) > 0:")
with open('pages/04_Charger_Health.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 07_Capacity_Simulator.py
with open('pages/07_Capacity_Simulator.py', 'r', encoding='utf-8') as f:
    c = f.read()
if 'selected_stn =' not in c:
    patch = """
if f_stn != "All Network" and f_stn != "All":
    selected_stn = f_stn
else:
    selected_stn = merged['station_id'].iloc[0] if len(merged) > 0 else None
if not selected_stn:
"""
    c = c.replace('if not selected_stn:', patch)
with open('pages/07_Capacity_Simulator.py', 'w', encoding='utf-8') as f:
    f.write(c)
