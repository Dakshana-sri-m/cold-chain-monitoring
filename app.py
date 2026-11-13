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
# KONGU REGION LOGISTICS CORRIDORS & LOGISTICS HUBS (SOURCE & DESTINATION)
# ---------------------------------------------------------------------------
LOGISTICS_HUBS = {
    "CBE-01": {"id": "CBE-01", "name": "Coimbatore Mega Dairy Hub", "city": "Coimbatore", "lat": 11.0168, "lng": 76.9558, "type": "Origin Plant"},
    "TPR-01": {"id": "TPR-01", "name": "Tirupur Cold Distribution Bay", "city": "Tirupur", "lat": 11.1085, "lng": 77.3411, "type": "Waypoint Bay"},
    "PRD-01": {"id": "PRD-01", "name": "Perundurai SIPCOT Cold Vault", "city": "Perundurai", "lat": 11.2750, "lng": 77.5850, "type": "Transit Vault"},
    "ERD-01": {"id": "ERD-01", "name": "Erode Regional Cold Storage", "city": "Erode", "lat": 11.3410, "lng": 77.7172, "type": "Regional Hub"},
    "SLM-01": {"id": "SLM-01", "name": "Salem Central Refrigerated Terminal", "city": "Salem", "lat": 11.6643, "lng": 78.1460, "type": "Mega Terminal"},
    "NMK-01": {"id": "NMK-01", "name": "Namakkal Cold Chain Transfer Base", "city": "Namakkal", "lat": 11.2189, "lng": 78.1674, "type": "Dairy Terminal"},
    "KRR-01": {"id": "KRR-01", "name": "Karur Perishables Bay", "city": "Karur", "lat": 10.9601, "lng": 78.0766, "type": "Regional Bay"},
    "OTY-01": {"id": "OTY-01", "name": "Nilgiris High-Altitude Cold Vault", "city": "Ooty", "lat": 11.4102, "lng": 76.6950, "type": "Hardening Plant"}
}

# Corridors grouping multiple concurrent lorries running on the SAME Source -> Destination
LOGISTICS_CORRIDORS = {
    "COR-ERD-SLM": {
        "id": "COR-ERD-SLM",
        "name": "Erode to Salem Corridor (NH544)",
        "source": "Erode Regional Cold Storage (ERD-01)",
        "destination": "Salem Central Refrigerated Terminal (SLM-01)",
        "distance_km": 64.0,
        "active_vehicles": ["TN-33-CC-204", "TN-33-CC-512"]
    },
    "COR-CBE-ERD": {
        "id": "COR-CBE-ERD",
        "name": "Coimbatore to Erode Corridor (NH544)",
        "source": "Coimbatore Mega Dairy Hub (CBE-01)",
        "destination": "Erode Regional Cold Storage (ERD-01)",
        "distance_km": 98.0,
        "active_vehicles": ["TN-38-CC-181", "TN-38-CC-290"]
    },
    "COR-OTY-CBE": {
        "id": "COR-OTY-CBE",
        "name": "Nilgiris/Ooty to Coimbatore Corridor (NH181)",
        "source": "Nilgiris Cold Vault, Ooty (OTY-01)",
        "destination": "Coimbatore Mega Dairy Hub (CBE-01)",
        "distance_km": 86.0,
        "active_vehicles": ["TN-43-CC-309", "TN-43-CC-114"]
    },
    "COR-NMK-KRR": {
        "id": "COR-NMK-KRR",
        "name": "Namakkal to Karur Corridor (NH44)",
        "source": "Namakkal Cold Chain Transfer Base (NMK-01)",
        "destination": "Karur Perishables Bay (KRR-01)",
        "distance_km": 48.0,
        "active_vehicles": ["TN-41-CC-276", "TN-28-CC-415"]
    }
}

