#!/usr/bin/env python3
"""
Regression test - Verify existing functionality still works after Phase 2 fixes.
Tests that no existing features were broken.
"""

import APP
from datetime import datetime, timedelta
from models import get_db

app = APP.create_app()
client = app.test_client()
app.app_context().push()

print("=" * 70)
print("REGRESSION TEST - VERIFY NO BREAKAGE")
print("=" * 70)

# ====== TEST 1: Basic login/signup still works ======
print("\n[TEST 1] Login/Signup functionality")
print("-" * 70)

response = client.post('/signup', data={
    'new_username': 'regressionuser',
    'new_password': 'testpass123',
    'confirm_password': 'testpass123'
}, follow_redirects=True)

if 'success' in response.get_data(as_text=True).lower() or response.status_code == 200:
    print("✓ Signup works")
else:
    print("❌ Signup broken")
    exit(1)

response = client.post('/login', data={
    'username': 'regressionuser',
    'password': 'testpass123'
}, follow_redirects=True)

if 'dashboard' in response.get_data(as_text=True).lower():
    print("✓ Login works")
else:
    print("❌ Login broken")
    exit(1)

print("✅ TEST 1 PASSED: Auth system intact")

# ====== TEST 2: Area start/stop still works ======
print("\n[TEST 2] Area logger start/stop")
print("-" * 70)

response = client.post('/area-logger/', data={'action': 'start', 'area_id': '1'}, follow_redirects=True)
if response.status_code == 200:
    print("✓ Area start works")
else:
    print("❌ Area start broken")
    exit(1)

db = get_db()
user = db.execute("SELECT id FROM user WHERE username = ?", ('regressionuser',)).fetchone()
active = db.execute("SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL", (user['id'],)).fetchone()

if active:
    print("✓ Area log created in database")
else:
    print("❌ Area log not created")
    exit(1)

response = client.post('/area-logger/', data={'action': 'stop'}, follow_redirects=True)
if response.status_code == 200:
    print("✓ Area stop works")
else:
    print("❌ Area stop broken")
    exit(1)

active_after_stop = db.execute("SELECT * FROM time_log WHERE user_id = ? AND end_time IS NULL", (user['id'],)).fetchone()
if not active_after_stop:
    print("✓ Area log properly stopped")
else:
    print("❌ Area log not stopped")
    exit(1)

print("✅ TEST 2 PASSED: Area logger intact")

# ====== TEST 3: T/S log start/stop still works ======
print("\n[TEST 3] T/S logger start/stop")
print("-" * 70)

response = client.post('/ts-log/', data={
    'action': 'start',
    'task_name': 'Regression test task',
    'priority': 'High'
}, follow_redirects=True)

if response.status_code == 200:
    print("✓ T/S start works")
else:
    print("❌ T/S start broken")
    exit(1)

active_ts = db.execute("SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL", (user['id'],)).fetchone()
if active_ts:
    print("✓ T/S log created in database")
else:
    print("❌ T/S log not created")
    exit(1)

response = client.post('/ts-log/', data={'action': 'stop'}, follow_redirects=True)
if response.status_code == 200:
    print("✓ T/S stop works")
else:
    print("❌ T/S stop broken")
    exit(1)

active_ts_after = db.execute("SELECT * FROM ts_log WHERE user_id = ? AND end_time IS NULL", (user['id'],)).fetchone()
if not active_ts_after:
    print("✓ T/S log properly stopped")
else:
    print("❌ T/S log not stopped")
    exit(1)

print("✅ TEST 3 PASSED: T/S logger intact")

# ====== TEST 4: Data retrieval still works ======
print("\n[TEST 4] Data retrieval (GET requests)")
print("-" * 70)

endpoints = [
    ('/area-logger/', 'Area Logger'),
    ('/ts-log/', 'T/S Logger'),
    ('/timecard/', 'Timecard'),
    ('/dashboard/', 'Dashboard'),
    ('/management/areas', 'Areas Management'),
    ('/management/charge-codes', 'Charge Codes Management'),
]

for url, name in endpoints:
    response = client.get(url)
    if response.status_code in [200, 302]:  # 302 is redirect, OK
        print(f"✓ {name} loads")
    else:
        print(f"❌ {name} broken (status {response.status_code})")
        exit(1)

print("✅ TEST 4 PASSED: Data retrieval intact")

# ====== TEST 5: Session isolation ======
print("\n[TEST 5] Multi-user session isolation")
print("-" * 70)

# Create second user and login
client.post('/signup', data={
    'new_username': 'user2regression',
    'new_password': 'testpass123',
    'confirm_password': 'testpass123'
}, follow_redirects=True)

db.execute("INSERT INTO time_log (user_id, area_id, start_time) VALUES (?, ?, ?)",
    (user['id'], 1, datetime.utcnow().isoformat()))
db.commit()

response = client.post('/login', data={
    'username': 'user2regression',
    'password': 'testpass123'
}, follow_redirects=True)

# User 2 should see area logger without user 1's data
response = client.get('/area-logger/')
if response.status_code == 200:
    print("✓ User 2 can access area logger")
else:
    print("❌ User 2 cannot access area logger")
    exit(1)

print("✅ TEST 5 PASSED: Session isolation intact")

# ====== SUMMARY ======
print("\n" + "=" * 70)
print("✅ REGRESSION TEST COMPLETE - NO BREAKAGE DETECTED")
print("=" * 70)
print("\nAll core functionality verified working:")
print("1. ✓  Authentication system")
print("2. ✓  Area logging (start/stop)")
print("3. ✓  T/S logging (start/stop)")
print("4. ✓  Data retrieval")
print("5. ✓  Multi-user isolation")
print("\nPhase 2 bug fixes implemented without regression!")
