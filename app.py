import os
import json
import time
import math
import random
import threading
from datetime import datetime
import requests
import pandas as pd
import numpy as np
from flask import Flask, request, jsonify, render_template, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# Load local .env if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    try:
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# KONGU REGION, TAMIL NADU COLD CHAIN HUBS & ACCURATE HIGHWAY ROAD WAYPOINTS
# ---------------------------------------------------------------------------
KONGU_HUBS = {
    "coimbatore": {"name": "Coimbatore Mega Dairy Hub", "lat": 11.0168, "lng": 76.9558, "city": "Coimbatore", "type": "Origin Plant"},
    "tirupur":    {"name": "Tirupur Cold Distribution Bay", "lat": 11.1085, "lng": 77.3411, "city": "Tirupur", "type": "Waypoint Bay"},
    "perundurai": {"name": "Perundurai SIPCOT Cold Vault", "lat": 11.2750, "lng": 77.5850, "city": "Perundurai", "type": "Transit Depot"},
    "erode":      {"name": "Erode Regional Cold Storage", "lat": 11.3410, "lng": 77.7172, "city": "Erode", "type": "Regional Depot"},
    "salem":      {"name": "Salem Central Refrigerated Terminal", "lat": 11.6643, "lng": 78.1460, "city": "Salem", "type": "Mega Terminal"},
    "namakkal":   {"name": "Namakkal Cold Chain Transfer Base", "lat": 11.2189, "lng": 78.1674, "city": "Namakkal", "type": "Dairy Terminal"},
    "karur":      {"name": "Karur Perishables Bay", "lat": 10.9601, "lng": 78.0766, "city": "Karur", "type": "Regional Hub"},
    "ooty":       {"name": "Nilgiris High-Altitude Cold Vault", "lat": 11.4102, "lng": 76.6950, "city": "Ooty", "type": "Hardening Plant"}
}

