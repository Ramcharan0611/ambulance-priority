# Smart Ambulance Traffic Signal Priority & Advance Clearance System

> **Web-Based Ambulance Green Corridor, Traffic Signal Priority and Traffic Police Coordination System**

A 100% software-based, intelligent emergency transit system that creates dynamic, moving green corridors by coordinating **Ambulances**, **Traffic Signals**, **Traffic Police**, **Hospitals**, and the **Traffic Control Center**.

---

## 🌟 The Core Problem & Differentiating Innovation

### The Problem
Ambulances frequently get delayed even when traffic signals turn green. Merely turning a traffic light green is ineffective when the road is physically jammed with vehicles, blocked by cross-traffic, or clogged with cars stopped past the white line that have nowhere to move.

### The Solution: Pre-Arrival Physical Traffic Clearance
This system does not wait until the ambulance arrives at the intersection. 
Instead, it calculates real-time distance and ETA along the route and alerts traffic police stationed at upcoming intersections **2 to 5 minutes before the ambulance arrives**.

Traffic police physically clear the required lane (e.g., *Eastbound Main Express Lane*), confirm **`ROAD CLEAR`**, and only then does the traffic signal transition into **`PRIORITY GREEN`**.

---

## 🚑 Key Highlight Features

### 1. Highlighted SOS Button & Live Patient Dispatch
- **Pulsating SOS Button**: Permanently highlighted on the top navigation bar and citizen view with emergency heartbeat animation.
- **Instant Dispatch**: When a citizen or patient triggers the SOS, their live GPS coordinates are acquired.
- **Two-Phase Emergency Transit**:
  1. *Phase 1*: The nearest ALS ambulance (e.g., `AMB-101`) is immediately dispatched to the patient's live location with pre-arrival traffic clearance.
  2. *Phase 2*: Once the patient is onboard, the ambulance rushes to the designated trauma hospital (`City Hospital`) via the dynamic multi-intersection green corridor.

### 2. Multi-Level Advance Traffic Police Alert System
- **Level 1 — Early Alert (2,000m / 5 min)**:
  - Status: `PREPARE`
  - Action: Officer receives advance chime and approaches assigned junction.
- **Level 2 — Clearance Required (1,000m / 3 min)**:
  - Status: `CLEARING`
  - Action: Officer physically diverts vehicles away from the ambulance lane.
- **Level 3 — Priority Preparation (500m / 90s)**:
  - Status: `URGENT CLEARANCE`
  - Action: Signal enters `PREPARING` phase; officer confirms `ROAD CLEAR`.
- **Level 4 — Final Approach & Green (200m / 30s)**:
  - Status: `PRIORITY ACTIVE`
  - Action: Signal turns `PRIORITY GREEN` only after physical clearance confirmation.
- **Intersection Passed**:
  - Status: `AMBULANCE_PASSED` -> Signal restores to normal cycle and next intersection in line escalates!

### 3. Obstruction Reporting & Dynamic Alternative Route
- Traffic police can report real-time roadblocks: Heavy Traffic, Accident, Breakdown, Road Work, or Lane Blockage.
- The Traffic Control Center is immediately notified, and can activate a simulated **Alternative Bypass Route** (via Outer Ring Road Bypass) that redirects the ambulance in real time!

### 4. Zero Hardware Dependencies
- Completely software and web-based.
- No ESP32, Arduino, Raspberry Pi, RFID, or physical sensors.
- Built-in Web Audio API emergency siren and chime synthesizer (no external audio files needed).

---

## 🖥️ Complete 23 System Views

| View # | View Name | Description |
|---|---|---|
| **1** | **Landing Page** | High-impact hero, live corridor pipeline visualizer, 8-step workflow, and quick demo launcher. |
| **2** | **Citizen SOS Emergency View** | Giant pulsating SOS button, GPS coordinate summoner, emergency triage selector, live ambulance radar tracker. |
| **3** | **Admin Dashboard** | Executive KPI cards, fleet allocation, live system health, and quick actions. |
| **4** | **Ambulance Driver Dashboard** | Cockpit HUD, digital speedometer, total ETA, next junction distance, clearance status, and signal priority readiness. |
| **5** | **Traffic Police Dashboard** | Mobile-optimized terminal, emergency alert banner, MM:SS arrival countdown, large tactile action buttons. |
| **6** | **Traffic Control Center** | Central command deck, multi-junction corridor status, obstruction warnings, manual signal overrides. |
| **7** | **Live Map** | Leaflet OpenStreetMap with custom vehicle markers, glowing signal icons, and dynamic color-coded route segments. |
| **8** | **Green Corridor Visualization** | Dynamic moving corridor pipeline with live progress propagation. |
| **9** | **Active Ambulance Trips** | Real-time telemetry cards showing speed, remaining distance, and active priority. |
| **10** | **Ambulance Management** | Fleet table, equipment checklist (Ventilator, Defibrillator, Oxygen), maintenance logs. |
| **11** | **Driver Management** | Driver registry, license verification, duty shifts, and assigned ambulances. |
| **12** | **Traffic Police Management** | Officer directory, junction post allocations, availability status. |
| **13** | **Intersection Management** | Coordinates, connected road names, lane to clear configurations, bound signal IDs. |
| **14** | **Traffic Signal Management** | Signal controllers matrix, live red/yellow/green preview, manual priority green & cycle triggers. |
| **15** | **Hospital Management** | Emergency hospital directory, ICU bed availability, trauma team contact, direct dispatch. |
| **16** | **Traffic Clearance Management** | Staged alert configuration, clearance event audit logs with timestamps and officer IDs. |
| **17** | **Obstruction Reports** | Real-time incident logs with alternative bypass route solver. |
| **18** | **Trip History** | Completed emergency runs, actual duration, and verified time saved metrics. |
| **19** | **Analytics & Reports** | Performance KPIs: Average time saved per trip, police clearance response distribution. |
| **20** | **Notifications Center** | Real-time broadcast feed for dispatch, clearance, and traffic alerts. |
| **21** | **System Settings** | Sliders for alert distance thresholds (2000m, 1000m, 500m, 250m), simulation speed, auto-fallback. |
| **22** | **Profile View** | Active role console (Admin, Driver, Police, Operator, Citizen). |
| **23** | **About Project** | Detailed academic problem statement, engineering architecture, and safety logic documentation. |

---

## 🚀 Running the System Locally

The application runs using Python 3.13 (FastAPI + Uvicorn + python-socketio):

```powershell
# Navigate to the project directory
cd C:\Users\RAMCHARAN\.gemini\antigravity-ide\scratch\smart-ambulance-corridor

# Start the server
python -m uvicorn app:app_asgi --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
👉 **`http://127.0.0.1:8000`**

### Test Scenarios to Try:
1. **SOS Emergency Summon**: Click the pulsating red **SOS EMERGENCY** button in the header or on the Citizen SOS view. Watch the ambulance dispatched in real time to the patient's coordinates!
2. **Police Terminal Interaction**: Switch to **Police Terminal** in the top navigation. Watch the arrival countdown tick down (`02:35 -> 02:34...`), click **START CLEARING**, and click **CONFIRM ROAD IS CLEAR**. Notice the signal switch to `PRIORITY GREEN`!
3. **Obstruction & Alternative Route**: Click **REPORT OBSTRUCTION** in the police terminal (or control room), select "Heavy Congestion", and click **ACTIVATE ALTERNATIVE ROUTE VIA BYPASS**. Watch the route polyline dynamically update!
4. **Driver HUD**: Switch to **Ambulance HUD** to monitor real-time vehicle speed, hospital ETA, and next junction status.
