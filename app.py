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
# KONGU REGION, TAMIL NADU COLD CHAIN HUBS & HIGHWAY ROAD WAYPOINTS
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

# 5 Active Refrigerated Transport Lorries matching FrostGuard UI
FLEET_LORRIES = {
    "TN-33-CC-204": {
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "name": "Erode Cold Carrier 2",
        "driver": "K. Murugan",
        "driver_phone": "+91 98422 71045",
        "product": "Milk & Ice Cream",
        "cargo_type": "Milk & Ice Cream",
        "cargo_load_kg": 4800,
        "cargo_val_inr": 432000,
        "route_name": "Erode Hub -> Perundurai -> Salem Depot (NH544 Bypass)",
        "route_color": "#6366f1", # Indigo
        "eta": "1h 20m",
        "status_label": "On Route",
        "current_location": "Near Erode",
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
        "speed_kmh": 0.0,
        "door_status": "Open", # Incident: Rear Door Open
        "battery_percent": 88.0,
        "temp_front": -16.4,
        "temp_mid": -13.8,
        "temp_rear": -7.5,
        "humidity": 89.2,
        "alert_level": "Critical",
        "condition": "Thawing Risk",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-38-CC-181": {
        "vehicle_id": "TN-38-CC-181",
        "truck_id": "T-103",
        "name": "Kongu Express 1",
        "driver": "M. Senthil Kumar",
        "driver_phone": "+91 94431 22891",
        "product": "Ice Cream Pints",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 5200,
        "cargo_val_inr": 468000,
        "route_name": "Coimbatore -> Tirupur -> Erode (NH544)",
        "route_color": "#10b981", # Emerald
        "eta": "2h 10m",
        "status_label": "At Depot",
        "current_location": "Tirupur Cold Bay",
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
        "speed_kmh": 48.0,
        "door_status": "Closed",
        "battery_percent": 96.5,
        "temp_front": -20.8,
        "temp_mid": -19.4,
        "temp_rear": -18.7,
        "humidity": 72.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-43-CC-309": {
        "vehicle_id": "TN-43-CC-309",
        "truck_id": "T-107",
        "name": "Nilgiris Mountain Vault 4",
        "driver": "A. Balaji",
        "driver_phone": "+91 99441 55620",
        "product": "Frozen Veg & Ice Cream",
        "cargo_type": "Frozen Veg",
        "cargo_load_kg": 3600,
        "cargo_val_inr": 324000,
        "route_name": "Nilgiris/Ooty -> Mettupalayam -> Coimbatore Hub (NH181)",
        "route_color": "#06b6d4", # Cyan
        "eta": "3h 05m",
        "status_label": "On Route",
        "current_location": "Coonoor Ghats",
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
        "progress": 0.30,
        "speed_kmh": 38.0,
        "door_status": "Closed",
        "battery_percent": 98.0,
        "temp_front": -22.5,
        "temp_mid": -21.5,
        "temp_rear": -20.6,
        "humidity": 68.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-41-CC-276": {
        "vehicle_id": "TN-41-CC-276",
        "truck_id": "T-105",
        "name": "Namakkal Cold Liner 3",
        "driver": "P. Ramesh",
        "driver_phone": "+91 97890 33412",
        "product": "Dairy Desserts",
        "cargo_type": "Dairy",
        "cargo_load_kg": 4400,
        "cargo_val_inr": 396000,
        "route_name": "Namakkal Dairy Belt -> Karur Cold Bay (NH44)",
        "route_color": "#f59e0b", # Amber
        "eta": "4h 30m",
        "status_label": "Delayed",
        "current_location": "Paramathi NH44",
        "waypoints": [
            [11.2189, 78.1674], # Namakkal Base
            [11.1600, 78.1400], # Keerambur
            [11.1000, 78.0800], # Paramathi
            [11.0500, 78.0100], # Velur Cauvery Bridge
            [10.9900, 78.0400], # Vangal Road
            [10.9601, 78.0766]  # Karur Bay
        ],
        "progress": 0.65,
        "speed_kmh": 42.0,
        "door_status": "Closed",
        "battery_percent": 91.2,
        "temp_front": -20.1,
        "temp_mid": -19.2,
        "temp_rear": -18.2,
        "humidity": 76.5,
        "alert_level": "Warning",
        "condition": "Warning",
        "refreezing_detected": "No",
        "active": True
    },
    "TN-39-CC-221": {
        "vehicle_id": "TN-39-CC-221",
        "truck_id": "T-102",
        "name": "Salem Perishables Runner",
        "driver": "S. Rajesh",
        "driver_phone": "+91 94421 88392",
        "product": "Fruits & Dairy",
        "cargo_type": "Fruits",
        "cargo_load_kg": 4100,
        "cargo_val_inr": 369000,
        "route_name": "Salem Depot -> Perundurai Transit Hub",
        "route_color": "#10b981", # Green
        "eta": "--",
        "status_label": "Delivered",
        "current_location": "Salem Depot",
        "waypoints": [
            [11.6643, 78.1460], # Salem
            [11.5900, 78.0400],
            [11.4880, 77.8720],
            [11.3410, 77.7172]  # Erode
        ],
        "progress": 1.0,
        "speed_kmh": 0.0,
        "door_status": "Closed",
        "battery_percent": 99.0,
        "temp_front": -21.0,
        "temp_mid": -20.4,
        "temp_rear": -19.8,
        "humidity": 70.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "refreezing_detected": "No",
        "active": True
    }
}

