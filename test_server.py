import requests
import json

base = 'http://127.0.0.1:8000'

# 1. Test homepage
r = requests.get(base + '/')
assert r.status_code == 200, f'Index failed: {r.status_code}'
assert 'Smart Ambulance Traffic Signal Priority' in r.text, 'Title missing in HTML'
assert 'sos-button-main' in r.text, 'SOS button missing in HTML'
print('Test 1: Index HTML loaded successfully (Status 200)')

# 2. Test CSS and JS static files
css = requests.get(base + '/static/css/style.css')
assert css.status_code == 200, 'CSS failed'
print('Test 2: style.css loaded successfully (Status 200)')

js = requests.get(base + '/static/js/app.js')
assert js.status_code == 200, 'app.js failed'
print('Test 3: app.js loaded successfully (Status 200)')

# 3. Test REST endpoints
ambs = requests.get(base + '/api/ambulances').json()
print(f'Test 4: Ambulances endpoint returned {len(ambs["ambulances"])} vehicles')

inters = requests.get(base + '/api/intersections').json()
print(f'Test 5: Intersections endpoint returned {len(inters["intersections"])} intersections ({inters["intersections"][1]["name"]})')

# 4. Test SOS Dispatch Trigger
sos_payload = {
    'patientName': 'Emergency Caller at Benz Circle',
    'phone': '+91 98480 12345',
    'lat': 16.4940,
    'lng': 80.6580,
    'address': 'Benz Circle Market Square',
    'condition': 'Acute Cardiac Arrest'
}
sos_res = requests.post(base + '/api/sos/trigger', json=sos_payload).json()
assert sos_res['status'] == 'success', 'SOS trigger failed'
trip_id = sos_res['trip']['tripId']
print(f'Test 6: SOS triggered successfully! Trip ID: {trip_id}, Dispatched Ambulance: {sos_res["sos"]["dispatchedAmbulance"]}')

# 5. Test Active Trips
active = requests.get(base + '/api/trips/active').json()
assert len(active['trips']) > 0, 'Active trips empty after SOS'
print(f'Test 7: Active trips verified ({len(active["trips"])} active trip)')

# 6. Test Traffic Police Road Clear Confirmation
clear_res = requests.post(base + '/api/clearance/road-clear', json={'intersectionId': 'INT-02', 'policeId': 'POL-02'}).json()
assert clear_res['status'] == 'success', 'Road clear failed'
print('Test 8: Road clear confirmed for Benz Circle Junction (INT-02)')

# 7. Stop Trip
stop_res = requests.post(f'{base}/api/trips/{trip_id}/stop').json()
assert stop_res['status'] == 'success', 'Stop trip failed'
print('Test 9: Trip completed and stopped cleanly')

print('\nALL 9 SERVER & API VALIDATION TESTS PASSED WITH 100% SUCCESS!')