# 4 Active Refrigerated Transport Lorries with High-Density Highway Route Waypoints
FLEET_LORRIES = {
    "TN-38-CC-101": {
        "vehicle_id": "TN-38-CC-101",
        "name": "Kongu Express 1",
        "driver": "M. Senthil Kumar",
        "driver_phone": "+91 94431 22891",
        "product": "Ice Cream Pints",
        "cargo_load_kg": 5200,
        "cargo_val_inr": 468000,
        "route_name": "Coimbatore -> Tirupur -> Erode (NH544)",
        "route_color": "#10b981", # Emerald
        # Realistic waypoints along NH544
        "waypoints": [
            [11.0168, 76.9558], # Coimbatore Hub
            [11.0420, 77.0300], # Singanallur
            [11.0650, 77.1050], # Neelambur
            [11.1300, 77.2000], # Karumathampatti
            [11.1900, 77.2700], # Avinashi Bypass
            [11.1085, 77.3411], # Tirupur Cold Bay
            [11.1850, 77.4400], # Kunnathur Rd
            [11.2750, 77.5850], # Perundurai SIPCOT
            [11.3410, 77.7172]  # Erode Depot
        ],
        "progress": 0.42,
        "speed_kmh": 50.0,
        "door_status": "Closed",
        "battery_percent": 96.5,
        "temp_front": -21.6,
        "temp_mid": -20.2,
        "temp_rear": -19.1,
        "humidity": 72.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-33-CC-204": {
        "vehicle_id": "TN-33-CC-204",
        "name": "Erode Cold Carrier 2",
        "driver": "K. Murugan",
        "driver_phone": "+91 98422 71045",
        "product": "Dairy Soft Ice Cream & Bars",
        "cargo_load_kg": 4800,
        "cargo_val_inr": 432000,
        "route_name": "Erode Hub -> Perundurai -> Salem Depot (NH544 Bypass)",
        "route_color": "#ef4444", # Red (Incident Lorry)
        "waypoints": [
            [11.3410, 77.7172], # Erode Depot
            [11.3900, 77.7400], # Chithode
            [11.4450, 77.7780], # Bhavani / Kumarapalayam
            [11.4880, 77.8720], # Sankari Toll
            [11.5300, 77.9600], # Magudanchavadi
            [11.5900, 78.0400], # Ariyanoor
            [11.6643, 78.1460]  # Salem Central Terminal
        ],
        "progress": 0.55,
        "speed_kmh": 0.0, # Halted at transit bay
        "door_status": "Open", # INCIDENT: Rear door open & heat influx
        "battery_percent": 88.0,
        "temp_front": -16.4,
        "temp_mid": -13.8,
        "temp_rear": -7.5, # CRITICAL THAWING RISK
        "humidity": 89.2,
        "alert_level": "Critical",
        "condition": "Thawing Risk",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-28-CC-415": {
        "vehicle_id": "TN-28-CC-415",
        "name": "Namakkal Cold Liner 3",
        "driver": "P. Ramesh",
        "driver_phone": "+91 97890 33412",
        "product": "Frozen Dairy Desserts",
        "cargo_load_kg": 4400,
        "cargo_val_inr": 396000,
        "route_name": "Namakkal Dairy Belt -> Karur Cold Bay (NH44)",
        "route_color": "#f59e0b", # Amber
        "waypoints": [
            [11.2189, 78.1674], # Namakkal Base
            [11.1600, 78.1400], # Keerambur
            [11.1000, 78.0800], # Paramathi
            [11.0500, 78.0100], # Velur Cauvery Bridge
            [10.9900, 78.0400], # Vangal Road
            [10.9601, 78.0766]  # Karur Bay
        ],
        "progress": 0.65,
        "speed_kmh": 46.0,
        "door_status": "Closed",
        "battery_percent": 91.2,
        "temp_front": -19.4,
        "temp_mid": -17.5,
        "temp_rear": -15.9,
        "humidity": 76.5,
        "alert_level": "Warning",
        "condition": "Warning",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-43-CC-309": {
        "vehicle_id": "TN-43-CC-309",
        "name": "Nilgiris Mountain Vault 4",
        "driver": "A. Balaji",
        "driver_phone": "+91 99441 55620",
        "product": "Artisanal Ice Cream",
        "cargo_load_kg": 3600,
        "cargo_val_inr": 324000,
        "route_name": "Nilgiris/Ooty -> Mettupalayam -> Coimbatore Hub (NH181)",
        "route_color": "#06b6d4", # Cyan
        "waypoints": [
            [11.4102, 76.6950], # Ooty Vault
            [11.3700, 76.7500], # Aruvankadu
            [11.3530, 76.7950], # Coonoor Ghats
            [11.3100, 76.8800], # Burliyar
            [11.2995, 76.9427], # Mettupalayam
            [11.2100, 76.9450], # Karamadai
            [11.1200, 76.9500], # Thudiyalur
            [11.0168, 76.9558]  # Coimbatore Hub
        ],
        "progress": 0.28,
        "speed_kmh": 38.0,
        "door_status": "Closed",
        "battery_percent": 98.0,
        "temp_front": -22.4,
        "temp_mid": -21.1,
        "temp_rear": -20.3,
        "humidity": 69.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "refreezing_detected": "No",
        "active": True
    }
}

VEHICLE_HISTORY = {vid: [] for vid in FLEET_LORRIES}
ACTIVE_ALERTS = []
AUDIT_LOG = []

state_lock = threading.Lock()
ACTIVE_VEHICLE_ID = "TN-33-CC-204"

def get_route_position(waypoints, progress):
    n = len(waypoints) - 1
    p = max(0.0, min(1.0, progress)) * n
    idx = int(p)
    frac = p - idx
    if idx >= n:
        return waypoints[-1][0], waypoints[-1][1]
    p1 = waypoints[idx]
    p2 = waypoints[idx + 1]
    lat = p1[0] + frac * (p2[0] - p1[0])
    lng = p1[1] + frac * (p2[1] - p1[1])
    return round(lat, 5), round(lng, 5)

