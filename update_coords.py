import json

data_file = "data/database.json"

with open(data_file, "r", encoding="utf-8") as f:
    db = json.load(f)

# Update Hospitals
db["hospitals"] = [
    {
        "id": "HOSP-01",
        "name": "Government General Hospital (City Hospital)",
        "shortName": "City Hospital",
        "lat": 16.5129,
        "lng": 80.6186,
        "address": "MG Road Central, Near Bus Terminal",
        "phone": "0866-2577888",
        "emergencyBeds": 16,
        "icuAvailable": 5,
        "traumaSpecialistsOnDuty": 4,
        "traumaReady": True,
        "specialties": ["Trauma & Ortho", "Cardiology", "Neurology", "Emergency Surgery"]
    },
    {
        "id": "HOSP-02",
        "name": "Apollo Emergency Trauma Institute",
        "shortName": "Apollo Trauma",
        "lat": 16.5200,
        "lng": 80.6350,
        "address": "Ring Road Sector 3",
        "phone": "0866-2489000",
        "emergencyBeds": 9,
        "icuAvailable": 3,
        "traumaSpecialistsOnDuty": 3,
        "traumaReady": True,
        "specialties": ["Cardiac ICU", "Neurosurgery", "Burn Care"]
    },
    {
        "id": "HOSP-03",
        "name": "Manipal Super Specialty Hospital",
        "shortName": "Manipal Hospital",
        "lat": 16.4910,
        "lng": 80.6320,
        "address": "Tadepalli Highway Crossing",
        "phone": "0866-2500000",
        "emergencyBeds": 12,
        "icuAvailable": 4,
        "traumaSpecialistsOnDuty": 2,
        "traumaReady": True,
        "specialties": ["Polytrauma", "Pediatric ICU", "Critical Care"]
    }
]

# Update Intersections
db["intersections"] = [
    {
        "id": "INT-01",
        "name": "Patamata Junction",
        "lat": 16.4950,
        "lng": 80.6610,
        "roadNames": ["Bandar Road", "Patamata High Street", "Pantakaluva Rd"],
        "signalId": "SIG-01",
        "assignedPoliceId": "POL-01",
        "laneToClear": "Westbound Primary Ambulance Corridor",
        "approachDirection": "East → West",
        "clearanceStatus": "NOT_ALERTED",
        "currentAmbulanceId": None,
        "distanceToAmbulance": None,
        "eta": None,
        "obstructionStatus": "NONE",
        "lastUpdated": "2026-09-25T21:00:00"
    },
    {
        "id": "INT-02",
        "name": "Benz Circle Junction",
        "lat": 16.4984,
        "lng": 80.6527,
        "roadNames": ["MG Road", "NH 16 Bypass", "Bandar Road"],
        "signalId": "SIG-02",
        "assignedPoliceId": "POL-02",
        "laneToClear": "East-West Flyover Underpass Lane",
        "approachDirection": "East → West",
        "clearanceStatus": "NOT_ALERTED",
        "currentAmbulanceId": None,
        "distanceToAmbulance": None,
        "eta": None,
        "obstructionStatus": "NONE",
        "lastUpdated": "2026-09-25T21:00:00"
    },
    {
        "id": "INT-03",
        "name": "DV Manor / Modern Cross",
        "lat": 16.5020,
        "lng": 80.6440,
        "roadNames": ["MG Road", "Pinnamaneni Poly Clinic Rd"],
        "signalId": "SIG-03",
        "assignedPoliceId": "POL-03",
        "laneToClear": "Central Express Lane (MG Road)",
        "approachDirection": "East → West",
        "clearanceStatus": "NOT_ALERTED",
        "currentAmbulanceId": None,
        "distanceToAmbulance": None,
        "eta": None,
        "obstructionStatus": "NONE",
        "lastUpdated": "2026-09-25T21:00:00"
    },
    {
        "id": "INT-04",
        "name": "Ramesh Hospital Crossing",
        "lat": 16.5065,
        "lng": 80.6350,
        "roadNames": ["MG Road", "Ring Road Concourse"],
        "signalId": "SIG-04",
        "assignedPoliceId": "POL-04",
        "laneToClear": "Inner Ambulance Priority Lane",
        "approachDirection": "East → West",
        "clearanceStatus": "NOT_ALERTED",
        "currentAmbulanceId": None,
        "distanceToAmbulance": None,
        "eta": None,
        "obstructionStatus": "NONE",
        "lastUpdated": "2026-09-25T21:00:00"
    },
    {
        "id": "INT-05",
        "name": "Governorpet Hospital Gate Junction",
        "lat": 16.5100,
        "lng": 80.6250,
        "roadNames": ["Hospital Road", "Old Bus Stand Rd", "Eluru Road"],
        "signalId": "SIG-05",
        "assignedPoliceId": "POL-05",
        "laneToClear": "Hospital Emergency Inbound Ramp",
        "approachDirection": "South-East → North-West",
        "clearanceStatus": "NOT_ALERTED",
        "currentAmbulanceId": None,
        "distanceToAmbulance": None,
        "eta": None,
        "obstructionStatus": "NONE",
        "lastUpdated": "2026-09-25T21:00:00"
    }
]

