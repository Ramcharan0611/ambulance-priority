import os
import json
import math
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "database.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Initialize Socket.IO and FastAPI
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI(title="Smart Ambulance Traffic Signal Priority & Advance Clearance System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database cache with persistence
db: Dict[str, Any] = {}

def load_db():
    global db
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {}

def save_db():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)

load_db()

# --- Geographic Math Utilities ---
def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate Great Circle distance between two points in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate bearing from point 1 to point 2 in degrees (0-360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)
    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360.0) % 360.0

# --- Real-Time Simulation State ---
sim_task: Optional[asyncio.Task] = None
active_simulation = {
    "is_running": False,
    "trip_id": None,
    "ambulance_id": None,
    "target_waypoints": [],
    "current_waypoint_index": 0,
    "segment_progress": 0.0, # 0.0 to 1.0 along current segment
    "speed_kmh": 60.0,
    "step_multiplier": 1.0,
    "auto_police_response": True, # If true, simulates officer clearance automatically after realistic delay
    "is_rerouted": False
}

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    # Send initial state snapshot to connected client
    active_trips = [t for t in db.get("trips", []) if t.get("status") in ["ACTIVE", "EN_ROUTE_PATIENT"]]
    await sio.emit("system:init", {
        "ambulances": db.get("ambulances", []),
        "intersections": db.get("intersections", []),
        "signals": db.get("trafficSignals", []),
        "hospitals": db.get("hospitals", []),
        "police": db.get("trafficPolice", []),
        "activeTrips": active_trips,
        "settings": db.get("settings", {}),
        "recentEvents": db.get("clearanceEvents", [])[-20:]
    }, to=sid)

@sio.event
async def disconnect(sid):
    pass

# --- Simulation Background Loop ---
async def simulation_loop():
    while active_simulation["is_running"]:
        try:
            await advance_simulation_step()
        except Exception as e:
            print(f"Simulation error: {e}")
        await asyncio.sleep(1.0)

