import re
with open('pages/02_Station_Intelligence.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'statuses = \["All"\] \+ sorted\(stations\[\'station_status\'\]\.unique\(\)\.tolist\(\)\)\n', '', content)
content = re.sub(r'if f_status != "All": f_stn = f_stn\[f_stn\[\'station_status\'\] == f_status\]\n?', '', content)

with open('pages/02_Station_Intelligence.py', 'w', encoding='utf-8') as f:
    f.write(content)
