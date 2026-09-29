# ⚡ ChargeByEV: Network Operations Center (NOC)

<div align="center">
  <a href="https://chargebyev-ruwt6rkgyqf99gjfqgehyz.streamlit.app/Executive_Insights">
    <img src="https://img.shields.io/badge/🔴_LIVE_DEMO-ChargeByEV_Network_Command_Center-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Live Demo" />
  </a>
</div>
<br>

![ChargeByEV Platform](https://via.placeholder.com/1200x600?text=ChargeByEV+Dashboard+Screenshot)

## 📌 1. Project Overview
**ChargeByEV** is a production-grade Network Operations Center (NOC) and analytical platform designed specifically for Electric Vehicle (EV) charging network operators. It transforms raw transactional telemetry (charging sessions) into actionable operational intelligence. 

Rather than functioning as a standard BI reporting tool, ChargeByEV is engineered as a **diagnostic engine** to actively monitor hardware health, spatial demand, capacity pressure, and network revenue streams in real-time.

---

## 🎯 2. What Does It Do? (Core Capabilities)
The platform consists of **10 highly specialized analytical modules** designed to solve specific operational bottlenecks:

1. **Network Command Center:** Provides a macro-level overview of network health, total active sessions, cumulative revenue, and energy dispensed.
2. **Station Intelligence:** Drills down into micro-level site profiles, tracking individual station utilization, charging pressure, and historical performance.
3. **Demand Intelligence:** Uses temporal load profiling to detect statistical peak windows, demand heatmaps, and grid-stress periods.
4. **Charger Health & Anomaly Detection:** Statistically flags hardware failures, abnormal camper behavior (vehicles plugged in but not drawing power), and underperforming chargers using Interquartile Range (IQR) bounds.
5. **Revenue Intelligence:** Analyzes financial yield, identifying the most profitable stations and plotting them on a 4-quadrant Utilization vs. Revenue matrix.
6. **Geo Intelligence:** A spatial mapping engine clustering geographic performance, allowing operators to visually spot regional demand spikes.
7. **Capacity Simulator:** A deterministic stress-testing sandbox that allows operators to simulate the impact of deploying new hardware (adding chargers) on historical station pressure.
8. **Customer Intelligence:** Segments charging behavior into cohorts (High Frequency, Occasional, High Value) to drive loyalty and pricing strategies.
9. **Data Quality Validation:** Automated relational integrity scans that ensure dataset validity, pinpointing orphaned records, negative energy readings, and missing values.
10. **Executive Insights:** Generates automated, non-hallucinating deterministic text summaries of critical network states for rapid executive briefings.

---

## ⚙️ 3. How Does It Work? (Technical Architecture)
The application is built entirely in Python, leveraging a highly optimized data pipeline and a stateless frontend architecture:

* **Data Engine (Pandas & NumPy):** Processes a 250,000+ row synthetic database on the fly. Applies vectorized operations to calculate complex KPIs (like the proprietary Charging Pressure Index) in milliseconds.
* **Global Filter State:** Implements a custom Session State routing mechanism. When a user filters data (e.g., selecting a specific city or date range) in the sidebar, that state seamlessly persists and filters the data across all 10 independent modules.
* **Visualization Layer (Plotly):** Renders highly interactive, responsive, and accessible charts, spatial maps, and heatmaps without visual clutter.
* **Stateless Cloud Architecture:** The platform features **dynamic data generation on boot**. When deployed to a cloud environment without a persistent disk, the system automatically detects the absence of the massive database files and seamlessly compiles the synthetic dataset directly into RAM before launching the dashboard.

---

## 💼 4. Business Value & Use Cases
As EV adoption accelerates, charging network operators face acute infrastructure bottlenecks. Operating blindly leads to stranded capital and terrible customer experiences. ChargeByEV solves this by providing:

* **Hardware Optimization:** Identifying which specific DC Fast chargers are experiencing high failure rates so maintenance crews can be dispatched proactively.
* **Capital Allocation:** Using the *Capacity Simulator* to prove mathematically where adding new chargers will yield the highest ROI based on historical grid pressure.
* **Grid Load Management:** Using *Demand Intelligence* to identify peak temporal windows, allowing operators to implement time-of-use (TOU) pricing to shift charging behavior off-peak.
* **Revenue Protection:** Identifying "Campers" (cars that are fully charged but occupying a stall), allowing operators to implement idle fees.

---
LIVE DEMO LINK - https://chargebyev-ruwt6rkgyqf99gjfqgehyz.streamlit.app/Executive_Insights