async def advance_simulation_step():
    if not active_simulation["is_running"] or not active_simulation["trip_id"]:
        return

    trip_id = active_simulation["trip_id"]
    trip = next((t for t in db.get("trips", []) if t["tripId"] == trip_id), None)
    if not trip or trip["status"] not in ["ACTIVE", "EN_ROUTE_PATIENT"]:
        active_simulation["is_running"] = False
        return

    amb = next((a for a in db.get("ambulances", []) if a["id"] == trip["ambulanceId"]), None)
    if not amb:
        return

    waypoints = active_simulation["target_waypoints"]
    idx = active_simulation["current_waypoint_index"]

    if idx >= len(waypoints) - 1:
        # Reached destination!
        await complete_trip(trip, amb)
        return

    p1 = waypoints[idx]
    p2 = waypoints[idx + 1]

    seg_distance = haversine_distance(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
    if seg_distance <= 1:
        seg_distance = 1.0

    # Calculate distance traveled in this 1-second tick (accounting for speed & multiplier)
    effective_speed_kmh = active_simulation["speed_kmh"] * active_simulation["step_multiplier"]
    speed_mps = (effective_speed_kmh * 1000.0) / 3600.0
    progress_delta = speed_mps / seg_distance

    active_simulation["segment_progress"] += progress_delta

    if active_simulation["segment_progress"] >= 1.0:
        active_simulation["segment_progress"] = 0.0
        active_simulation["current_waypoint_index"] += 1
        idx = active_simulation["current_waypoint_index"]

        if idx >= len(waypoints) - 1:
            await complete_trip(trip, amb)
            return
        p1 = waypoints[idx]
        p2 = waypoints[idx + 1]

    prog = active_simulation["segment_progress"]
    curr_lat = p1["lat"] + (p2["lat"] - p1["lat"]) * prog
    curr_lng = p1["lng"] + (p2["lng"] - p1["lng"]) * prog
    bearing = calculate_bearing(p1["lat"], p1["lng"], p2["lat"], p2["lng"])

    # Update ambulance telemetry
    amb["currentLocation"] = {"lat": curr_lat, "lng": curr_lng}
    amb["speed"] = round(effective_speed_kmh + (prog * 3.0 - 1.5), 1)
    amb["bearing"] = round(bearing, 1)

    # Check remaining distance & ETA to destination
    remaining_dist = calculate_route_remaining_distance(curr_lat, curr_lng, waypoints, idx)
    avg_speed_mps = max(speed_mps, 10.0)
    trip_eta_seconds = int(remaining_dist / avg_speed_mps)

    trip["remainingDistance"] = round(remaining_dist)
    trip["etaSeconds"] = trip_eta_seconds

    # Evaluate each intersection on the route
    await evaluate_intersections_and_clearance(trip, amb, curr_lat, curr_lng, speed_mps)

    # Broadcast location update & corridor progress
    await sio.emit("ambulance:location", {
        "tripId": trip["tripId"],
        "ambulanceId": amb["id"],
        "location": amb["currentLocation"],
        "speed": amb["speed"],
        "bearing": amb["bearing"],
        "remainingDistance": trip["remainingDistance"],
        "etaSeconds": trip["etaSeconds"],
        "currentIntersection": trip.get("currentIntersection"),
        "nextIntersection": trip.get("nextIntersection")
    })

    await sio.emit("corridor:updated", {
        "tripId": trip["tripId"],
        "intersections": db.get("intersections", []),
        "signals": db.get("trafficSignals", [])
    })

def calculate_route_remaining_distance(lat: float, lng: float, waypoints: list, curr_idx: int) -> float:
    if curr_idx >= len(waypoints) - 1:
        return 0.0
    dist = haversine_distance(lat, lng, waypoints[curr_idx + 1]["lat"], waypoints[curr_idx + 1]["lng"])
    for i in range(curr_idx + 1, len(waypoints) - 1):
        dist += haversine_distance(waypoints[i]["lat"], waypoints[i]["lng"], waypoints[i + 1]["lat"], waypoints[i + 1]["lng"])
    return dist

async def evaluate_intersections_and_clearance(trip: dict, amb: dict, curr_lat: float, curr_lng: float, speed_mps: float):
    intersections = db.get("intersections", [])
    signals = db.get("trafficSignals", [])
    settings = db.get("settings", {}).get("alertThresholds", {})

    l1_dist = settings.get("level1Distance", 2000)
    l2_dist = settings.get("level2Distance", 1000)
    l3_dist = settings.get("level3Distance", 500)
    l4_dist = settings.get("level4Distance", 250)

    # Sort upcoming intersections by distance
    upcoming = []
    for inter in intersections:
        dist = haversine_distance(curr_lat, curr_lng, inter["lat"], inter["lng"])
        eta_sec = int(dist / max(speed_mps, 1.0))
        inter["distanceToAmbulance"] = round(dist)
        inter["eta"] = eta_sec
        inter["currentAmbulanceId"] = amb["id"]
        inter["lastUpdated"] = datetime.now().isoformat()

        # Check if ambulance already passed this intersection
        status = inter.get("clearanceStatus", "NOT_ALERTED")
        if status != "AMBULANCE_PASSED" and status != "COMPLETED":
            upcoming.append((dist, inter))

    upcoming.sort(key=lambda x: x[0])

    if upcoming:
        trip["currentIntersection"] = upcoming[0][1]["id"]
        trip["nextIntersection"] = upcoming[1][1]["id"] if len(upcoming) > 1 else None
    else:
        trip["currentIntersection"] = None
        trip["nextIntersection"] = None

    for dist, inter in upcoming:
        inter_id = inter["id"]
        sig = next((s for s in signals if s["intersectionId"] == inter_id), None)
        police = next((p for p in db.get("trafficPolice", []) if p["assignedIntersection"] == inter_id), None)
        curr_status = inter.get("clearanceStatus", "NOT_ALERTED")
        eta_sec = inter["eta"]

        # Check if ambulance has reached / passed the intersection (within 30m)
        if dist <= 35:
            if curr_status != "AMBULANCE_PASSED":
                inter["clearanceStatus"] = "AMBULANCE_PASSED"
                record_clearance_event(trip["tripId"], amb["id"], inter_id, police["id"] if police else None,
                                       "AMBULANCE_PASSED", dist, eta_sec, "Ambulance safely crossed intersection.")
                if sig:
                    sig["status"] = "RESTORING"
                    sig["light"] = "YELLOW"
                    await sio.emit("signal:restored", {"signalId": sig["id"], "intersectionId": inter_id, "status": "RESTORING"})
                    asyncio.create_task(restore_signal_after_delay(sig))

                await sio.emit("ambulance:intersection-passed", {
                    "tripId": trip["tripId"],
                    "intersectionId": inter_id,
                    "name": inter["name"]
                })
            continue

        # Level 4: Final Approach (<= 250m or <= 35s)
        if dist <= l4_dist or eta_sec <= 35:
            # Check safety logic: Is road confirmed clear?
            if curr_status == "ROAD_CLEAR":
                if sig and sig["status"] != "PRIORITY_GREEN":
                    sig["status"] = "PRIORITY_GREEN"
                    sig["light"] = "GREEN"
                    record_clearance_event(trip["tripId"], amb["id"], inter_id, police["id"] if police else None,
                                           "PRIORITY_GREEN_ACTIVATED", dist, eta_sec, "Priority green active; lane physically cleared.")
                    await sio.emit("signal:priority", {
                        "signalId": sig["id"],
                        "intersectionId": inter_id,
                        "light": "GREEN",
                        "status": "PRIORITY_GREEN"
                    })
            elif curr_status in ["ALERTED", "ACKNOWLEDGED", "CLEARING", "NOT_ALERTED"]:
                # Road not yet confirmed clear!
                inter["warning"] = "CLEARANCE_NOT_CONFIRMED"
                if active_simulation.get("auto_police_response"):
                    # Auto-clearing fallback for demonstration
                    inter["clearanceStatus"] = "ROAD_CLEAR"
                    if sig:
                        sig["status"] = "PRIORITY_GREEN"
                        sig["light"] = "GREEN"
                        await sio.emit("signal:priority", {"signalId": sig["id"], "intersectionId": inter_id, "light": "GREEN", "status": "PRIORITY_GREEN"})
                        await sio.emit("clearance:confirmed", {"intersectionId": inter_id, "policeId": police["id"] if police else None})
            continue

        # Level 3: Priority Preparation (<= 500m or <= 90s)
        if dist <= l3_dist or eta_sec <= 90:
            if curr_status in ["ALERTED", "ACKNOWLEDGED", "CLEARING"]:
                if sig and sig["status"] == "NORMAL":
                    sig["status"] = "PREPARING"
                    sig["light"] = "YELLOW"
                    await sio.emit("signal:preparing", {
                        "signalId": sig["id"],
                        "intersectionId": inter_id,
                        "status": "PREPARING",
                        "eta": eta_sec
                    })
            if active_simulation.get("auto_police_response") and curr_status in ["ALERTED", "ACKNOWLEDGED", "CLEARING"]:
                # Auto-progress to ROAD_CLEAR
                inter["clearanceStatus"] = "ROAD_CLEAR"
                record_clearance_event(trip["tripId"], amb["id"], inter_id, police["id"] if police else None,
                                       "ROAD_CLEAR", dist, eta_sec, "Officer cleared lane and confirmed via terminal.")
                await sio.emit("clearance:confirmed", {
                    "intersectionId": inter_id,
                    "policeId": police["id"] if police else None,
                    "lane": inter["laneToClear"]
                })
            continue

        # Level 2: Clearance Required (<= 1000m or <= 180s)
        if dist <= l2_dist or eta_sec <= 180:
            if curr_status in ["NOT_ALERTED", "ALERTED", "ACKNOWLEDGED"]:
                inter["clearanceStatus"] = "CLEARING"
                record_clearance_event(trip["tripId"], amb["id"], inter_id, police["id"] if police else None,
                                       "CLEARANCE_STARTED", dist, eta_sec, "Traffic police active. Emergency lane cordoned.")
                await sio.emit("clearance:started", {
                    "intersectionId": inter_id,
                    "policeId": police["id"] if police else None,
                    "lane": inter["laneToClear"],
                    "eta": eta_sec,
                    "distance": dist
                })
            continue

        # Level 1: Early Alert (<= 2000m or <= 300s)
        if dist <= l1_dist or eta_sec <= 300:
            if curr_status == "NOT_ALERTED":
                inter["clearanceStatus"] = "ALERTED"
                record_clearance_event(trip["tripId"], amb["id"], inter_id, police["id"] if police else None,
                                       "POLICE_ALERTED", dist, eta_sec, "Advance alert dispatched to assigned traffic officer.")
                await sio.emit("police:alert", {
                    "level": "Level 1 — Early Alert",
                    "intersectionId": inter_id,
                    "intersectionName": inter["name"],
                    "policeId": police["id"] if police else None,
                    "ambulanceId": amb["id"],
                    "distance": dist,
                    "eta": eta_sec,
                    "direction": inter["approachDirection"],
                    "lane": inter["laneToClear"],
                    "priority": "CRITICAL"
                })
            continue

async def restore_signal_after_delay(sig: dict):
    await asyncio.sleep(4)
    sig["status"] = "NORMAL"
    sig["light"] = "RED"
    await sio.emit("signal:restored", {"signalId": sig["id"], "intersectionId": sig["intersectionId"], "status": "NORMAL"})

def record_clearance_event(trip_id: str, amb_id: str, inter_id: str, police_id: Optional[str],
                           event_type: str, distance: float, eta: int, notes: str):
    evt = {
        "eventId": f"EVT-{int(time.time() * 1000) % 1000000}",
        "tripId": trip_id,
        "ambulanceId": amb_id,
        "intersectionId": inter_id,
        "policeId": police_id,
        "eventType": event_type,
        "distance": round(distance),
        "eta": eta,
        "timestamp": datetime.now().isoformat(),
        "notes": notes
    }
    events = db.setdefault("clearanceEvents", [])
    events.append(evt)
    if len(events) > 200:
        db["clearanceEvents"] = events[-200:]
    return evt

async def complete_trip(trip: dict, amb: dict):
    active_simulation["is_running"] = False
    now = datetime.now()
    trip["status"] = "COMPLETED"
    trip["endTime"] = now.isoformat()
    start_dt = datetime.fromisoformat(trip["startTime"])
    trip["actualDuration"] = int((now - start_dt).total_seconds())
    # Calculate realistic time saved: normal congested travel time vs green corridor
    normal_travel_time = trip["estimatedDuration"]
    trip["estimatedTimeSaved"] = max(0, normal_travel_time - trip["actualDuration"])

    amb["status"] = "AVAILABLE"
    amb["speed"] = 0

    # Add to trip history
    history = db.setdefault("tripHistory", [])
    history.insert(0, trip)
    save_db()

    await sio.emit("trip:completed", {
        "tripId": trip["tripId"],
        "ambulanceId": amb["id"],
        "actualDuration": trip["actualDuration"],
        "timeSaved": trip["estimatedTimeSaved"],
        "destination": trip["destinationHospital"]
    })

# --- REST API Endpoints ---

# 1. Authentication Endpoints
@app.post("/api/auth/login")
async def login(credentials: dict = Body(...)):
    role = credentials.get("role", "admin").lower()
    user_id = credentials.get("userId")
    # Quick role-based profile return
    profiles = {
        "admin": {"id": "ADM-01", "name": "Chief Controller Sharma", "role": "admin", "title": "System Administrator"},
        "driver": {"id": user_id or "DRV-01", "name": "Rajesh Kumar", "role": "driver", "assignedAmbulance": "AMB-101"},
        "police": {"id": user_id or "POL-02", "name": "Sub-Inspector K. Ramesh", "role": "police", "assignedIntersection": "INT-02", "badge": "TP-3812"},
        "operator": {"id": "OP-01", "name": "Operator Ananya", "role": "operator", "title": "Traffic Control Room Officer"},
        "citizen": {"id": "CIT-01", "name": "Citizen / Patient User", "role": "citizen", "title": "Emergency Caller"}
    }
    user = profiles.get(role, profiles["admin"])
    return {"status": "success", "user": user, "token": f"mock-token-{role}"}

@app.get("/api/auth/me")
async def auth_me(role: str = "admin"):
    return await login({"role": role})

# 2. Trips Endpoints
@app.post("/api/trips/start")
async def start_trip(payload: dict = Body(...)):
    global sim_task
    amb_id = payload.get("ambulanceId", "AMB-101")
    hospital_id = payload.get("hospitalId", "HOSP-01")
    driver_id = payload.get("driverId", "DRV-01")
    patient_condition = payload.get("patientCondition", "Severe Emergency Trauma")
    is_sos = payload.get("isSos", False)
    patient_coords = payload.get("patientLocation", None)

    amb = next((a for a in db.get("ambulances", []) if a["id"] == amb_id), None)
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    hosp = next((h for h in db.get("hospitals", []) if h["id"] == hospital_id), None)

    # Reset any previous intersection clearance states
    for inter in db.get("intersections", []):
        inter["clearanceStatus"] = "NOT_ALERTED"
        inter["distanceToAmbulance"] = None
        inter["eta"] = None
        inter["obstructionStatus"] = "NONE"
    for sig in db.get("trafficSignals", []):
        sig["status"] = "NORMAL"
        sig["light"] = "RED"

    waypoints = list(db.get("corridorRouteWaypoints", []))

    # If SOS, prep route from current amb location to patient, then to hospital
    if is_sos and patient_coords:
        start_pt = {"lat": patient_coords["lat"], "lng": patient_coords["lng"], "name": "Patient SOS Pick-up"}
        waypoints = [start_pt] + [w for w in waypoints if "hospitalId" in w or "intersectionId" in w]

    # Calculate estimated distance
    total_dist = 0
    for i in range(len(waypoints) - 1):
        total_dist += haversine_distance(waypoints[i]["lat"], waypoints[i]["lng"], waypoints[i+1]["lat"], waypoints[i+1]["lng"])

    trip_id = f"TRIP-{int(time.time()) % 100000}"
    trip = {
        "tripId": trip_id,
        "ambulanceId": amb_id,
        "driverId": driver_id,
        "destinationHospital": hosp["name"] if hosp else "Government General Hospital",
        "hospitalId": hospital_id,
        "patientCondition": patient_condition,
        "isSos": is_sos,
        "startTime": datetime.now().isoformat(),
        "endTime": None,
        "distance": round(total_dist),
        "remainingDistance": round(total_dist),
        "estimatedDuration": int((total_dist / 6.0)), # congested city baseline ~22 km/h
        "actualDuration": None,
        "estimatedTimeSaved": 0,
        "signalsOnRoute": [s["id"] for s in db.get("trafficSignals", [])],
        "intersectionsOnRoute": [i["id"] for i in db.get("intersections", [])],
        "currentIntersection": "INT-01",
        "nextIntersection": "INT-02",
        "clearedIntersections": [],
        "prioritySignals": [],
        "status": "ACTIVE"
    }

    # Update ambulance state
    amb["status"] = "ON_TRIP"
    amb["currentLocation"] = {"lat": waypoints[0]["lat"], "lng": waypoints[0]["lng"]}
    amb["speed"] = 45.0

    trips = db.setdefault("trips", [])
    trips.append(trip)
    save_db()

    # Initialize simulation parameters
    active_simulation["is_running"] = True
    active_simulation["trip_id"] = trip_id
    active_simulation["ambulance_id"] = amb_id
    active_simulation["target_waypoints"] = waypoints
    active_simulation["current_waypoint_index"] = 0
    active_simulation["segment_progress"] = 0.0
    active_simulation["speed_kmh"] = 65.0
    active_simulation["is_rerouted"] = False

    # Start async simulation worker if not active
    if sim_task is None or sim_task.done():
        sim_task = asyncio.create_task(simulation_loop())

    await sio.emit("trip:started", trip)
    return {"status": "success", "trip": trip}

@app.post("/api/trips/{trip_id}/stop")
async def stop_trip(trip_id: str):
    trip = next((t for t in db.get("trips", []) if t["tripId"] == trip_id), None)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    amb = next((a for a in db.get("ambulances", []) if a["id"] == trip["ambulanceId"]), None)
    if amb:
        await complete_trip(trip, amb)
    return {"status": "success", "trip": trip}

@app.get("/api/trips/active")
async def get_active_trips():
    active = [t for t in db.get("trips", []) if t.get("status") in ["ACTIVE", "EN_ROUTE_PATIENT"]]
    return {"status": "success", "trips": active}

@app.get("/api/trips/history")
async def get_trip_history():
    return {"status": "success", "history": db.get("tripHistory", [])}

@app.get("/api/trips/{trip_id}")
async def get_trip(trip_id: str):
    trip = next((t for t in db.get("trips", []) if t["tripId"] == trip_id), None)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return {"status": "success", "trip": trip}

# 3. Ambulance Location & Fleet Endpoints
@app.get("/api/ambulances")
async def list_ambulances():
    return {"status": "success", "ambulances": db.get("ambulances", [])}

@app.post("/api/ambulances")
async def create_ambulance(payload: dict = Body(...)):
    new_amb = {
        "id": f"AMB-{len(db.get('ambulances', [])) + 101}",
        "registration": payload.get("registration", "AP-16-TX-0000"),
        "model": payload.get("model", "ICU Advanced Ambulance"),
        "driverId": payload.get("driverId", "DRV-01"),
        "status": "AVAILABLE",
        "currentLocation": payload.get("location", {"lat": 16.5020, "lng": 80.6480}),
        "speed": 0,
        "fuelLevel": 100,
        "equipment": payload.get("equipment", ["Oxygen", "Defibrillator", "Ventilator"]),
        "lastMaintained": datetime.now().strftime("%Y-%m-%d")
    }
    db.setdefault("ambulances", []).append(new_amb)
    save_db()
    return {"status": "success", "ambulance": new_amb}

@app.put("/api/ambulances/{amb_id}/location")
async def update_ambulance_location(amb_id: str, payload: dict = Body(...)):
    amb = next((a for a in db.get("ambulances", []) if a["id"] == amb_id), None)
    if not amb:
        raise HTTPException(status_code=404, detail="Ambulance not found")
    if "lat" in payload and "lng" in payload:
        amb["currentLocation"] = {"lat": payload["lat"], "lng": payload["lng"]}
    if "speed" in payload:
        amb["speed"] = payload["speed"]
    save_db()
    await sio.emit("ambulance:location", {"ambulanceId": amb_id, "location": amb["currentLocation"], "speed": amb["speed"]})
    return {"status": "success", "ambulance": amb}

# 4. Drivers Endpoints
@app.get("/api/drivers")
async def list_drivers():
    return {"status": "success", "drivers": db.get("drivers", [])}

@app.post("/api/drivers")
async def create_driver(payload: dict = Body(...)):
    new_driver = {
        "id": f"DRV-{len(db.get('drivers', [])) + 1:02d}",
        "name": payload.get("name"),
        "phone": payload.get("phone"),
        "email": payload.get("email"),
        "license": payload.get("license"),
        "shift": payload.get("shift", "Morning"),
        "rating": 5.0,
        "assignedAmbulance": payload.get("assignedAmbulance", "AMB-101"),
        "status": "ON_DUTY",
        "completedTrips": 0
    }
    db.setdefault("drivers", []).append(new_driver)
    save_db()
    return {"status": "success", "driver": new_driver}

# 5. Traffic Police Endpoints
@app.get("/api/traffic-police")
async def list_traffic_police():
    return {"status": "success", "police": db.get("trafficPolice", [])}

@app.post("/api/traffic-police")
async def create_police(payload: dict = Body(...)):
    new_pol = {
        "id": f"POL-{len(db.get('trafficPolice', [])) + 1:02d}",
        "name": payload.get("name"),
        "phone": payload.get("phone"),
        "email": payload.get("email"),
        "assignedIntersection": payload.get("assignedIntersection"),
        "shift": payload.get("shift", "Morning"),
        "availability": "ACTIVE",
        "badge": payload.get("badge", "TP-9999"),
        "station": payload.get("station", "Central Traffic PS")
    }
    db.setdefault("trafficPolice", []).append(new_pol)
    save_db()
    return {"status": "success", "police": new_pol}

@app.get("/api/traffic-police/{police_id}")
async def get_traffic_police(police_id: str):
    pol = next((p for p in db.get("trafficPolice", []) if p["id"] == police_id), None)
    if not pol:
        raise HTTPException(status_code=404, detail="Police officer not found")
    inter = next((i for i in db.get("intersections", []) if i["id"] == pol["assignedIntersection"]), None)
    return {"status": "success", "police": pol, "assignedIntersection": inter}

@app.put("/api/traffic-police/{police_id}")
async def update_traffic_police(police_id: str, payload: dict = Body(...)):
    pol = next((p for p in db.get("trafficPolice", []) if p["id"] == police_id), None)
    if not pol:
        raise HTTPException(status_code=404, detail="Police officer not found")
    for k, v in payload.items():
        if k in pol:
            pol[k] = v
    save_db()
    return {"status": "success", "police": pol}

# 6. Intersections Endpoints
@app.get("/api/intersections")
async def list_intersections():
    return {"status": "success", "intersections": db.get("intersections", [])}

@app.post("/api/intersections")
async def create_intersection(payload: dict = Body(...)):
    new_int = {
        "id": f"INT-{len(db.get('intersections', [])) + 1:02d}",
        "name": payload.get("name"),
        "lat": payload.get("lat"),
        "lng": payload.get("lng"),
        "roadNames": payload.get("roadNames", []),
        "signalId": payload.get("signalId"),
        "assignedPoliceId": payload.get("assignedPoliceId"),
        "laneToClear": payload.get("laneToClear", "Main Lane"),
        "approachDirection": payload.get("approachDirection", "East → West"),
        "clearanceStatus": "NOT_ALERTED",
        "obstructionStatus": "NONE"
    }
    db.setdefault("intersections", []).append(new_int)
    save_db()
    return {"status": "success", "intersection": new_int}

# 7. Traffic Signals Endpoints
@app.get("/api/signals")
async def list_traffic_signals():
    return {"status": "success", "signals": db.get("trafficSignals", [])}

@app.post("/api/signals/{sig_id}/priority")
async def set_signal_priority(sig_id: str):
    sig = next((s for s in db.get("trafficSignals", []) if s["id"] == sig_id), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    sig["status"] = "PRIORITY_GREEN"
    sig["light"] = "GREEN"
    save_db()
    await sio.emit("signal:priority", {"signalId": sig_id, "intersectionId": sig["intersectionId"], "light": "GREEN", "status": "PRIORITY_GREEN"})
    return {"status": "success", "signal": sig}

@app.post("/api/signals/{sig_id}/restore")
async def restore_signal(sig_id: str):
    sig = next((s for s in db.get("trafficSignals", []) if s["id"] == sig_id), None)
    if not sig:
        raise HTTPException(status_code=404, detail="Signal not found")
    sig["status"] = "NORMAL"
    sig["light"] = "RED"
    save_db()
    await sio.emit("signal:restored", {"signalId": sig_id, "intersectionId": sig["intersectionId"], "status": "NORMAL"})
    return {"status": "success", "signal": sig}

# 8. Hospitals Endpoints
@app.get("/api/hospitals")
async def list_hospitals():
    return {"status": "success", "hospitals": db.get("hospitals", [])}

# 9. Clearance Workflow Endpoints (Police Actions)
@app.post("/api/clearance/acknowledge")
async def acknowledge_clearance(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    trip_id = payload.get("tripId", active_simulation.get("trip_id"))

    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail="Intersection not found")

    inter["clearanceStatus"] = "ACKNOWLEDGED"
    pol = next((p for p in db.get("trafficPolice", []) if p["id"] == police_id), None)
    if pol:
        pol["lastAcknowledgedAlert"] = datetime.now().isoformat()

    record_clearance_event(trip_id, active_simulation.get("ambulance_id", "AMB-101"), inter_id, police_id,
                           "ALERT_ACKNOWLEDGED", inter.get("distanceToAmbulance", 0) or 0,
                           inter.get("eta", 0) or 0, "Officer acknowledged emergency alert on mobile console.")

    await sio.emit("police:acknowledged", {"intersectionId": inter_id, "policeId": police_id, "status": "ACKNOWLEDGED"})
    return {"status": "success", "intersection": inter}

@app.post("/api/clearance/start")
async def start_clearance(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    trip_id = payload.get("tripId", active_simulation.get("trip_id"))

    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail="Intersection not found")

    inter["clearanceStatus"] = "CLEARING"
    record_clearance_event(trip_id, active_simulation.get("ambulance_id", "AMB-101"), inter_id, police_id,
                           "CLEARANCE_STARTED", inter.get("distanceToAmbulance", 0) or 0,
                           inter.get("eta", 0) or 0, f"Clearing {inter['laneToClear']}. Vehicles diverted.")

    await sio.emit("clearance:started", {"intersectionId": inter_id, "policeId": police_id, "status": "CLEARING", "lane": inter["laneToClear"]})
    return {"status": "success", "intersection": inter}

@app.post("/api/clearance/road-clear")
async def confirm_road_clear(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    trip_id = payload.get("tripId", active_simulation.get("trip_id"))

    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail="Intersection not found")

    inter["clearanceStatus"] = "ROAD_CLEAR"
    sig = next((s for s in db.get("trafficSignals", []) if s["intersectionId"] == inter_id), None)

    # If ambulance is in range (<= 500m), trigger PRIORITY_GREEN immediately
    dist = inter.get("distanceToAmbulance") or 9999
    if dist <= 500 and sig:
        sig["status"] = "PRIORITY_GREEN"
        sig["light"] = "GREEN"
        await sio.emit("signal:priority", {"signalId": sig["id"], "intersectionId": inter_id, "light": "GREEN", "status": "PRIORITY_GREEN"})

    record_clearance_event(trip_id, active_simulation.get("ambulance_id", "AMB-101"), inter_id, police_id,
                           "ROAD_CLEAR", dist, inter.get("eta", 0) or 0, "Officer confirms road physically clear.")

    await sio.emit("clearance:confirmed", {"intersectionId": inter_id, "policeId": police_id, "status": "ROAD_CLEAR", "signalReady": True})
    return {"status": "success", "intersection": inter, "signal": sig}

@app.post("/api/clearance/obstruction")
async def report_obstruction(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    reason = payload.get("reason", "Heavy Congestion / Breakdown")
    trip_id = payload.get("tripId", active_simulation.get("trip_id"))

    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail="Intersection not found")

    inter["clearanceStatus"] = "OBSTRUCTION"
    inter["obstructionStatus"] = reason

    report = {
        "reportId": f"OBS-{int(time.time()) % 10000}",
        "intersectionId": inter_id,
        "intersectionName": inter["name"],
        "policeId": police_id,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "resolved": False,
        "alternativeRouteAvailable": True
    }
    db.setdefault("obstructionReports", []).insert(0, report)

    record_clearance_event(trip_id, active_simulation.get("ambulance_id", "AMB-101"), inter_id, police_id,
                           "OBSTRUCTION_REPORTED", inter.get("distanceToAmbulance", 0) or 0,
                           inter.get("eta", 0) or 0, f"Obstruction: {reason}")

    await sio.emit("clearance:obstruction", {
        "intersectionId": inter_id,
        "intersectionName": inter["name"],
        "reason": reason,
        "alternativeRouteAvailable": True
    })
    return {"status": "success", "report": report, "intersection": inter}

@app.post("/api/clearance/assistance")
async def request_assistance(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if inter:
        inter["clearanceStatus"] = "ASSISTANCE_REQUIRED"
    await sio.emit("clearance:assistance", {
        "intersectionId": inter_id,
        "policeId": police_id,
        "message": f"Backup assistance requested at {inter['name'] if inter else inter_id}"
    })
    return {"status": "success", "message": "Backup unit alerted"}

@app.post("/api/clearance/ambulance-passed")
async def confirm_ambulance_passed(payload: dict = Body(...)):
    inter_id = payload.get("intersectionId")
    police_id = payload.get("policeId")
    trip_id = payload.get("tripId", active_simulation.get("trip_id"))

    inter = next((i for i in db.get("intersections", []) if i["id"] == inter_id), None)
    if not inter:
        raise HTTPException(status_code=404, detail="Intersection not found")

    inter["clearanceStatus"] = "AMBULANCE_PASSED"
    sig = next((s for s in db.get("trafficSignals", []) if s["intersectionId"] == inter_id), None)
    if sig:
        sig["status"] = "RESTORING"
        sig["light"] = "YELLOW"
        asyncio.create_task(restore_signal_after_delay(sig))

    record_clearance_event(trip_id, active_simulation.get("ambulance_id", "AMB-101"), inter_id, police_id,
                           "AMBULANCE_PASSED", 0, 0, "Officer confirmed ambulance passed junction safely.")

    await sio.emit("ambulance:intersection-passed", {"intersectionId": inter_id, "tripId": trip_id})
    return {"status": "success", "intersection": inter}

@app.get("/api/clearance/events")
async def get_clearance_events():
    return {"status": "success", "events": db.get("clearanceEvents", [])}

# 10. SOS Emergency Dispatch
@app.post("/api/sos/trigger")
async def trigger_sos(payload: dict = Body(...)):
    patient_name = payload.get("patientName", "Emergency Caller")
    phone = payload.get("phone", "+91 98765 43210")
    lat = payload.get("lat", 16.4940)
    lng = payload.get("lng", 80.6580)
    address = payload.get("address", "Benz Circle Market Square")
    condition = payload.get("condition", "Critical Cardiac Arrest")

    # Pick closest available ambulance
    ambulances = [a for a in db.get("ambulances", []) if a.get("status") == "AVAILABLE"]
    chosen_amb = ambulances[0] if ambulances else db.get("ambulances", [])[0]

    # Start emergency dispatch
    trip_resp = await start_trip({
        "ambulanceId": chosen_amb["id"],
        "hospitalId": "HOSP-01",
        "driverId": chosen_amb.get("driverId", "DRV-01"),
        "patientCondition": condition,
        "isSos": True,
        "patientLocation": {"lat": lat, "lng": lng}
    })

    sos_record = {
        "sosId": f"SOS-{int(time.time()) % 10000}",
        "patientName": patient_name,
        "phone": phone,
        "location": {"lat": lat, "lng": lng, "address": address},
        "condition": condition,
        "dispatchedAmbulance": chosen_amb["id"],
        "tripId": trip_resp["trip"]["tripId"],
        "timestamp": datetime.now().isoformat()
    }

    await sio.emit("sos:dispatched", sos_record)
    return {"status": "success", "sos": sos_record, "trip": trip_resp["trip"]}

# 11. Alternative Route Application
@app.post("/api/trips/{trip_id}/apply-alternative-route")
async def apply_alternative_route(trip_id: str):
    trip = next((t for t in db.get("trips", []) if t["tripId"] == trip_id), None)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    alt_waypoints = db.get("alternativeRouteWaypoints", [])
    active_simulation["target_waypoints"] = alt_waypoints
    active_simulation["current_waypoint_index"] = 0
    active_simulation["segment_progress"] = 0.0
    active_simulation["is_rerouted"] = True

    trip["isRerouted"] = True
    trip["reroutedVia"] = "Outer Ring Road North Bypass"

    await sio.emit("trip:rerouted", {
        "tripId": trip_id,
        "newRoute": alt_waypoints,
        "message": "Emergency green corridor successfully rerouted via Bypass!"
    })
    return {"status": "success", "trip": trip, "waypoints": alt_waypoints}

# 12. Settings & Simulation Speed Endpoints
@app.get("/api/settings")
async def get_settings():
    return {"status": "success", "settings": db.get("settings", {})}

@app.post("/api/settings")
async def update_settings(payload: dict = Body(...)):
    settings = db.setdefault("settings", {})
    for k, v in payload.items():
        settings[k] = v
    if "simulationSpeed" in payload:
        active_simulation["step_multiplier"] = float(payload["simulationSpeed"])
    save_db()
    return {"status": "success", "settings": settings}

@app.post("/api/simulation/toggle-auto-police")
async def toggle_auto_police(payload: dict = Body(...)):
    active_simulation["auto_police_response"] = payload.get("autoPolice", True)
    return {"status": "success", "autoPolice": active_simulation["auto_police_response"]}

@app.post("/api/simulation/reset")
async def reset_simulation():
    active_simulation["is_running"] = False
    active_simulation["trip_id"] = None
    # Reset ambulances
    for a in db.get("ambulances", []):
        a["status"] = "AVAILABLE"
        a["speed"] = 0
    # Reset intersections
    for i in db.get("intersections", []):
        i["clearanceStatus"] = "NOT_ALERTED"
        i["distanceToAmbulance"] = None
        i["eta"] = None
        i["obstructionStatus"] = "NONE"
    for s in db.get("trafficSignals", []):
        s["status"] = "NORMAL"
        s["light"] = "RED"
    save_db()
    await sio.emit("system:reset", {})
    return {"status": "success", "message": "Simulation reset completed."}

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

# Wrap with Socket.IO ASGI app
app_asgi = socketio.ASGIApp(sio, app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app_asgi", host="127.0.0.1", port=8000, reload=False)
