import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

def generate_chargebyev_data():
    np.random.seed(42)
    
    # -----------------------------
    # 1. STATIONS
    # -----------------------------
    num_stations = 150
    cities = ['San Francisco', 'Los Angeles', 'San Diego', 'Sacramento', 'San Jose']
    station_types = ['Highway', 'Urban', 'Retail', 'Workplace']
    
    stations = []
    for i in range(num_stations):
        city = np.random.choice(cities, p=[0.3, 0.4, 0.15, 0.05, 0.1])
        s_type = np.random.choice(station_types, p=[0.2, 0.4, 0.3, 0.1])
        
        # Base coordinates for cities (approximate)
        if city == 'San Francisco': lat, lon = 37.77, -122.41
        elif city == 'Los Angeles': lat, lon = 34.05, -118.24
        elif city == 'San Diego': lat, lon = 32.71, -117.16
        elif city == 'Sacramento': lat, lon = 38.58, -121.49
        else: lat, lon = 37.33, -121.88
            
        lat += np.random.normal(0, 0.1)
        lon += np.random.normal(0, 0.1)
        
        # High utilization for urban/retail in SF/LA
        demand_factor = 1.0
        if city in ['San Francisco', 'Los Angeles']: demand_factor *= 1.5
        if s_type in ['Urban', 'Retail']: demand_factor *= 1.2
        if s_type == 'Highway': demand_factor *= 1.3
        if s_type == 'Workplace': demand_factor *= 0.7 # lower overall volume, just peaks
        
        total_chargers = np.random.randint(4, 20)
        
        stations.append({
            'station_id': f"STN_{i:04d}",
            'station_name': f"ChargeByEV {city} {s_type} {i}",
            'city': city,
            'area': f"{city} Metro",
            'latitude': round(lat, 4),
            'longitude': round(lon, 4),
            'total_chargers': total_chargers,
            'station_type': s_type,
            '_demand_factor': demand_factor # internal use for sessions
        })
        
    stations_df = pd.DataFrame(stations)
    
    # -----------------------------
    # 2. CHARGERS
    # -----------------------------
    chargers = []
    charger_types = ['Level 2 (AC)', 'DC Fast (50kW)', 'DC Ultra-Fast (150kW+)', 'DC Hyper-Fast (350kW)']
    
    charger_counter = 1
    for _, row in stations_df.iterrows():
        for _ in range(row['total_chargers']):
            c_type = np.random.choice(charger_types, p=[0.4, 0.3, 0.2, 0.1])
            if c_type == 'Level 2 (AC)': power = np.random.choice([7.2, 11, 22])
            elif c_type == 'DC Fast (50kW)': power = 50
            elif c_type == 'DC Ultra-Fast (150kW+)': power = 150
            else: power = 350
            
            chargers.append({
                'charger_id': f"CHG_{charger_counter:05d}",
                'station_id': row['station_id'],
                'charger_type': c_type,
                'power_kw': power,
                'installation_date': (datetime(2023, 1, 1) + timedelta(days=np.random.randint(0, 365))).strftime('%Y-%m-%d'),
                'charger_status': np.random.choice(['Active', 'Maintenance', 'Offline'], p=[0.9, 0.07, 0.03])
            })
            charger_counter += 1
            
    chargers_df = pd.DataFrame(chargers)
    
    # -----------------------------
    # 3. CHARGING SESSIONS (12 Months)
    # -----------------------------
    start_date = datetime(2024, 10, 1)
    end_date = datetime(2025, 10, 1)
    total_days = (end_date - start_date).days
    
    sessions = []
    session_counter = 1
    
    vehicle_types = ['Tesla Model 3', 'Tesla Model Y', 'Ford Mustang Mach-E', 'Chevy Bolt', 'Hyundai Ioniq 5', 'Rivian R1T', 'VW ID.4', 'Porsche Taycan', 'Nissan Leaf']
    vehicle_probs = [0.25, 0.30, 0.10, 0.08, 0.10, 0.05, 0.05, 0.02, 0.05]
    
    print("Generating sessions... this might take a minute.")
    
    chargers_list = chargers_df.to_dict('records')
    station_demand_map = {s['station_id']: (s['_demand_factor'], s['station_type']) for s in stations}
    
    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        is_weekend = current_date.weekday() >= 5
        
        # Base number of sessions for this day
        base_sessions = np.random.randint(800, 1200)
        if is_weekend:
            base_sessions = int(base_sessions * 1.3)
            
        for _ in range(base_sessions):
            charger = np.random.choice(chargers_list)
            station_id = charger['station_id']
            demand_f, s_type = station_demand_map[station_id]
            
            # Select time based on realistic commute/weekend patterns
            if is_weekend:
                # Bell curve centered around 1pm for weekends
                hour = int(np.random.normal(13, 3)) % 24
            else:
                if s_type == 'Workplace':
                    hour = int(np.random.normal(8.5, 1.0)) % 24 # morning arrival
                else:
                    # Bimodal: Morning commute and Evening
                    if np.random.random() < 0.4:
                        hour = int(np.random.normal(8, 1.5)) % 24
                    else:
                        hour = int(np.random.normal(18, 2)) % 24
                        
            minute = np.random.randint(0, 60)
            start_time = current_date.replace(hour=hour, minute=minute)
            
            # Accept or reject based on demand_factor to simulate high/low util stations
            if np.random.random() > (demand_f / 2.5):
                continue
                
            charger_id = charger['charger_id']
            power_kw = charger['power_kw']
            
            # Status
            status_prob = np.random.random()
            if status_prob < 0.90:
                session_status = 'Completed'
                payment_status = 'Paid'
            elif status_prob < 0.95:
                session_status = 'Failed'
                payment_status = 'Refunded'
            elif status_prob < 0.98:
                session_status = 'Cancelled'
                payment_status = 'Voided'
            else:
                session_status = 'Abnormal'
                payment_status = 'Pending'
                
            # Calculate metrics
            if session_status in ['Cancelled', 'Failed']:
                duration_minutes = np.random.randint(1, 10)
                energy_kwh = np.random.uniform(0, 2)
            elif session_status == 'Abnormal':
                if np.random.random() < 0.5:
                    # Camper
                    duration_minutes = np.random.randint(300, 1440)
                    energy_kwh = np.random.uniform(1, 5)
                else:
                    # Glitch
                    duration_minutes = np.random.randint(5, 15)
                    energy_kwh = np.random.uniform(200, 500)
            else:
                if power_kw <= 22:
                    duration_minutes = np.random.randint(60, 480)
                else:
                    duration_minutes = np.random.randint(15, 60)
                    
                max_energy = (power_kw * (duration_minutes / 60)) * 0.9
                energy_kwh = np.random.uniform(max_energy * 0.4, max_energy)
                energy_kwh = min(energy_kwh, 95.0)
                
            end_time = start_time + timedelta(minutes=duration_minutes)
            price_per_kwh = round(np.random.uniform(0.30, 0.65), 2)
            revenue = round(energy_kwh * price_per_kwh, 2) if session_status == 'Completed' else 0.0
            
            sessions.append({
                'session_id': f"SESSION_{session_counter:07d}",
                'station_id': station_id,
                'charger_id': charger_id,
                'customer_id': f"CUST_{np.random.randint(1, 15000):05d}",
                'vehicle_type': np.random.choice(vehicle_types, p=vehicle_probs),
                'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_minutes': int(duration_minutes),
                'energy_kwh': round(energy_kwh, 2),
                'price_per_kwh': price_per_kwh,
                'revenue': revenue,
                'session_status': session_status,
                'payment_status': payment_status
            })
            session_counter += 1

    sessions_df = pd.DataFrame(sessions)
    stations_df = stations_df.drop(columns=['_demand_factor'])
    
    print(f"Generated {len(stations_df)} stations.")
    print(f"Generated {len(chargers_df)} chargers.")
    print(f"Generated {len(sessions_df)} sessions.")
    
    stations_df.to_csv('stations.csv', index=False)
    chargers_df.to_csv('chargers.csv', index=False)
    sessions_df.to_csv('charging_sessions.csv', index=False)
    print("Files saved successfully: stations.csv, chargers.csv, charging_sessions.csv")

if __name__ == '__main__':
    generate_chargebyev_data()
