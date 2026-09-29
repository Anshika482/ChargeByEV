-- =====================================================================
-- CHARGEBYEV SQL ANALYTICS LAYER
-- Database: PostgreSQL / BigQuery Dialect
-- Target Tables: stations, chargers, charging_sessions
-- =====================================================================

-- ---------------------------------------------------------------------
-- 1. Network KPIs
-- Business Purpose: Provides a high-level executive summary of the 
-- entire charging network's historical performance, success rates,
-- and absolute financial yield.
-- ---------------------------------------------------------------------
WITH session_metrics AS (
    SELECT 
        COUNT(session_id) AS total_sessions,
        SUM(CASE WHEN session_status = 'Completed' THEN 1 ELSE 0 END) AS successful_sessions,
        SUM(energy_kwh) AS total_energy_kwh,
        SUM(revenue) AS total_revenue_usd,
        AVG(duration_minutes) AS avg_duration_minutes
    FROM charging_sessions
)
SELECT 
    total_sessions,
    total_energy_kwh,
    total_revenue_usd,
    avg_duration_minutes,
    (total_revenue_usd / NULLIF(successful_sessions, 0)) AS avg_revenue_per_session,
    (successful_sessions * 100.0 / NULLIF(total_sessions, 0)) AS network_success_rate
FROM session_metrics;


-- ---------------------------------------------------------------------
-- 2. Station Performance
-- Business Purpose: Aggregates lifetime session data to measure the 
-- absolute transaction volume, yield, and reliability of each station.
-- ---------------------------------------------------------------------
SELECT 
    s.station_id,
    s.station_name,
    s.city,
    COUNT(cs.session_id) AS total_sessions,
    SUM(cs.revenue) AS total_revenue,
    SUM(cs.energy_kwh) AS total_energy,
    AVG(cs.duration_minutes) AS avg_duration,
    (SUM(CASE WHEN cs.session_status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(cs.session_id), 0)) AS failure_rate_pct
FROM stations s
LEFT JOIN charging_sessions cs ON s.station_id = cs.station_id
GROUP BY 1, 2, 3
ORDER BY total_revenue DESC;


-- ---------------------------------------------------------------------
-- 3. Charger Failure Rate
-- Business Purpose: Identifies problematic hardware by calculating the 
-- failure rate per individual charger, ranking them by highest risk 
-- to inform maintenance dispatch.
-- ---------------------------------------------------------------------
SELECT 
    c.charger_id,
    c.station_id,
    c.charger_type,
    COUNT(cs.session_id) AS total_attempts,
    SUM(CASE WHEN cs.session_status = 'Failed' THEN 1 ELSE 0 END) AS total_failures,
    (SUM(CASE WHEN cs.session_status = 'Failed' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(cs.session_id), 0)) AS failure_rate_pct
FROM chargers c
LEFT JOIN charging_sessions cs ON c.charger_id = cs.charger_id
GROUP BY 1, 2, 3
HAVING COUNT(cs.session_id) > 10
ORDER BY failure_rate_pct DESC;


-- ---------------------------------------------------------------------
-- 4. Hourly Demand
-- Business Purpose: Understand intraday capacity requirements by mapping 
-- session volume to the hour of the day to identify peak congestion.
-- ---------------------------------------------------------------------
SELECT 
    EXTRACT(HOUR FROM start_time) AS hour_of_day,
    COUNT(session_id) AS total_sessions,
    SUM(energy_kwh) AS total_energy,
    SUM(revenue) AS total_revenue
FROM charging_sessions
GROUP BY 1
ORDER BY 1 ASC;


-- ---------------------------------------------------------------------
-- 5. Daily Demand
-- Business Purpose: Highlights variations in network traffic throughout 
-- the week (e.g., commute days vs weekend leisure travel) to aid in
-- dynamic pricing strategies.
-- ---------------------------------------------------------------------
SELECT 
    EXTRACT(DAYOFWEEK FROM start_time) AS day_of_week_num,
    COUNT(session_id) AS total_sessions,
    AVG(duration_minutes) AS avg_duration,
    SUM(energy_kwh) AS total_energy
FROM charging_sessions
GROUP BY 1
ORDER BY 1 ASC;


-- ---------------------------------------------------------------------
-- 6. Monthly Revenue (Cumulative via Window Function)
-- Business Purpose: Tracks macro financial growth and seasonality by 
-- aggregating revenue yield month-over-month while calculating a running
-- total of gross revenue.
-- ---------------------------------------------------------------------
SELECT 
    DATE_TRUNC('month', start_time) AS billing_month,
    COUNT(session_id) AS total_sessions,
    SUM(revenue) AS gross_revenue_usd,
    SUM(SUM(revenue)) OVER (ORDER BY DATE_TRUNC('month', start_time)) AS cumulative_revenue_usd
FROM charging_sessions
GROUP BY 1
ORDER BY 1 ASC;


-- ---------------------------------------------------------------------
-- 7. Top Revenue Stations (Window Function Rank)
-- Business Purpose: Uses a window function to strictly rank the most 
-- financially lucrative stations in the network, isolating primary anchors.
-- ---------------------------------------------------------------------
WITH StationRevenue AS (
    SELECT 
        station_id,
        SUM(revenue) AS total_revenue
    FROM charging_sessions
    GROUP BY 1
)
SELECT 
    s.station_name,
    s.city,
    sr.total_revenue,
    RANK() OVER (ORDER BY sr.total_revenue DESC) AS revenue_rank
