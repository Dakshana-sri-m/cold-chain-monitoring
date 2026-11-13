# Boomerang Logistics &bull; Kongu Fleet Cold Chain Real-Time Operations Center

**Company / Partner:** Boomerang Cold Chain Logistics  
**Operational Belt:** Kongu Region, Tamil Nadu (Coimbatore, Tirupur, Erode, Salem, Namakkal, Nilgiris/Ooty, Karur)  
**Lead Developer:** Dakshana Sri M  
**Dashboard URL:** `http://127.0.0.1:5050`  

---

## 1. Owner's Real-Time Operational Overview

Designed exclusively as an **Executive Fleet Owner's Real-Time Control Center**, this interface strips away technical hardware setup clutter to display solely the live operational data the fleet owner needs to know:
- **No historical simulation sliders or past/present toggles** &mdash; a 100% pure real-time data stream updating every 1.5 seconds.
- **Concurrent Multiple Transport Lorries** traversing the Kongu logistics corridor in Tamil Nadu.
- **3 Dedicated Temperature Detectors per Vehicle:**
  1. **Detector 1 ($T_1$) &ndash; Front (Chiller Air Outlet):** Measures refrigeration delivery temperature.
  2. **Detector 2 ($T_2$) &ndash; Middle (Cargo Core Mass):** Measures preservation of the bulk ice cream core.
  3. **Detector 3 ($T_3$) &ndash; Rear (Back Door Zone):** Directly monitors thermal ingress and door seal integrity.

---

## 2. Kongu Region Fleet Lorries

| Vehicle ID | Lorry Name | Route (Kongu Belt) | Status | Driver & Contact |
| :--- | :--- | :--- | :--- | :--- |
| **`TN-38-CC-101`** | Kongu Express 1 | **Coimbatore $\rightarrow$ Tirupur $\rightarrow$ Erode** (NH544) | <span style="color:#10b981">SAFE</span> | M. Senthil Kumar (`+91 94431 22891`) |
| **`TN-33-CC-204`** | Erode Cold Carrier 2 | **Erode Hub $\rightarrow$ Perundurai $\rightarrow$ Salem Depot** (NH544 Bypass) | <span style="color:#ef4444">CRITICAL (Door Open)</span> | K. Murugan (`+91 98422 71045`) |
| **`TN-28-CC-415`** | Namakkal Cold Liner 3 | **Namakkal Dairy Belt $\rightarrow$ Karur Cold Bay** (NH44) | <span style="color:#f59e0b">WARNING</span> | P. Ramesh (`+91 97890 33412`) |
| **`TN-43-CC-309`** | Nilgiris Mountain Vault 4 | **Nilgiris/Ooty $\rightarrow$ Mettupalayam $\rightarrow$ Coimbatore Hub** | <span style="color:#10b981">SAFE</span> | A. Balaji (`+91 99441 55620`) |

---

## 3. Real-Time Graphs Incorporating 3 Temperature Detectors

1. **Graph 1: 3-Detector Real-Time Thermal Multi-Line ($T_1, T_2, T_3$):**
   * Plotted simultaneously with Safe ($-18.0^\circ\text{C}$), Warning ($-15.0^\circ\text{C}$), and Critical Thawing ($-10.0^\circ\text{C}$) reference lines.
2. **Graph 2: Thermal Gradient & Airflow Distribution ($\Delta T = T_3 - T_1$):**
   * Measures thermal disparity between the rear door and front chiller. $\Delta T > 3.0^\circ\text{C}$ flags cargo ventilation blockage or door seal leaks.
3. **Graph 3: Kongu Fleet Comparative Real-Time Temperatures:**
   * Plots the real-time average temperature curves of all 4 Kongu transport lorries concurrently.
4. **Graph 4: Moisture Ingress & Rear Door Influx Correlation:**
   * Real-time physical correlation between door opening events and humidity/rear probe ($T_3$) temperature spikes.

---

## 4. Quick Start Guide

### Launch Dashboard
* Double-click [start_dashboard.bat](file:///c:/Users/Dakshana%20Sri/OneDrive/Desktop/cold%20chain/start_dashboard.bat) or run [run_dashboard.ps1](file:///c:/Users/Dakshana%20Sri/OneDrive/Desktop/cold%20chain/run_dashboard.ps1).
* Opens directly at `http://127.0.0.1:5050`.

### Ingest Data from Hardware
Send live sensor data directly to `POST http://127.0.0.1:5050/api/telemetry` with:
```json
{
  "vehicle_id": "TN-33-CC-204",
  "temp_front": -20.5,
  "temp_mid": -19.2,
  "temp_rear": -14.0,
  "humidity": 82.0,
  "door_status": "Open",
  "battery_percent": 95.0,
  "gps_lat": 11.3410,
  "gps_lng": 77.7172,
  "speed_kmh": 0.0
}
```