VEHICLE_HISTORY = {vid: [] for vid in FLEET_LORRIES}
ACTIVE_ALERTS = [
    {
        "id": "ALT-101",
        "title": "Temperature Spike Detected",
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "description": "TN-33-CC-204 • -18.2°C in 30 min",
        "timestamp": "09:52 AM",
        "alert_level": "Critical",
        "condition": "Thawing Risk",
        "raw_time": time.time() - 1200,
        "door_status": "Open",
        "temp_front": -16.4,
        "temp_mid": -13.8,
        "temp_rear": -7.5,
        "read": False
    },
    {
        "id": "ALT-102",
        "title": "Compartment Door Open",
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "description": "Rear Door • TN-33-CC-204",
        "timestamp": "09:47 AM",
        "alert_level": "Warning",
        "condition": "Warning",
        "raw_time": time.time() - 1500,
        "door_status": "Open",
        "temp_front": -16.8,
        "temp_mid": -14.2,
        "temp_rear": -8.1,
        "read": False
    },
    {
        "id": "ALT-103",
        "title": "Temperature Back to Normal",
        "vehicle_id": "TN-38-CC-181",
        "truck_id": "T-103",
        "description": "TN-38-CC-181 • -20.1°C",
        "timestamp": "08:20 AM",
        "alert_level": "Info",
        "condition": "Safe",
        "raw_time": time.time() - 7200,
        "door_status": "Closed",
        "temp_front": -21.4,
        "temp_mid": -20.1,
        "temp_rear": -19.0,
        "read": False
    },
    {
        "id": "ALT-104",
        "title": "Shipment Delivered",
        "vehicle_id": "TN-39-CC-221",
        "truck_id": "T-102",
        "description": "TN-39-CC-221 • Salem Terminal",
        "timestamp": "Yesterday",
        "alert_level": "Info",
        "condition": "Delivered",
        "raw_time": time.time() - 86400,
        "door_status": "Closed",
        "temp_front": -20.5,
        "temp_mid": -20.1,
        "temp_rear": -19.8,
        "read": False
    }
]

SYSTEM_SETTINGS = {
    "temp_min": -25.0,
    "temp_max": -18.0,
    "email_alerts": True,
    "sms_alerts": True,
    "push_notifications": True,
    "version": "v1.0.0",
    "last_updated": "Nov 13, 2026",
    "app_name": "FrostGuard",
    "tagline": "Keep Every Scoop Cold"
}

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

# Initialize historical points (30 historical intervals)
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
        time.sleep(1.5)
        with state_lock:
            ts_str = datetime.now().strftime("%H:%M:%S")
            
            for vid, v in FLEET_LORRIES.items():
                if v["status_label"] != "Delivered":
                    if v["door_status"] == "Closed":
                        v["progress"] += 0.004
                        if v["progress"] > 1.0:
                            v["progress"] = 0.02
                        lat, lng = get_route_position(v["waypoints"], v["progress"])
                        v["gps_lat"] = lat
                        v["gps_lng"] = lng
                        v["speed_kmh"] = round(random.uniform(42.0, 55.0), 1)
                    else:
                        v["speed_kmh"] = 0.0

                # 3 Temperature Detectors Simulation
                if vid == "TN-33-CC-204":
                    if v["door_status"] == "Open":
                        v["temp_rear"] = min(-6.8, v["temp_rear"] + round(random.uniform(0.03, 0.12), 2))
                        v["temp_mid"]  = min(-13.0, v["temp_mid"]  + round(random.uniform(0.02, 0.07), 2))
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
        all_hist = {vid: hist[-45:] for vid, hist in VEHICLE_HISTORY.items()}

        active_alerts_list = [a for a in ACTIVE_ALERTS if not a.get("read", False)]

        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_str": datetime.now().strftime("%I:%M %p"),
            "region": "Kongu Region, Tamil Nadu",
            "fleet_summary": {
                "total_shipments": 12,
                "in_transit": 6,
                "delivered": 5,
                "delayed": 1,
                "active_transports": total_lorries,
                "safe_count": lorries_safe,
                "warning_count": lorries_warn,
                "critical_count": lorries_crit,
                "door_open_count": door_open_count
            },
            "spoilage_stats": {
                "spoilage_rate_pct": 2.6,
                "potential_spoilage_kg": 18,
                "prevented_spoilage_kg": 15,
                "savings_inr": 6300,
                "compliance_pct": 96.4,
                "cold_chain_health_pct": 98.0,
                "shipment_performance_pct": 94.0
            },
            "hubs": KONGU_HUBS,
            "fleet": FLEET_LORRIES,
            "active_vehicle_id": active_vid,
            "active_vehicle": active_v,
            "active_history": active_hist,
            "fleet_history": all_hist,
            "active_alerts": active_alerts_list,
            "all_alerts": ACTIVE_ALERTS,
            "audit_log": AUDIT_LOG[:10],
            "settings": SYSTEM_SETTINGS
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