# ---------------------------------------------------------------------------
# LOGISTICS REFRIGERATED FLEET (3 IoT DETECTORS PER LORRY)
# ---------------------------------------------------------------------------
FLEET_LORRIES = {
    # Corridor 1: Erode -> Salem
    "TN-33-CC-204": {
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "name": "Erode Cold Carrier Alpha",
        "corridor_id": "COR-ERD-SLM",
        "corridor_name": "Erode to Salem (NH544)",
        "source_hub": "Erode Regional Storage",
        "destination_hub": "Salem Central Terminal",
        "departure_time": "08:30 AM",
        "eta": "1h 20m",
        "driver": "K. Murugan",
        "driver_phone": "+91 98422 71045",
        "product": "Milk & Soft Ice Cream",
        "cargo_type": "Milk & Ice Cream",
        "cargo_load_kg": 4800,
        "cargo_val_inr": 432000,
        "route_color": "#ef4444", # Red (Incident)
        "status_label": "On Route",
        "current_location": "Sankari Bypass (NH544)",
        "waypoints": [
            [11.3410, 77.7172], # Erode
            [11.3900, 77.7400], # Chithode
            [11.4450, 77.7780], # Bhavani
            [11.4880, 77.8720], # Sankari Toll
            [11.5300, 77.9600], # Magudanchavadi
            [11.5900, 78.0400], # Ariyanoor
            [11.6643, 78.1460]  # Salem
        ],
        "progress": 0.55,
        "speed_kmh": 0.0,
        "door_status": "Open", # INCIDENT: Rear Door Open Excursion
        "battery_percent": 88.0,
        # 3 Dedicated Devices inside the transport lorry
        "device_1_front": -16.4, # Chiller Evaporator Delivery
        "device_2_mid":   -13.8, # Core Pallet Mass
        "device_3_rear":  -7.5,  # Rear Door / Influx Zone
        "temp_front": -16.4,
        "temp_mid": -13.8,
        "temp_rear": -7.5,
        "humidity": 89.2,
        "alert_level": "Critical",
        "condition": "Thawing Risk",
        "excursion_type": "Localized Rear Door Influx Breach",
        "active": True
    },
    "TN-33-CC-512": {
        "vehicle_id": "TN-33-CC-512",
        "truck_id": "T-108",
        "name": "Erode Cold Carrier Beta",
        "corridor_id": "COR-ERD-SLM",
        "corridor_name": "Erode to Salem (NH544)",
        "source_hub": "Erode Regional Storage",
        "destination_hub": "Salem Central Terminal",
        "departure_time": "09:15 AM",
        "eta": "2h 05m",
        "driver": "M. Karthik",
        "driver_phone": "+91 94433 11872",
        "product": "Ice Cream Tubs & Cones",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 5000,
        "cargo_val_inr": 450000,
        "route_color": "#10b981", # Green (Healthy comparator on same route!)
        "status_label": "On Route",
        "current_location": "Chithode Bypass",
        "waypoints": [
            [11.3410, 77.7172],
            [11.3900, 77.7400],
            [11.4450, 77.7780],
            [11.4880, 77.8720],
            [11.5300, 77.9600],
            [11.5900, 78.0400],
            [11.6643, 78.1460]
        ],
        "progress": 0.22,
        "speed_kmh": 52.0,
        "door_status": "Closed",
        "battery_percent": 97.0,
        "device_1_front": -21.8,
        "device_2_mid":   -20.4,
        "device_3_rear":  -19.6,
        "temp_front": -21.8,
        "temp_mid": -20.4,
        "temp_rear": -19.6,
        "humidity": 71.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },

    # Corridor 2: Coimbatore -> Erode
    "TN-38-CC-181": {
        "vehicle_id": "TN-38-CC-181",
        "truck_id": "T-103",
        "name": "Kongu Dairy Express 1",
        "corridor_id": "COR-CBE-ERD",
        "corridor_name": "Coimbatore to Erode (NH544)",
        "source_hub": "Coimbatore Mega Dairy Hub",
        "destination_hub": "Erode Regional Storage",
        "departure_time": "07:45 AM",
        "eta": "45m",
        "driver": "M. Senthil Kumar",
        "driver_phone": "+91 94431 22891",
        "product": "Ice Cream Pints",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 5200,
        "cargo_val_inr": 468000,
        "route_color": "#10b981", # Green
        "status_label": "At Depot",
        "current_location": "Perundurai SIPCOT",
        "waypoints": [
            [11.0168, 76.9558],
            [11.0420, 77.0300],
            [11.0650, 77.1050],
            [11.1300, 77.2000],
            [11.1900, 77.2700],
            [11.1085, 77.3411],
            [11.1850, 77.4400],
            [11.2750, 77.5850],
            [11.3410, 77.7172]
        ],
        "progress": 0.85,
        "speed_kmh": 46.0,
        "door_status": "Closed",
        "battery_percent": 96.5,
        "device_1_front": -21.2,
        "device_2_mid":   -19.8,
        "device_3_rear":  -18.7,
        "temp_front": -21.2,
        "temp_mid": -19.8,
        "temp_rear": -18.7,
        "humidity": 72.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },
    "TN-38-CC-290": {
        "vehicle_id": "TN-38-CC-290",
        "truck_id": "T-104",
        "name": "Kongu Dairy Express 2",
        "corridor_id": "COR-CBE-ERD",
        "corridor_name": "Coimbatore to Erode (NH544)",
        "source_hub": "Coimbatore Mega Dairy Hub",
        "destination_hub": "Erode Regional Storage",
        "departure_time": "09:00 AM",
        "eta": "2h 10m",
        "driver": "R. Prakash",
        "driver_phone": "+91 94441 55210",
        "product": "Frozen Yogurt & Bars",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 4600,
        "cargo_val_inr": 414000,
        "route_color": "#06b6d4", # Cyan
        "status_label": "On Route",
        "current_location": "Avinashi Bypass",
        "waypoints": [
            [11.0168, 76.9558],
            [11.0420, 77.0300],
            [11.0650, 77.1050],
            [11.1300, 77.2000],
            [11.1900, 77.2700],
            [11.1085, 77.3411],
            [11.1850, 77.4400],
            [11.2750, 77.5850],
            [11.3410, 77.7172]
        ],
        "progress": 0.40,
        "speed_kmh": 50.0,
        "door_status": "Closed",
        "battery_percent": 98.0,
        "device_1_front": -22.0,
        "device_2_mid":   -20.9,
        "device_3_rear":  -19.8,
        "temp_front": -22.0,
        "temp_mid": -20.9,
        "temp_rear": -19.8,
        "humidity": 69.5,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },

    # Corridor 3: Nilgiris/Ooty -> Coimbatore
    "TN-43-CC-309": {
        "vehicle_id": "TN-43-CC-309",
        "truck_id": "T-107",
        "name": "Nilgiris Mountain Vault 1",
        "corridor_id": "COR-OTY-CBE",
        "corridor_name": "Nilgiris to Coimbatore (NH181)",
        "source_hub": "Nilgiris Vault, Ooty",
        "destination_hub": "Coimbatore Mega Dairy Hub",
        "departure_time": "08:00 AM",
        "eta": "3h 05m",
        "driver": "A. Balaji",
        "driver_phone": "+91 99441 55620",
        "product": "Frozen Veg & Ice Cream",
        "cargo_type": "Frozen Veg",
        "cargo_load_kg": 3600,
        "cargo_val_inr": 324000,
        "route_color": "#06b6d4",
        "status_label": "On Route",
        "current_location": "Coonoor Ghats",
        "waypoints": [
            [11.4102, 76.6950],
            [11.3700, 76.7500],
            [11.3530, 76.7950],
            [11.3100, 76.8800],
            [11.2995, 76.9427],
            [11.2100, 76.9450],
            [11.1200, 76.9500],
            [11.0168, 76.9558]
        ],
        "progress": 0.30,
        "speed_kmh": 38.0,
        "door_status": "Closed",
        "battery_percent": 98.0,
        "device_1_front": -22.5,
        "device_2_mid":   -21.5,
        "device_3_rear":  -20.6,
        "temp_front": -22.5,
        "temp_mid": -21.5,
        "temp_rear": -20.6,
        "humidity": 68.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },
    "TN-43-CC-114": {
        "vehicle_id": "TN-43-CC-114",
        "truck_id": "T-106",
        "name": "Nilgiris Mountain Vault 2",
        "corridor_id": "COR-OTY-CBE",
        "corridor_name": "Nilgiris to Coimbatore (NH181)",
        "source_hub": "Nilgiris Vault, Ooty",
        "destination_hub": "Coimbatore Mega Dairy Hub",
        "departure_time": "09:30 AM",
        "eta": "4h 15m",
        "driver": "V. Ganesan",
        "driver_phone": "+91 98942 66731",
        "product": "Artisanal Dairy Pints",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 3800,
        "cargo_val_inr": 342000,
        "route_color": "#8b5cf6",
        "status_label": "On Route",
        "current_location": "Aruvankadu Sector",
        "waypoints": [
            [11.4102, 76.6950],
            [11.3700, 76.7500],
            [11.3530, 76.7950],
            [11.3100, 76.8800],
            [11.2995, 76.9427],
            [11.2100, 76.9450],
            [11.1200, 76.9500],
            [11.0168, 76.9558]
        ],
        "progress": 0.15,
        "speed_kmh": 35.0,
        "door_status": "Closed",
        "battery_percent": 99.0,
        "device_1_front": -22.8,
        "device_2_mid":   -21.9,
        "device_3_rear":  -21.0,
        "temp_front": -22.8,
        "temp_mid": -21.9,
        "temp_rear": -21.0,
        "humidity": 67.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },

    # Corridor 4: Namakkal -> Karur
    "TN-41-CC-276": {
        "vehicle_id": "TN-41-CC-276",
        "truck_id": "T-105",
        "name": "Namakkal Cold Liner Alpha",
        "corridor_id": "COR-NMK-KRR",
        "corridor_name": "Namakkal to Karur (NH44)",
        "source_hub": "Namakkal Base",
        "destination_hub": "Karur Perishables Bay",
        "departure_time": "07:15 AM",
        "eta": "4h 30m",
        "driver": "P. Ramesh",
        "driver_phone": "+91 97890 33412",
        "product": "Dairy Desserts",
        "cargo_type": "Dairy",
        "cargo_load_kg": 4400,
        "cargo_val_inr": 396000,
        "route_color": "#f59e0b",
        "status_label": "Delayed",
        "current_location": "Paramathi NH44",
        "waypoints": [
            [11.2189, 78.1674],
            [11.1600, 78.1400],
            [11.1000, 78.0800],
            [11.0500, 78.0100],
            [10.9900, 78.0400],
            [10.9601, 78.0766]
        ],
        "progress": 0.50,
        "speed_kmh": 22.0, # Slow traffic / delayed
        "door_status": "Closed",
        "battery_percent": 91.2,
        "device_1_front": -20.1,
        "device_2_mid":   -19.2,
        "device_3_rear":  -18.2,
        "temp_front": -20.1,
        "temp_mid": -19.2,
        "temp_rear": -18.2,
        "humidity": 76.5,
        "alert_level": "Warning",
        "condition": "Warning",
        "excursion_type": "Traffic Delay Drift",
        "active": True
    },
    "TN-28-CC-415": {
        "vehicle_id": "TN-28-CC-415",
        "truck_id": "T-109",
        "name": "Namakkal Cold Liner Beta",
        "corridor_id": "COR-NMK-KRR",
        "corridor_name": "Namakkal to Karur (NH44)",
        "source_hub": "Namakkal Base",
        "destination_hub": "Karur Perishables Bay",
        "departure_time": "08:45 AM",
        "eta": "1h 50m",
        "driver": "D. Vignesh",
        "driver_phone": "+91 97901 88412",
        "product": "Ice Cream Bulk Bricks",
        "cargo_type": "Ice Cream",
        "cargo_load_kg": 4200,
        "cargo_val_inr": 378000,
        "route_color": "#10b981",
        "status_label": "On Route",
        "current_location": "Velur Cauvery Bridge",
        "waypoints": [
            [11.2189, 78.1674],
            [11.1600, 78.1400],
            [11.1000, 78.0800],
            [11.0500, 78.0100],
            [10.9900, 78.0400],
            [10.9601, 78.0766]
        ],
        "progress": 0.65,
        "speed_kmh": 48.0,
        "door_status": "Closed",
        "battery_percent": 95.0,
        "device_1_front": -21.5,
        "device_2_mid":   -20.1,
        "device_3_rear":  -19.2,
        "temp_front": -21.5,
        "temp_mid": -20.1,
        "temp_rear": -19.2,
        "humidity": 73.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Fully Compliant)",
        "active": True
    },

    # Destination Bay Completed
    "TN-39-CC-221": {
        "vehicle_id": "TN-39-CC-221",
        "truck_id": "T-102",
        "name": "Salem Perishables Runner",
        "corridor_id": "COR-ERD-SLM",
        "corridor_name": "Salem to Erode (NH544)",
        "source_hub": "Salem Central Terminal",
        "destination_hub": "Erode Regional Storage",
        "departure_time": "06:00 AM",
        "eta": "Delivered",
        "driver": "S. Rajesh",
        "driver_phone": "+91 94421 88392",
        "product": "Fruits & Dairy",
        "cargo_type": "Fruits",
        "cargo_load_kg": 4100,
        "cargo_val_inr": 369000,
        "route_color": "#64748b",
        "status_label": "Delivered",
        "current_location": "Erode Bay (Completed)",
        "waypoints": [
            [11.6643, 78.1460],
            [11.5900, 78.0400],
            [11.4880, 77.8720],
            [11.3410, 77.7172]
        ],
        "progress": 1.0,
        "speed_kmh": 0.0,
        "door_status": "Closed",
        "battery_percent": 99.0,
        "device_1_front": -21.0,
        "device_2_mid":   -20.4,
        "device_3_rear":  -19.8,
        "temp_front": -21.0,
        "temp_mid": -20.4,
        "temp_rear": -19.8,
        "humidity": 70.0,
        "alert_level": "No Alert",
        "condition": "Safe",
        "excursion_type": "None (Delivered)",
        "active": True
    }
}

