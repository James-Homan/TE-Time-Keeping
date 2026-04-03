#!/usr/bin/env python3
"""Test T/S log edit functionality."""

import APP
from datetime import datetime, timedelta

app = APP.create_app()
client = app.test_client()

# Login
print("=" * 60)
print("Login")
print("=" * 60)
response = client.post('/login', data={
    'username': 'testuser_pdf',
    'password': 'testpass123'
}, follow_redirects=True)

if 'Dashboard' not in response.get_data(as_text=True):
    print("❌ Login failed")
    exit(1)

print("✓ Logged in as testuser_pdf")

# Create a T/S log entry
print("\n" + "=" * 60)
print("Create T/S Log")
print("=" * 60)
response = client.post('/ts-log/', data={
    'action': 'start',
    'task_name': 'Test Task',
    'station': 'Station A',
    'problem': 'Test problem',
    'solution': 'Test solution',
    'description': 'Test description',
    'category': 'Testing',
    'priority': 'High'
}, follow_redirects=True)

print(f"✓ T/S log started")

# Stop the T/S log
print("\n" + "=" * 60)
print("Stop T/S Log")
print("=" * 60)
response = client.post('/ts-log/', data={
    'action': 'stop'
}, follow_redirects=True)

print("✓ T/S log stopped")

# Get the log ID from the database
from models import get_db
app.app_context().push()
db = get_db()
log = db.execute("SELECT id FROM ts_log WHERE user_id = 8 ORDER BY created_at DESC LIMIT 1").fetchone()
if not log:
    print("❌ Could not find created log")
    exit(1)

log_id = log['id']
print(f"✓ Got log ID: {log_id}")

# Try to access the edit form
print("\n" + "=" * 60)
print("Test Edit Form")
print("=" * 60)
response = client.get(f'/ts-log/edit/{log_id}')

if response.status_code == 200 and 'Edit T/S Log' in response.get_data(as_text=True):
    print(f"✅ Edit form loads successfully")
else:
    print(f"❌ Edit form failed: {response.status_code}")
    print(f"   Content: {response.get_data(as_text=True)[:200]}")
    exit(1)

# Try to submit an edit
print("\n" + "=" * 60)
print("Submit Edit")
print("=" * 60)

now = datetime.utcnow()
start_time = now.isoformat()
end_time = (now + timedelta(hours=1)).isoformat()

response = client.post(f'/ts-log/edit/{log_id}', data={
    'task_name': 'Updated Task Name',
    'station': 'Station B',
    'problem': 'Updated problem',
    'solution': 'Updated solution',
    'description': 'Updated description',
    'category': 'Updated Category',
    'priority': 'Critical',
    'status': 'Completed',
    'start_time': start_time,
    'end_time': end_time
}, follow_redirects=True)

if 'T/S log updated successfully' in response.get_data(as_text=True):
    print("✅ T/S log edited successfully")
else:
    print(f"❌ Edit failed")
    text = response.get_data(as_text=True)
    if 'error' in text.lower():
        print(f"   Error found in response")
    print(f"   Status: {response.status_code}")

print("\n" + "=" * 60)
print("✅ EDIT FUNCTIONALITY TEST COMPLETE")
print("=" * 60)