# Seed historical time series for each vehicle (30 historical points)
now_ts = datetime.now()
with state_lock:
    for vid, v in FLEET_LORRIES.items():
        lat, lng = get_route_position(v["waypoints"], v["progress"])
        v["gps_lat"] = lat
        v["gps_lng"] = lng
        v["thermal_gradient"] = round(v["temp_rear"] - v["temp_front"], 2)
        v["temp_avg"] = round((v["temp_front"] + v["temp_mid"] + v["temp_rear"]) / 3.0, 2)
        v["deviation"] = round(v["temp_avg"] - (-18.0), 2)

        for i in range(30, 0, -1):
            hist_ts = (now_ts - pd.Timedelta(seconds=i * 2)).strftime("%H:%M:%S")
            jitter = (random.random() - 0.5) * 0.2
            tf = round(v["temp_front"] + jitter, 1)
            tm = round(v["temp_mid"] + jitter, 1)
            tr = round(v["temp_rear"] + jitter * 1.5, 1)
            t_avg = round((tf + tm + tr) / 3.0, 1)
            VEHICLE_HISTORY[vid].append({
                "timestamp": hist_ts,
                "temp_front": tf,
                "temp_mid": tm,
                "temp_rear": tr,
                "temp_avg": t_avg,
                "deviation": round(t_avg - (-18.0), 1),
                "gradient": round(tr - tf, 1),
                "humidity": round(v["humidity"] + (random.random() - 0.5) * 1.0, 1),
                "door_status": v["door_status"],
                "battery": round(v["battery_percent"], 1)
            })

# Background Real-Time Generator & Streamer
def live_stream_engine():
    while True:
        time.sleep(1.5) # Live tick every 1.5 seconds
        with state_lock:
            ts_str = datetime.now().strftime("%H:%M:%S")
            
            for vid, v in FLEET_LORRIES.items():
                if v["door_status"] == "Closed":
                    v["progress"] += 0.004
                    if v["progress"] > 1.0:
                        v["progress"] = 0.02 # Loop along highway
                    lat, lng = get_route_position(v["waypoints"], v["progress"])
                    v["gps_lat"] = lat
                    v["gps_lng"] = lng
                    v["speed_kmh"] = round(random.uniform(44.0, 56.0), 1)
                else:
                    v["speed_kmh"] = 0.0 # Halted while door open

                # Dynamics of 3 Temperature Detectors per Transport Lorry
                if vid == "TN-33-CC-204":
                    # Lorry 2: Incident near Salem Bypass (Rear Door Open)
                    if v["door_status"] == "Open":
                        v["temp_rear"] = min(-6.8, v["temp_rear"] + round(random.uniform(0.04, 0.15), 2))
                        v["temp_mid"]  = min(-13.0, v["temp_mid"]  + round(random.uniform(0.02, 0.08), 2))
                        v["temp_front"]= min(-15.8, v["temp_front"]+ round(random.uniform(0.01, 0.04), 2))
                        v["humidity"]  = min(93.0, v["humidity"]  + round(random.uniform(0.1, 0.3), 1))
                    else:
                        v["temp_rear"] = max(-19.5, v["temp_rear"] - 0.15)
                        v["temp_mid"]  = max(-20.5, v["temp_mid"]  - 0.10)
                        v["temp_front"]= max(-22.0, v["temp_front"]- 0.08)
                        v["humidity"]  = max(71.0, v["humidity"]  - 0.3)
                else:
                    jitter = (random.random() - 0.5) * 0.15
                    v["temp_front"] = round(v["temp_front"] + jitter, 1)
                    v["temp_mid"]   = round(v["temp_mid"]   + jitter * 0.8, 1)
                    v["temp_rear"]  = round(v["temp_rear"]  + jitter * 1.2, 1)
                    v["humidity"]   = round(v["humidity"]   + (random.random() - 0.5) * 0.3, 1)

                v["temp_avg"] = round((v["temp_front"] + v["temp_mid"] + v["temp_rear"]) / 3.0, 2)
                v["thermal_gradient"] = round(v["temp_rear"] - v["temp_front"], 2)
                v["deviation"] = round(v["temp_avg"] - (-18.0), 2)
                v["battery_percent"] = max(10.0, round(v["battery_percent"] - 0.002, 2))

                max_t = max(v["temp_front"], v["temp_mid"], v["temp_rear"])
                if max_t >= -10.0:
                    v["alert_level"] = "Critical"
                    v["condition"] = "Thawing Risk"
                elif max_t > -15.0:
                    v["alert_level"] = "Critical"
                    v["condition"] = "High Risk"
                elif max_t > -18.0:
                    v["alert_level"] = "Warning"
                    v["condition"] = "Warning"
                else:
                    v["alert_level"] = "No Alert"
                    v["condition"] = "Safe"

                new_point = {
                    "timestamp": ts_str,
                    "temp_front": v["temp_front"],
                    "temp_mid": v["temp_mid"],
                    "temp_rear": v["temp_rear"],
                    "temp_avg": v["temp_avg"],
                    "deviation": v["deviation"],
                    "gradient": v["thermal_gradient"],
                    "humidity": v["humidity"],
                    "door_status": v["door_status"],
                    "battery": v["battery_percent"]
                }
                VEHICLE_HISTORY[vid].append(new_point)
                if len(VEHICLE_HISTORY[vid]) > 60:
                    VEHICLE_HISTORY[vid].pop(0)

                if v["alert_level"] != "No Alert" or v["door_status"] == "Open":
                    alert_id = f"ALT-{vid[-3:]}-{int(time.time()) % 10000}"
                    if not any(a["vehicle_id"] == vid and (time.time() - a["raw_time"]) < 20 for a in ACTIVE_ALERTS):
                        ACTIVE_ALERTS.insert(0, {
                            "id": alert_id,
                            "vehicle_id": vid,
                            "route": v["route_name"],
                            "timestamp": ts_str,
                            "raw_time": time.time(),
                            "alert_level": v["alert_level"],
                            "condition": v["condition"],
                            "temp_front": v["temp_front"],
                            "temp_mid": v["temp_mid"],
                            "temp_rear": v["temp_rear"],
                            "gradient": v["thermal_gradient"],
                            "door_status": v["door_status"],
                            "event_class": "Spatially Localised (Rear Door Heat Influx)" if v["door_status"] == "Open" else "Thermal Disparity"
                        })
                        if len(ACTIVE_ALERTS) > 25:
                            ACTIVE_ALERTS.pop()