VEHICLE_HISTORY = {vid: [] for vid in FLEET_LORRIES}
ACTIVE_ALERTS = [
    {
        "id": "ALT-101",
        "title": "Temperature Spike Detected (Device 3 Rear)",
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "corridor": "Erode -> Salem (NH544)",
        "description": "TN-33-CC-204 • Device 3 heated to -7.5°C (Threshold: -18°C)",
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
        "title": "Compartment Rear Door Open",
        "vehicle_id": "TN-33-CC-204",
        "truck_id": "T-101",
        "corridor": "Erode -> Salem (NH544)",
        "description": "Rear Door Latch Unsecured • Sankari Bypass",
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
        "title": "Route Transit Speed Normal",
        "vehicle_id": "TN-38-CC-181",
        "truck_id": "T-103",
        "corridor": "Coimbatore -> Erode (NH544)",
        "description": "TN-38-CC-181 • All 3 Devices Safe (-20.1°C avg)",
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
        "title": "Shipment Batch Delivered",
        "vehicle_id": "TN-39-CC-221",
        "truck_id": "T-102",
        "corridor": "Salem -> Erode",
        "description": "TN-39-CC-221 • Erode Regional Storage Bay",
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
    "version": "v1.2.0",
    "last_updated": "Nov 13, 2026",
    "app_name": "FrostGuard Logistics",
    "tagline": "3-Device Cold Chain Fleet Excursion Center"
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
                "device_1_front": tf,
                "device_2_mid": tm,
                "device_3_rear": tr,
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
                        v["progress"] += 0.003
                        if v["progress"] > 1.0:
                            v["progress"] = 0.05
                        lat, lng = get_route_position(v["waypoints"], v["progress"])
                        v["gps_lat"] = lat
                        v["gps_lng"] = lng
                        v["speed_kmh"] = round(random.uniform(44.0, 56.0), 1)
                    else:
                        v["speed_kmh"] = 0.0

                # 3 Temperature Detectors Physics Simulation
                if vid == "TN-33-CC-204":
                    # Incident vehicle: Door Open causing Rear Device 3 thermal breach
                    if v["door_status"] == "Open":
                        v["device_3_rear"] = min(-6.8, v["device_3_rear"] + round(random.uniform(0.03, 0.12), 2))
                        v["device_2_mid"]  = min(-13.0, v["device_2_mid"]  + round(random.uniform(0.02, 0.06), 2))
                        v["device_1_front"]= min(-15.8, v["device_1_front"]+ round(random.uniform(0.01, 0.03), 2))
                        v["humidity"]      = min(93.0, v["humidity"]        + round(random.uniform(0.1, 0.3), 1))
                    else:
                        v["device_3_rear"] = max(-19.5, v["device_3_rear"] - 0.15)
                        v["device_2_mid"]  = max(-20.5, v["device_2_mid"]  - 0.10)
                        v["device_1_front"]= max(-22.0, v["device_1_front"]- 0.08)
                        v["humidity"]      = max(71.0, v["humidity"]        - 0.3)
                else:
                    jitter = (random.random() - 0.5) * 0.15
                    v["device_1_front"] = round(v["device_1_front"] + jitter, 1)
                    v["device_2_mid"]   = round(v["device_2_mid"]   + jitter * 0.8, 1)
                    v["device_3_rear"]  = round(v["device_3_rear"]  + jitter * 1.2, 1)
                    v["humidity"]       = round(v["humidity"]       + (random.random() - 0.5) * 0.3, 1)

                v["temp_front"] = v["device_1_front"]
                v["temp_mid"]   = v["device_2_mid"]
                v["temp_rear"]  = v["device_3_rear"]
                v["temp_avg"] = round((v["temp_front"] + v["temp_mid"] + v["temp_rear"]) / 3.0, 2)
                v["thermal_gradient"] = round(v["temp_rear"] - v["temp_front"], 2)
                v["deviation"] = round(v["temp_avg"] - (-18.0), 2)
                v["battery_percent"] = max(10.0, round(v["battery_percent"] - 0.002, 2))

                max_t = max(v["temp_front"], v["temp_mid"], v["temp_rear"])
                if max_t >= -10.0:
                    v["alert_level"] = "Critical"
                    v["condition"] = "Thawing Risk"
                    v["excursion_type"] = "Localized Rear Door Influx Breach" if v["door_status"] == "Open" else "Severe Core Excursion"
                elif max_t > -15.0:
                    v["alert_level"] = "Critical"
                    v["condition"] = "High Risk"
                    v["excursion_type"] = "High Thermal Drift"
                elif max_t > -18.0:
                    v["alert_level"] = "Warning"
                    v["condition"] = "Warning"
                    v["excursion_type"] = "Pre-Thaw Borderline Excursion"
                else:
                    v["alert_level"] = "No Alert"
                    v["condition"] = "Safe"
                    v["excursion_type"] = "None (Fully Compliant)"

                new_point = {
                    "timestamp": ts_str,
                    "device_1_front": v["temp_front"],
                    "device_2_mid": v["temp_mid"],
                    "device_3_rear": v["temp_rear"],
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

        # Group vehicles by Corridor for Logistics Efficiency
        corridor_data = {}
        for cid, corr in LOGISTICS_CORRIDORS.items():
            vehicles_on_corridor = [FLEET_LORRIES[vid] for vid in corr["active_vehicles"] if vid in FLEET_LORRIES]
            corridor_data[cid] = {
                **corr,
                "vehicles": vehicles_on_corridor,
                "avg_temp": round(np.mean([v["temp_avg"] for v in vehicles_on_corridor]), 1) if vehicles_on_corridor else -19.5,
                "has_excursion": any(v["alert_level"] != "No Alert" for v in vehicles_on_corridor)
            }

        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "time_str": datetime.now().strftime("%I:%M %p"),
            "region": "Kongu Logistics Belt, Tamil Nadu",
            "fleet_summary": {
                "total_shipments": 12,
                "in_transit": 8,
                "delivered": 1,
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
            "hubs": LOGISTICS_HUBS,
            "corridors": corridor_data,
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
        # Find companion vehicle on the SAME corridor
        companion = next((other for other in FLEET_LORRIES.values() if other["corridor_id"] == v["corridor_id"] and other["vehicle_id"] != v["vehicle_id"]), None)

    comp_info = ""
    if companion:
        comp_info = f"Companion vehicle {companion['vehicle_id']} running on the same corridor ({v['corridor_name']}) has Device 1: {companion['temp_front']}°C, Device 2: {companion['temp_mid']}°C, Device 3: {companion['temp_rear']}°C (Fully Compliant)."

    prompt = f"""You are the FrostGuard Fleet Logistics Intelligence Officer.
Analyze live telemetry for Refrigerated Transport Lorry {v['vehicle_id']} on route {v['source_hub']} -> {v['destination_hub']} ({v['corridor_name']}) in Kongu region, Tamil Nadu:
- Product: {v['product']} (Safe setpoint <= -18.0 C)
- Cargo Value: Rs. {v['cargo_val_inr']:,} ({v['cargo_load_kg']} kg)
- 3 IN-VEHICLE TEMPERATURE DETECTORS:
  * Device 1 (Front/Chiller Air Delivery): {v['temp_front']} C
  * Device 2 (Middle/Cargo Core Center): {v['temp_mid']} C
  * Device 3 (Rear/Back Door Zone): {v['temp_rear']} C
- Thermal Gradient (Device 3 - Device 1): +{v['thermal_gradient']} C
- Compartment Door Status: {v['door_status']}
- Chamber Relative Humidity: {v['humidity']}%
- Transit Speed: {v['speed_kmh']} km/h
- Excursion Type: {v['excursion_type']}
- Same Corridor Benchmark: {comp_info}

Provide a 4-point executive logistics advisory for the fleet owner:
1. 3-DEVICE EXCURSION DIAGNOSIS (Identify whether failure is compressor or door influx breach based on the 3 probes)
2. SAME-CORRIDOR EFFICIENCY COMPARISON (Contrast with other vehicle on same route)
3. IMMEDIATE DISPATCHER DIRECTIVE for driver {v['driver']} ({v['driver_phone']})
4. FINANCIAL EXPOSURE & CARGO RESCUE RECOMMENDATION"""

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
            ai_text = f"""1. 3-DEVICE EXCURSION DIAGNOSIS: Spatial thermal breach at rear loading zone (+{v['thermal_gradient']}°C gradient). Device 3 (Rear) heated to {v['temp_rear']}°C while Device 1 (Chiller Delivery) remains cold at {v['temp_front']}°C. This proves the Thermo King chiller is functional, but warm ambient air is infiltrating through an unsecured rear door latch on {v['corridor_name']}.
2. SAME-CORRIDOR EFFICIENCY COMPARISON: Companion lorry {companion['vehicle_id'] if companion else 'TN-33-CC-512'} operating simultaneously on the Erode -> Salem corridor maintains -20.4°C across all 3 devices, confirming that highway weather/ambient heat is NOT the cause of the excursion.
3. IMMEDIATE DISPATCHER DIRECTIVE: Call driver {v['driver']} ({v['driver_phone']}) immediately. Pull over at Sankari Toll bay, secure rear door latches, and switch evaporator to continuous max cooling override.
4. FINANCIAL EXPOSURE & CARGO RESCUE: High risk on ₹ {v['cargo_val_inr']:,}. Immediate sealing preserves the core mass (Device 2: {v['temp_mid']}°C) before crystal lattice softening occurs."""
        else:
            ai_text = f"""1. 3-DEVICE EXCURSION DIAGNOSIS: Optimal 3-zone preservation. Device 1 ({v['temp_front']}°C), Device 2 ({v['temp_mid']}°C), and Device 3 ({v['temp_rear']}°C) are all below the critical -18°C setpoint. Thermal gradient is balanced at +{v['thermal_gradient']}°C.
2. SAME-CORRIDOR EFFICIENCY COMPARISON: Consistent with multi-lorry performance along {v['corridor_name']}. Fleet energy efficiency rating is 98.4%.
3. IMMEDIATE DISPATCHER DIRECTIVE: Vehicle is on schedule from {v['source_hub']} to {v['destination_hub']}. Maintain cruising speed ({v['speed_kmh']} km/h).
4. FINANCIAL EXPOSURE: Zero cargo loss risk across ₹ {v['cargo_val_inr']:,} valuation."""

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
    tf = payload.get("temp_front") or payload.get("device_1_front")
    tm = payload.get("temp_mid") or payload.get("device_2_mid")
    tr = payload.get("temp_rear") or payload.get("device_3_rear")
    
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
            v["device_1_front"] = round(tf, 1)
            v["device_2_mid"]   = round(tm, 1)
            v["device_3_rear"]  = round(tr, 1)
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
            v = FLEET_LORRIES[vid]
            for pt in history:
                rows.append({
                    "Vehicle_ID": vid,
                    "Corridor": v["corridor_name"],
                    "Source_Hub": v["source_hub"],
                    "Destination_Hub": v["destination_hub"],
                    "Timestamp": pt["timestamp"],
                    "Device_1_Front_Chiller_C": pt["device_1_front"],
                    "Device_2_Mid_Core_C": pt["device_2_mid"],
                    "Device_3_Rear_Door_C": pt["device_3_rear"],
                    "Chamber_Average_C": pt["temp_avg"],
                    "Thermal_Gradient_Delta_C": pt["gradient"],
                    "Humidity_Percent": pt["humidity"],
                    "Door_Status": pt["door_status"],
                    "Battery_Percent": pt["battery"]
                })
        df = pd.DataFrame(rows)
        csv_path = os.path.join('static', 'kongu_fleet_cold_chain_telemetry.csv')
        df.to_csv(csv_path, index=False)
        return send_file(csv_path, as_attachment=True, download_name="frostguard_logistics_telemetry.csv")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5050))
    print(f"FrostGuard Logistics Fleet Server running on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
