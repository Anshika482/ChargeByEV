# ⚡ ChargeByEV: EV Network Operations Center (NOC)

![ChargeByEV Platform](https://via.placeholder.com/1200x600?text=ChargeByEV+Dashboard+Screenshot)

## 1. Project Overview
**ChargeByEV** is a production-grade Network Operations Center (NOC) and analytical platform designed for Electric Vehicle (EV) charging operators. It transforms raw transactional telemetry into actionable operational intelligence. Rather than functioning as a standard BI reporting tool, ChargeByEV is engineered to actively monitor hardware health, spatial demand, capacity pressure, and network revenue streams in real-time.

## 2. Business Problem
As EV adoption accelerates, charging network operators face acute infrastructure bottlenecks. Operating blindly leads to stranded capital (underutilized stations), severe grid/hardware degradation (overloaded stations), and terrible customer experiences (high failure rates and long queues). Operators need a deterministic, transparent engine to monitor their physical assets, segment their customers, and safely simulate hardware capacity expansions without relying on opaque "black-box" AI predictions.

## 3. Key Questions Answered
1. How is the entire charging network performing financially and operationally?
2. Which stations are healthy, overloaded, underutilized, or posing a hardware risk?
3. When and where does peak spatial-temporal demand occur?
4. Which individual chargers show abnormal statistical behavior (e.g., campers or failures)?
5. Where should the operator deploy capital to add charging capacity?

---

## 4. Dataset Architecture
The platform is built on top of a highly realistic, synthetic relational database mapping 12 months of telemetry. 
* **Stations Table:** 150 unique sites.
* **Chargers Table:** 1,761 physical chargers (AC and DC Fast).
* **Sessions Table:** ~250,000 charging sessions containing time, energy, and revenue parameters.

## 5. Data Dictionary

### `stations.csv`
| Column | Type | Description |
|--------|------|-------------|
| `station_id` | String | Primary Key. Unique identifier for the station. |
| `station_name`| String | Human-readable name. |
| `city` | String | Metropolitan location. |
| `area` | String | Specific neighborhood or zone. |
| `latitude` / `longitude` | Float | Geospatial coordinates. |
| `total_chargers` | Integer | Total hardware stalls physically present. |
| `station_type` | String | e.g., Highway, Urban, Retail, Workplace. |

### `chargers.csv`
| Column | Type | Description |
|--------|------|-------------|
| `charger_id` | String | Primary Key. Unique identifier for the charger. |
| `station_id` | String | Foreign Key linking to `stations.csv`. |
| `charger_type`| String | Standard AC (Level 2) or DC Fast. |
| `power_kw` | Float | Max throughput capability. |
| `charger_status`| String | Active, Maintenance, or Offline. |

### `charging_sessions.csv`
| Column | Type | Description |
|--------|------|-------------|
| `session_id` | String | Primary Key. |
| `station_id` | String | Foreign Key. |
| `charger_id` | String | Foreign Key. |
| `customer_id` | String | Unique user ID. |
| `vehicle_type` | String | Make/Model class. |
| `start_time` / `end_time` | Datetime | Temporal bounds of the session. |
| `energy_kwh` | Float | Total energy delivered. |
| `revenue` | Float | Gross revenue generated. |
| `session_status`| String | Completed, Cancelled, or Failed. |

---

## 6. Data Cleaning & Quality Assurance
The platform includes a dedicated, non-destructive **Data Quality Validation Layer**. 
* **Zero-Destruction Policy:** Problematic records are explicitly flagged in a warning log, but *never* silently deleted to preserve audit trails.
* **Rules Engine:** Scans for NULLs, duplicate primary keys, inverted timestamps, negative energy/revenue, orphan hardware, and relational foreign-key mismatches.

## 7. SQL Analytics Layer
The repository includes `analytics_layer.sql`, a production-ready PostgreSQL/BigQuery dialect script containing 12 heavily structured queries using `CTEs`, `Window Functions`, and `CASE` statements to pre-calculate KPIs, establish cumulative financial running totals, and execute database-level anomaly flagging.

---

## 8. Analytical Methodology: Metric Classifications

To ensure total transparency, the dashboard rigorously classifies its metrics:

* **Observed Metrics:** Hard mathematical facts extracted directly from raw telemetry (e.g., *Total Revenue, Sessions, Unique Customers*).
* **Derived Metrics:** Ratios and aggregations calculated using standard deterministic math (e.g., *Average Utilization Rate, Failure Rate %*).
* **Anomaly Signals:** Statistical deviations identified via Explainable AI methods (IQR). These are explicitly labeled as *Potential Anomalies*, not confirmed failures.
* **Scenario Estimates:** Deterministic recalculations of historical baseline metrics designed to stress-test capacity expansions. *They are not forward-looking predictive forecasts.*

## 9. Charging Pressure Index (CPI) Methodology
A custom, derived operational metric (0-100 scale) that quantifies hardware strain without opaque AI weighting.
* **Utilization Pressure (35%):** Normalized average duration vs. hardware limits.
* **Peak Demand Pressure (25%):** The intensity of a station's busiest hour vs. its baseline average hour.
* **Queue/Turnover Pressure (20%):** Raw sessions per charger per day.
* **Failure Pressure (20%):** Hardware unreliability penalty.
*(0-25 = Low Pressure | 76-100 = Critical Pressure)*

## 10. Anomaly Detection Methodology
Detected using the **Interquartile Range (IQR)** and trailing 15-day rolling differentials.
* **Campers:** Duration exceeds Q3 + 3*IQR, but Energy Delivered is < 2.0 kWh.
* **Sudden Drops:** Flags chargers whose trailing 15-day utilization or revenue collapses by > 60% against the preceding 15 days.
* **Hardware Failure Risk:** Flags chargers whose specific failure rate exceeds the Q3 + 1.5*IQR threshold of the network average.

## 11. Capacity Simulator Assumptions
An interactive stress-testing module that simulates dropping in +1 to +5 new chargers at a site.
* **Static Demand:** Total historical session volume remains completely constant (does not assume induced demand).
* **Linear Load Balancing:** Simulated chargers instantly inherit an equal share of historical traffic.

---

## 12. Dashboard Screenshots

*(Note: Replace placeholders with actual environment screenshots)*
* `![Network Command Center](docs/command_center.png)`
* `![Geo Intelligence Map](docs/geo_map.png)`
* `![Revenue Matrix](docs/revenue_matrix.png)`

## 13. Technology Stack
* **Language:** Python 3.10+
* **Frontend Framework:** Streamlit (Native Multipage Architecture)
* **Data Manipulation:** Pandas, NumPy
* **Data Visualization:** Plotly Express, Plotly Graph Objects (using MapLibre `px.scatter_map`)
* **Analytics Layer:** Standard SQL

## 14. Project Architecture
```text
├── app.py                      # Main entrypoint and navigation
├── filters.py                  # Centralized global filter engine
├── generate_data.py            # Synthetic 12-month data generator
├── analytics_layer.sql         # BigQuery/Postgres analytical queries
├── .streamlit/
│   └── config.toml             # Custom Dark Mode UI configuration
├── pages/
│   ├── 01_Network_Command_Center.py
│   ├── 02_Station_Intelligence.py
│   ├── 03_Demand_Intelligence.py
│   ├── 04_Charger_Health.py
│   ├── 05_Revenue_Intelligence.py
│   ├── 06_Geo_Intelligence.py
│   ├── 07_Capacity_Simulator.py
│   ├── 08_Customer_Intelligence.py
│   ├── 09_Data_Quality.py
│   └── 10_Executive_Insights.py
└── README.md
```

## 15. How to Run Locally
1. Clone the repository.
2. Install requirements: `pip install streamlit pandas numpy plotly`
3. Generate the database: `python generate_data.py` (Creates the 3 CSV files)
4. Launch the NOC: `streamlit run app.py`

## 16. Deployment Instructions
The application is purely stateless and can be immediately deployed to any containerized environment or PaaS:
* **Streamlit Community Cloud:** Connect your GitHub repo and point the main file path to `app.py`.
* **Google Cloud Run / AWS Fargate:** Write a standard `Dockerfile` exposing port `8501`, build the image, and deploy. 

## 17. Limitations
* The platform currently reads from static `.csv` snapshots. In a production environment, `filters.py` must be refactored to execute live queries against a remote Data Warehouse (e.g., BigQuery) to prevent memory exhaustion on massive datasets.
* Geographic clustering relies entirely on hard-coded `area` tags rather than dynamic real-time spatial clustering algorithms like DBSCAN.

## 18. Future Improvements
* **Live Streaming Integration:** Connect to OCPP (Open Charge Point Protocol) webhooks for sub-second, real-time hardware status updates.
* **Pricing Elasticity Engine:** Expand the Capacity Simulator to model how dynamic, time-of-use pricing structures might smooth out the Peak Demand curves.
* **Predictive Maintenance (ML):** Integrate an actual Machine Learning pipeline to forecast hardware failures *before* they occur, upgrading the platform from diagnostic statistical anomalies to true predictive analytics.
