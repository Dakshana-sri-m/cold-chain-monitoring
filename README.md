# FrostGuard &bull; Keep Every Scoop Cold
### Real-Time Cold Chain Temperature Excursion Monitoring System

**Operational Belt:** Kongu Logistics Corridor, Tamil Nadu (Coimbatore, Tirupur, Erode, Salem, Namakkal, Nilgiris/Ooty, Karur)  
**Lead Developer:** Dakshana Sri M  
**Operations Center URL:** `http://127.0.0.1:5050`  

---

## ❄️ 1. Overview & Modern FrostGuard UI/UX

**FrostGuard** is an industrial-grade cold chain operations center designed to protect sensitive perishables (ice cream, frozen dairy desserts, and vaccines) during highway transit.

The interface incorporates 8 specialized operational modules:
1. **Dashboard:** Executive real-time overview featuring live KPI metric cards (Active Shipments, Current Temp, Active Alerts, Cold Chain Health), area temperature trend with safe limit line, OpenStreetMap live tracking preview, shipment overview table, recent alerts feed, and spoilage analysis summary.
2. **Shipments:** Comprehensive shipment registry with status filters (Total: 12, In Transit: 6, Delivered: 5, Delayed: 1), live truck temperatures, route milestones, and dispatch modal.
3. **Live Tracking:** Interactive OpenStreetMap (powered by Leaflet.js) visualizing Tamil Nadu NH544, NH44, and NH181 corridors with live moving lorries, transit hubs, cold vaults, and vehicle telematics sidebar.
4. **Temperature Monitoring:** 3-detector spatial monitoring:
   - **Front Sensor ($T_1$):** Chiller evaporator air delivery
   - **Middle Sensor ($T_2$):** Bulk cargo core mass
   - **Rear Sensor ($T_3$):** Back door / heat influx zone
   - Semicircular radial gauge with safe threshold indicator (-25°C to -18°C) and 24h curve.
5. **Spoilage Analysis:** Quantified financial & mass loss analytics:
   - Spoilage Rate Ring: **2.6%** (48% below target baseline)
   - Potential Spoilage: **~18 kg**
   - Estimated Savings: **₹ 6,300**
   - Actual vs. Predicted trend curves
   - 1-click **Google Gemini AI Excursion Intelligence Officer**
6. **Alerts:** Prioritized notification center with real-time severity levels (Critical, Warning, Info) and 1-click acknowledgment.
7. **Reports & Analytics:** Temperature compliance doughnut (96.4%), weekly spoilage bar chart (Mon–Sun), shipment timeliness (94% On Time), and telemetry CSV export.
8. **Settings:** Operational thresholds (-25°C to -18°C), notification toggles (Email, SMS, Push), and system info.

---

## 🚚 2. Kongu Region Active Transport Fleet

| Vehicle ID | Truck ID | Route (Tamil Nadu) | Cargo Type | Temp | Status | Driver & Contact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`TN-33-CC-204`** | `T-101` | Erode Hub $\rightarrow$ Perundurai $\rightarrow$ Salem Depot (NH544) | Milk & Ice Cream | `-20.4°C` | **On Route** | K. Murugan (`+91 98422 71045`) |
| **`TN-38-CC-181`** | `T-103` | Coimbatore $\rightarrow$ Tirupur $\rightarrow$ Erode (NH544) | Ice Cream Pints | `-18.7°C` | **At Depot** | M. Senthil Kumar (`+91 94431 22891`) |
| **`TN-43-CC-309`** | `T-107` | Nilgiris/Ooty $\rightarrow$ Mettupalayam $\rightarrow$ Coimbatore (NH181) | Frozen Veg & Ice Cream | `-21.5°C` | **On Route** | A. Balaji (`+91 99441 55620`) |
| **`TN-41-CC-276`** | `T-105` | Namakkal Dairy Belt $\rightarrow$ Karur Cold Bay (NH44) | Dairy Soft Cream | `-19.2°C` | **Delayed** | P. Ramesh (`+91 97890 33412`) |
| **`TN-39-CC-221`** | `T-102` | Salem Terminal $\rightarrow$ Perundurai Transit Hub | Fruits & Dairy | `-20.1°C` | **Delivered** | S. Rajesh (`+91 94421 88392`) |

---

## ⚡ 3. Quick Start & Execution

1. Run the local dashboard:
   ```bash
   python app.py
   ```
   Or double-click `start_dashboard.bat`.
2. Open your browser at **`http://127.0.0.1:5050`**.
3. Ingest real hardware sensor data:
   ```bash
   POST http://127.0.0.1:5050/api/telemetry
   Content-Type: application/json

   {
     "vehicle_id": "TN-33-CC-204",
     "temp_front": -21.0,
     "temp_mid": -19.5,
     "temp_rear": -18.0,
     "humidity": 72.0,
     "door_status": "Closed",
     "battery_percent": 95.0,
     "gps_lat": 11.3410,
     "gps_lng": 77.7172,
     "speed_kmh": 48.0
   }
   ```