@app.route('/api/alerts/read-all', methods=['POST'])
def read_all_alerts():
    with state_lock:
        for a in ACTIVE_ALERTS:
            a["read"] = True
        return jsonify({"status": "success", "message": "All alerts marked as read"})

@app.route('/api/settings', methods=['GET', 'POST'])
def manage_settings():
    global SYSTEM_SETTINGS
    if request.method == 'POST':
        data = request.get_json() or {}
        with state_lock:
            if "temp_min" in data: SYSTEM_SETTINGS["temp_min"] = float(data["temp_min"])
            if "temp_max" in data: SYSTEM_SETTINGS["temp_max"] = float(data["temp_max"])
            if "email_alerts" in data: SYSTEM_SETTINGS["email_alerts"] = bool(data["email_alerts"])
            if "sms_alerts" in data: SYSTEM_SETTINGS["sms_alerts"] = bool(data["sms_alerts"])
            if "push_notifications" in data: SYSTEM_SETTINGS["push_notifications"] = bool(data["push_notifications"])
            return jsonify({"status": "success", "settings": SYSTEM_SETTINGS})
    return jsonify(SYSTEM_SETTINGS)

@app.route('/api/ai/diagnose', methods=['POST'])
def ai_diagnose():
    data = request.get_json() or {}
    vid = data.get("vehicle_id", ACTIVE_VEHICLE_ID)
    with state_lock:
        v = FLEET_LORRIES.get(vid, list(FLEET_LORRIES.values())[0])

    prompt = f"""You are the FrostGuard Cold Chain Fleet Intelligence Officer.
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
2. QUALITY & TEXTURE RISK (Ice crystal coarsening / thawing)
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
            ai_text = f"""1. ROOT-CAUSE DIAGNOSIS: Thermal breach in rear zone (+{v['thermal_gradient']}°C gradient). Rear detector heated to {v['temp_rear']}°C while front evaporator is at {v['temp_front']}°C. Warm air & humidity ingress via open compartment door on {v['route_name']}.
2. QUALITY & TEXTURE RISK: Critical thawing hazard. Ice crystal matrix destabilizing in rear pallets. Rapid recrystallization will cause grittiness and product loss.
3. IMMEDIATE DISPATCHER DIRECTIVE: Call driver {v['driver']} ({v['driver_phone']}) immediately. Secure rear door latches, switch refrigeration to continuous maximum override, and divert to Perundurai SIPCOT Cold Vault if temp remains above -15°C.
4. FINANCIAL EXPOSURE: High risk on total shipment value of ₹ {v['cargo_val_inr']:,}. Immediate sealing preserves ₹ 4.1L of core mass."""
        else:
            ai_text = f"""1. ROOT-CAUSE DIAGNOSIS: Optimal deep freeze operation. Chamber thermal gradient is balanced at +{v['thermal_gradient']}°C, indicating uniform airflow across pallets.
2. QUALITY & TEXTURE RISK: Zero recrystallization risk. All 3 detectors maintain temperatures below the critical -18.0°C threshold.
3. IMMEDIATE DISPATCHER DIRECTIVE: Lorry is on schedule along {v['route_name']}. Maintain current transit speed ({v['speed_kmh']} km/h).
4. FINANCIAL EXPOSURE: Cargo valuation of ₹ {v['cargo_val_inr']:,} is 100% compliant and protected."""

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
        return send_file(csv_path, as_attachment=True, download_name="frostguard_kongu_fleet_telemetry.csv")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"FrostGuard Cold Chain Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
