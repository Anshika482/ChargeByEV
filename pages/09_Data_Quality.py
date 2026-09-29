import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Data Quality Validation", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .dq-card { background-color: #1E1E1E;
        color: #E0E0E0; padding: 20px; border-radius: 8px; border-left: 4px solid #F44336; margin-bottom: 15px; }
    .dq-card.clean { border-left-color: #4CAF50; }
    .dq-card.warning { border-left-color: #FF9800; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Data Quality Validation Layer")
st.markdown("Automated integrity checks across all relational tables. Problematic records are explicitly flagged, not silently discarded.")

@st.cache_data
def load_raw_data():
    # Load raw without applying global filters because DQ checks apply to the entire database structure
    stations = pd.read_csv('stations.csv')
    chargers = pd.read_csv('chargers.csv')
    sessions = pd.read_csv('charging_sessions.csv')
    return stations, chargers, sessions

try:
    stations, chargers, sessions = load_raw_data()
except Exception as e:
    st.error(f"Data missing: {str(e)}")
    st.stop()

st.subheader("Data Integrity Scan Report")

# --- EXECUTE VALIDATION RULES ---
total_records = len(sessions)
invalid_indices = set()
warnings = []

# 1. Missing Values
missing_val_mask = sessions.isnull().any(axis=1)
missing_count = missing_val_mask.sum()
if missing_count > 0:
    invalid_indices.update(sessions[missing_val_mask].index)
    warnings.append({
        'Rule': 'Missing Values',
        'Violations': missing_count,
        'Description': 'Rows containing at least one NULL/NaN value in critical columns.'
    })

# 2. Duplicate Sessions
dup_mask = sessions.duplicated(subset=['session_id'], keep=False)
dup_count = dup_mask.sum()
if dup_count > 0:
    invalid_indices.update(sessions[dup_mask].index)
    warnings.append({
        'Rule': 'Duplicate Sessions',
        'Violations': dup_count,
        'Description': 'Multiple rows sharing the exact same primary key (session_id).'
    })

# 3. Invalid Timestamps (Start > End)
sessions['temp_start'] = pd.to_datetime(sessions['start_time'], errors='coerce')
sessions['temp_end'] = pd.to_datetime(sessions['end_time'], errors='coerce')
time_mask = sessions['temp_start'] >= sessions['temp_end']
time_count = time_mask.sum()
if time_count > 0:
    invalid_indices.update(sessions[time_mask].index)
    warnings.append({
        'Rule': 'Invalid Timestamps',
        'Violations': time_count,
        'Description': 'Session start_time is logically after or equal to the end_time.'
    })

# 4. Negative Energy
energy_mask = sessions['energy_kwh'] < 0
energy_count = energy_mask.sum()
if energy_count > 0:
    invalid_indices.update(sessions[energy_mask].index)
    warnings.append({
        'Rule': 'Negative Energy',
        'Violations': energy_count,
        'Description': 'Session recorded energy delivered as a negative value (< 0 kWh).'
    })

# 5. Negative Revenue
rev_mask = sessions['revenue'] < 0
rev_count = rev_mask.sum()
if rev_count > 0:
    invalid_indices.update(sessions[rev_mask].index)
    warnings.append({
        'Rule': 'Negative Revenue',
        'Violations': rev_count,
        'Description': 'Session recorded revenue as a negative value (< $0.00).'
    })

# 6. Impossible Durations (<= 0)
dur_mask = sessions['duration_minutes'] <= 0
dur_count = dur_mask.sum()
if dur_count > 0:
    invalid_indices.update(sessions[dur_mask].index)
    warnings.append({
        'Rule': 'Impossible Durations',
        'Violations': dur_count,
        'Description': 'Session recorded a duration of 0 or negative minutes.'
    })

# 7. Invalid Station IDs (Session reference doesn't exist in Station table)
valid_stn_ids = set(stations['station_id'])
inv_stn_mask = ~sessions['station_id'].isin(valid_stn_ids)
inv_stn_count = inv_stn_mask.sum()
if inv_stn_count > 0:
    invalid_indices.update(sessions[inv_stn_mask].index)
    warnings.append({
        'Rule': 'Invalid Station IDs',
        'Violations': inv_stn_count,
        'Description': 'Session references a station_id that does not exist in the master stations table.'
    })

# 8. Invalid Charger IDs (Session reference doesn't exist in Charger table)
valid_chg_ids = set(chargers['charger_id'])
inv_chg_mask = ~sessions['charger_id'].isin(valid_chg_ids)
inv_chg_count = inv_chg_mask.sum()
if inv_chg_count > 0:
    invalid_indices.update(sessions[inv_chg_mask].index)
    warnings.append({
        'Rule': 'Invalid Charger IDs',
        'Violations': inv_chg_count,
        'Description': 'Session references a charger_id that does not exist in the master chargers table.'
    })

# 9. Orphan Records (Charger associated with Station that doesn't exist)
orphan_chargers_mask = ~chargers['station_id'].isin(valid_stn_ids)
orphan_chg_count = orphan_chargers_mask.sum()
if orphan_chg_count > 0:
    warnings.append({
        'Rule': 'Orphan Chargers',
        'Violations': orphan_chg_count,
        'Description': 'Chargers table contains hardware mapped to a station_id that does not exist in the stations table.'
    })

# 10. Inconsistent Charger/Station Relationships
# e.g., session says station X and charger Y. But chargers table says charger Y belongs to station Z.
chg_stn_map = dict(zip(chargers['charger_id'], chargers['station_id']))
sessions['expected_station_id'] = sessions['charger_id'].map(chg_stn_map)
inconsistent_mask = (sessions['station_id'] != sessions['expected_station_id']) & (sessions['expected_station_id'].notnull())
inconsistent_count = inconsistent_mask.sum()
if inconsistent_count > 0:
    invalid_indices.update(sessions[inconsistent_mask].index)
    warnings.append({
        'Rule': 'Inconsistent Architecture (Relational Mismatch)',
        'Violations': inconsistent_count,
        'Description': 'Session assigns a charger to a station, but the master charger table maps that charger to a different station.'
    })

# --- RENDER TOP METRICS ---
invalid_records = len(invalid_indices)
valid_records = total_records - invalid_records
valid_pct = (valid_records / total_records) * 100 if total_records > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f"<div class='dq-card {'clean' if total_records>0 else ''}'><b>Total Records</b><br><span style='font-size:24px;'>{total_records:,}</span></div>", unsafe_allow_html=True)
with c2: st.markdown(f"<div class='dq-card clean'><b>Valid Records</b><br><span style='font-size:24px;'>{valid_records:,} ({valid_pct:.1f}%)</span></div>", unsafe_allow_html=True)
with c3: st.markdown(f"<div class='dq-card {'clean' if invalid_records==0 else ''}'><b>Invalid Records</b><br><span style='font-size:24px;'>{invalid_records:,}</span></div>", unsafe_allow_html=True)
with c4: st.markdown(f"<div class='dq-card {'clean' if len(warnings)==0 else 'warning'}'><b>Validation Warnings</b><br><span style='font-size:24px;'>{len(warnings)} Triggered</span></div>", unsafe_allow_html=True)

st.divider()

# --- WARNING LOG ---
st.subheader("Validation Warnings Log")
if len(warnings) > 0:
    warn_df = pd.DataFrame(warnings)
    st.dataframe(warn_df.style.format({'Violations': '{:,}'}), use_container_width=True, hide_index=True)
else:
    st.success("🎉 Database passed all structural and logical integrity checks! Zero warnings triggered.")

st.write("")
with st.expander("ℹ️ Transparency: Data Cleaning & Documentation Rules"):
    st.markdown("""
    **Zero-Destruction Policy:** Problematic records are explicitly flagged in this report, but they are **never silently removed** from the database. Deleting rows without a trace fundamentally corrupts operational reality and destroys the audit trail.
    
    The engine executes the following logic checks against the raw `.csv` schemas:
    
    1. **Missing Values:** Scans `charging_sessions` for any row containing a NULL/NaN value in any field.
    2. **Duplicate Sessions:** Validates the primary key constraint on `session_id`.
    3. **Invalid Timestamps:** Validates that the flow of time moves forward (End Time must strictly be > Start Time).
    4. **Negative Energy:** Flags violations of physical reality (energy delivered cannot be < 0 kWh).
    5. **Negative Revenue:** Flags violations of financial integrity (a session cannot cost < $0.00 unless explicitly flagged as a Refund status, which is not tracked via negative numbers in this schema).
    6. **Impossible Durations:** Flags sessions calculating at 0 or negative minutes.
    7. **Invalid Station IDs (Foreign Key Check):** Ensures every station billed in the sessions table physically exists in the `stations` master table.
    8. **Invalid Charger IDs (Foreign Key Check):** Ensures every charger billed in the sessions table physically exists in the `chargers` master table.
    9. **Orphan Records (Relational Integrity):** Validates that no charger hardware is assigned to a ghost station.
    10. **Inconsistent Charger/Station Mapping:** A cross-reference check to ensure a session didn't accidentally bill Charger #105 to Station A, when the hardware table dictates Charger #105 is permanently bolted to the ground at Station B.
    """)