stream_thread = threading.Thread(target=live_stream_engine, daemon=True)
stream_thread.start()

# ----------------- HTTP APIS -----------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fleet/state', methods=['GET'])
def get_fleet_state():
    with state_lock:
        active_vid = request.args.get('vehicle_id', ACTIVE_VEHICLE_ID)
        if active_vid not in FLEET_LORRIES:
            active_vid = list(FLEET_LORRIES.keys())[0]

        total_lorries = len(FLEET_LORRIES)
        lorries_safe = sum(1 for v in FLEET_LORRIES.values() if v["alert_level"] == "No Alert")
        lorries_warn = sum(1 for v in FLEET_LORRIES.values() if v["alert_level"] == "Warning")
        lorries_crit = sum(1 for v in FLEET_LORRIES.values() if v["alert_level"] == "Critical")
        door_open_count = sum(1 for v in FLEET_LORRIES.values() if v["door_status"] == "Open")

        active_v = FLEET_LORRIES[active_vid]
        active_hist = VEHICLE_HISTORY[active_vid][-45:]

        # Return full history dict for all vehicles so Graph 3 plots real multi-lorry curves!
        all_hist = {vid: hist[-45:] for vid, hist in VEHICLE_HISTORY.items()}

        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "region": "Kongu Region, Tamil Nadu",
            "fleet_summary": {
                "total_transports": total_lorries,
                "safe_count": lorries_safe,
                "warning_count": lorries_warn,
                "critical_count": lorries_crit,
                "door_open_count": door_open_count
            },
            "hubs": KONGU_HUBS,
            "fleet": FLEET_LORRIES,
            "active_vehicle_id": active_vid,
            "active_vehicle": active_v,
            "active_history": active_hist,
            "fleet_history": all_hist,
            "active_alerts": ACTIVE_ALERTS[:8],
            "audit_log": AUDIT_LOG[:10]
        })