# Update Signals
for i, s in enumerate(db["trafficSignals"]):
    s["status"] = "NORMAL"
    s["light"] = "RED"

# Update Corridor Route Waypoints
db["corridorRouteWaypoints"] = [
    {"lat": 16.4930, "lng": 80.6650, "name": "Patient SOS Origin"},
    {"lat": 16.4950, "lng": 80.6610, "name": "INT-01: Patamata Junction", "intersectionId": "INT-01"},
    {"lat": 16.4965, "lng": 80.6565, "name": "Bandar Road Approach"},
    {"lat": 16.4984, "lng": 80.6527, "name": "INT-02: Benz Circle Junction", "intersectionId": "INT-02"},
    {"lat": 16.5005, "lng": 80.6480, "name": "MG Road Main Corridor"},
    {"lat": 16.5020, "lng": 80.6440, "name": "INT-03: DV Manor Cross", "intersectionId": "INT-03"},
    {"lat": 16.5042, "lng": 80.6395, "name": "Labbipet Stretch"},
    {"lat": 16.5065, "lng": 80.6350, "name": "INT-04: Ramesh Hospital Crossing", "intersectionId": "INT-04"},
    {"lat": 16.5085, "lng": 80.6295, "name": "Governorpet Approach"},
    {"lat": 16.5100, "lng": 80.6250, "name": "INT-05: Governorpet Hospital Gate", "intersectionId": "INT-05"},
    {"lat": 16.5129, "lng": 80.6186, "name": "HOSP-01: City General Hospital Emergency Gate", "hospitalId": "HOSP-01"}
]

# Update Alternative Route Waypoints
db["alternativeRouteWaypoints"] = [
    {"lat": 16.4984, "lng": 80.6527, "name": "INT-02: Benz Circle Junction"},
    {"lat": 16.5040, "lng": 80.6540, "name": "Ring Road Diversion"},
    {"lat": 16.5100, "lng": 80.6510, "name": "Outer Ring Road North"},
    {"lat": 16.5140, "lng": 80.6410, "name": "Eluru Road Concourse"},
    {"lat": 16.5130, "lng": 80.6300, "name": "Railway Terminal Road"},
    {"lat": 16.5100, "lng": 80.6250, "name": "INT-05: Governorpet Hospital Gate", "intersectionId": "INT-05"},
    {"lat": 16.5129, "lng": 80.6186, "name": "HOSP-01: City General Hospital Emergency Gate", "hospitalId": "HOSP-01"}
]

# Update Ambulances Initial Position
for a in db["ambulances"]:
    a["currentLocation"] = {"lat": 16.4930, "lng": 80.6650}
    a["speed"] = 0
    a["status"] = "AVAILABLE"

db["trips"] = []

with open(data_file, "w", encoding="utf-8") as f:
    json.dump(db, f, indent=2)

print("database.json updated with real-world Vijayawada geometry!")
