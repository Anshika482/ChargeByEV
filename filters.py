import streamlit as st
import pandas as pd

import os
import generate_data

@st.cache_data
def load_all_data():
    if not os.path.exists('charging_sessions.csv'):
        print('Data not found. Generating on the fly for cloud deployment...')
        generate_data.generate_chargebyev_data()

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
    **Date:** {d_str}\n
    **City:** {f_city}\n
    **Station:** {f_stn}\n
    **Charger:** {f_ctype}\n
    **Vehicle:** {f_vtype}\n
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