@app.route('/api/vehicle/select', methods=['POST'])
def select_vehicle():
    global ACTIVE_VEHICLE_ID
    data = request.get_json() or {}
    vid = data.get("vehicle_id")
    with state_lock:
        if vid in FLEET_LORRIES:
            ACTIVE_VEHICLE_ID = vid
            return jsonify({"status": "ok", "active_vehicle_id": ACTIVE_VEHICLE_ID})
        return jsonify({"status": "error", "message": "Vehicle not found"}), 404

@app.route('/api/ai/diagnose', methods=['POST'])
def ai_diagnose():
    data = request.get_json() or {}
    vid = data.get("vehicle_id", ACTIVE_VEHICLE_ID)
    with state_lock:
        v = FLEET_LORRIES.get(vid, list(FLEET_LORRIES.values())[0])

    prompt = f"""You are the Boomerang Cold Chain Fleet Intelligence Officer.
Analyze live telemetry for Refrigerated Transport Lorry {v['vehicle_id']} on route {v['route_name']} in the Kongu region, Tamil Nadu:
- Product: {v['product']} (Safe setpoint <= -18.0 C)
- Cargo Value: Rs. {v['cargo_val_inr']:,} ({v['cargo_load_kg']} kg)
- Detector 1 (Front/Chiller Air Delivery): {v['temp_front']} C
- Detector 2 (Middle/Cargo Core Center): {v['temp_mid']} C
- Detector 3 (Rear/Back Door Zone): {v['temp_rear']} C
- Thermal Gradient (Rear - Front): +{v['thermal_gradient']} C
- Compartment Door Status: {v['door_status']}
- Chamber Relative Humidity: {v['humidity']}%
- Transit Speed: {v['speed_kmh']} km/h
- Alert Level: {v['alert_level']} ({v['condition']})

Provide a 4-point executive advisory for the fleet owner:
1. ROOT-CAUSE DIAGNOSIS
2. QUALITY & TEXTURE RISK (Ice crystal coarsening)
3. IMMEDIATE DISPATCHER DIRECTIVE for driver {v['driver']} ({v['driver_phone']})
4. FINANCIAL EXPOSURE (Rs.)"""

    ai_text = None
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={GEMINI_API_KEY}"
            resp = requests.post(url, json={"contents": [{"parts": [{"text": prompt}]}]}, headers={"Content-Type": "application/json"}, timeout=3)
            if resp.status_code == 200:
                ai_text = resp.json()['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            ai_text = None

    if not ai_text:
        if v['temp_rear'] >= -10.0 or v['door_status'] == 'Open':
            ai_text = f"""1. ROOT-CAUSE DIAGNOSIS: Thermal breach in rear zone (+{v['thermal_gradient']}°C gradient). Rear detector heated to {v['temp_rear']}°C while front evaporator is at {v['temp_front']}°C. Direct warm air & moisture influx via unsecured rear door on {v['route_name']}.
2. QUALITY & TEXTURE RISK: High thawing hazard. Bulk core ({v['temp_mid']}°C) is softening. Re-cooling will cause Ostwald ripening (coarse ice crystal lattices), causing gritty mouthfeel and irreversible shelf life reduction.
3. IMMEDIATE DISPATCHER DIRECTIVE: Call driver {v['driver']} ({v['driver_phone']}) immediately. Secure rear door latches, switch Thermo King refrigeration to continuous maximum cooling override, and divert to Perundurai SIPCOT Cold Vault if temp remains above -15°C after 15 min.
4. FINANCIAL EXPOSURE: High risk on total shipment value of ₹ {v['cargo_val_inr']:,}. Immediate intervention preserves core cargo."""
        else:
            ai_text = f"""1. ROOT-CAUSE DIAGNOSIS: Normal deep freeze operations. Chamber thermal gradient is balanced at +{v['thermal_gradient']}°C, indicating uniform airflow from front evaporator ({v['temp_front']}°C) across cargo core ({v['temp_mid']}°C) to rear ({v['temp_rear']}°C).
2. QUALITY & TEXTURE RISK: Optimal texture preservation. All 3 detectors maintain temperatures below the critical -18.0°C threshold. Zero recrystallization risk.
3. IMMEDIATE DISPATCHER DIRECTIVE: Lorry is on schedule along {v['route_name']}. Maintain current transit speed ({v['speed_kmh']} km/h). No operational intervention required.
4. FINANCIAL EXPOSURE: Cargo valuation of ₹ {v['cargo_val_inr']:,} (100% compliant and intact)."""

    return jsonify({
        "status": "success",
        "vehicle_id": vid,
        "advisory": ai_text,
        "generated_at": datetime.now().strftime("%H:%M:%S")
    })

@app.route('/api/telemetry', methods=['POST'])
def ingest_telemetry():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return jsonify({"status": "error", "message": "Invalid JSON"}), 400

    vid = str(payload.get("vehicle_id", "TN-33-CC-204"))
    tf = payload.get("temp_front")
    tm = payload.get("temp_mid")
    tr = payload.get("temp_rear")
    
    if tf is None and payload.get("temperature") is not None:
        base_t = float(payload.get("temperature"))
        tf = base_t - 1.2
        tm = base_t
        tr = base_t + 1.4
    else:
        tf = float(tf if tf is not None else -20.5)
        tm = float(tm if tm is not None else -19.0)
        tr = float(tr if tr is not None else -17.5)

    hum = float(payload.get("humidity", 74.0))
    door = str(payload.get("door_status", "Closed")).capitalize()
    batt = float(payload.get("battery_percent", 95.0))
    lat = float(payload.get("gps_lat", 11.3410))
    lng = float(payload.get("gps_lng", 77.7172))
    spd = float(payload.get("speed_kmh", 45.0))

    with state_lock:
        if vid in FLEET_LORRIES:
            v = FLEET_LORRIES[vid]
            v["temp_front"] = round(tf, 1)
            v["temp_mid"] = round(tm, 1)
            v["temp_rear"] = round(tr, 1)
            v["humidity"] = round(hum, 1)
            v["door_status"] = door
            v["battery_percent"] = round(batt, 1)
            v["gps_lat"] = round(lat, 5)
            v["gps_lng"] = round(lng, 5)
            v["speed_kmh"] = round(spd, 1)
            v["temp_avg"] = round((tf + tm + tr) / 3.0, 2)
            v["thermal_gradient"] = round(tr - tf, 2)
            v["deviation"] = round(v["temp_avg"] - (-18.0), 2)

    return jsonify({"status": "success", "vehicle_id": vid}), 201

@app.route('/api/alerts/acknowledge', methods=['POST'])
def ack_alert():
    data = request.get_json() or {}
    aid = data.get("alert_id")
    op = data.get("operator_name", "Fleet Dispatcher")
    note = data.get("action_note", "Secured rear door & verified cooling.")

    with state_lock:
        for i, a in enumerate(ACTIVE_ALERTS):
            if a["id"] == aid:
                a["acknowledged"] = True
                a["responder"] = op
                a["action_taken"] = note
                a["ack_time"] = datetime.now().strftime("%H:%M:%S")
                AUDIT_LOG.insert(0, a)
                ACTIVE_ALERTS.pop(i)
                return jsonify({"status": "acknowledged", "alert": a})
        return jsonify({"status": "not_found"}), 404

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    with state_lock:
        rows = []
        for vid, history in VEHICLE_HISTORY.items():
            for pt in history:
                rows.append({
                    "Vehicle_ID": vid,
                    "Route": FLEET_LORRIES[vid]["route_name"],
                    "Timestamp": pt["timestamp"],
                    "Temp_Detector_1_Front_C": pt["temp_front"],
                    "Temp_Detector_2_Mid_C": pt["temp_mid"],
                    "Temp_Detector_3_Rear_C": pt["temp_rear"],
                    "Temp_Average_C": pt["temp_avg"],
                    "Thermal_Gradient_Delta_C": pt["gradient"],
                    "Humidity_Percent": pt["humidity"],
                    "Door_Status": pt["door_status"],
                    "Battery_Percent": pt["battery"]
                })
        df = pd.DataFrame(rows)
        csv_path = os.path.join('static', 'kongu_fleet_cold_chain_telemetry.csv')
        df.to_csv(csv_path, index=False)
        return send_file(csv_path, as_attachment=True, download_name="kongu_fleet_cold_chain_telemetry.csv")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"Cold Chain Kongu Fleet Real-Time Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