FROM StationRevenue sr
JOIN stations s ON sr.station_id = s.station_id
ORDER BY revenue_rank ASC
LIMIT 10;


-- ---------------------------------------------------------------------
-- 8. Underutilized Stations
-- Business Purpose: Identifies locations with active hardware but 
-- exceptionally low session volume relative to total physical capacity,
-- flagging stranded capital expenditure.
-- ---------------------------------------------------------------------
WITH ChargerCount AS (
    SELECT station_id, COUNT(charger_id) AS active_chargers
    FROM chargers
    WHERE charger_status = 'Active'
    GROUP BY 1
),
StationLoad AS (
    SELECT 
        station_id,
        COUNT(session_id) AS total_sessions,
        SUM(duration_minutes) AS total_duration_minutes
    FROM charging_sessions
    GROUP BY 1
)
SELECT 
    s.station_name,
    s.city,
    cc.active_chargers,
    sl.total_sessions,
    -- Utilization Proxy Calculation (Assuming 365 day baseline)
    (sl.total_duration_minutes / (cc.active_chargers * 365 * 24 * 60)) * 100.0 AS est_utilization_pct
FROM stations s
JOIN ChargerCount cc ON s.station_id = cc.station_id
LEFT JOIN StationLoad sl ON s.station_id = sl.station_id
WHERE (sl.total_duration_minutes / (cc.active_chargers * 365 * 24 * 60)) * 100.0 < 2.0
ORDER BY est_utilization_pct ASC;


-- ---------------------------------------------------------------------
-- 9. High-Pressure Stations
-- Business Purpose: Identifies stations experiencing severe hardware 
-- congestion by isolating those turning over >15 sessions/charger/day.
-- ---------------------------------------------------------------------
WITH ChargerCount AS (
    SELECT station_id, COUNT(charger_id) AS active_chargers
    FROM chargers
    WHERE charger_status = 'Active'
    GROUP BY 1
),
StationLoad AS (
    SELECT 
        station_id,
        COUNT(session_id) AS total_sessions
    FROM charging_sessions
    GROUP BY 1
)
SELECT 
    s.station_name,
    s.city,
    cc.active_chargers,
    sl.total_sessions,
    (sl.total_sessions / (cc.active_chargers * 365)) AS sessions_per_charger_per_day
FROM stations s
JOIN ChargerCount cc ON s.station_id = cc.station_id
JOIN StationLoad sl ON s.station_id = sl.station_id
WHERE (sl.total_sessions / (cc.active_chargers * 365)) > 15
ORDER BY sessions_per_charger_per_day DESC;


-- ---------------------------------------------------------------------
-- 10. Customer Repeat Behavior (CASE Statement Segmentation)
-- Business Purpose: Segments the customer base into discrete buckets 
-- (Single-Use vs Power Users) to gauge brand loyalty and product-market fit.
-- ---------------------------------------------------------------------
WITH CustomerFrequency AS (
    SELECT 
        customer_id,
        COUNT(session_id) AS total_visits
    FROM charging_sessions
    GROUP BY 1
)
SELECT 
    CASE 
        WHEN total_visits = 1 THEN 'Single Use'
        WHEN total_visits BETWEEN 2 AND 5 THEN 'Occasional (2-5)'
        WHEN total_visits BETWEEN 6 AND 20 THEN 'Regular (6-20)'
        ELSE 'Power User (21+)'
    END AS customer_segment,
    COUNT(customer_id) AS customer_count,
    SUM(total_visits) AS total_network_visits
FROM CustomerFrequency
GROUP BY 1
ORDER BY customer_count DESC;


-- ---------------------------------------------------------------------
-- 11. Vehicle-Type Analysis
-- Business Purpose: Profiles hardware demand by vehicle model to 
-- understand which EVs draw the most energy and occupy the most time.
-- ---------------------------------------------------------------------
SELECT 
    vehicle_type,
    COUNT(session_id) AS total_sessions,
    SUM(energy_kwh) AS total_energy_kwh,
    AVG(energy_kwh) AS avg_kwh_per_session,
    AVG(duration_minutes) AS avg_duration_minutes,
    SUM(revenue) AS total_revenue
FROM charging_sessions
GROUP BY 1
ORDER BY total_sessions DESC;


-- ---------------------------------------------------------------------
-- 12. Anomaly Preparation (CASE Statement Flagging)
-- Business Purpose: Flags anomalous charging behavior directly in SQL, 
-- such as "Campers" occupying a charger for >4 hours while drawing <2 kWh,
-- or sessions that fail immediately upon plug-in.
-- ---------------------------------------------------------------------
SELECT 
    session_id,
    station_id,
    charger_id,
    duration_minutes,
    energy_kwh,
    CASE 
        WHEN duration_minutes > 240 AND energy_kwh < 2.0 THEN 'Idle Camper'
        WHEN duration_minutes < 5 AND energy_kwh = 0 THEN 'Immediate Failure/Abort'
        ELSE 'Normal'
    END AS anomaly_flag
FROM charging_sessions
WHERE 
    (duration_minutes > 240 AND energy_kwh < 2.0)
    OR 
    (duration_minutes < 5 AND energy_kwh = 0)
ORDER BY duration_minutes DESC;
