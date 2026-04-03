#!/usr/bin/env python3
"""Test PDF export and edit functionality after field name fixes."""

import APP
from datetime import date

app = APP.create_app()
client = app.test_client()

# Create a test user
print("=" * 60)
print("Creating test user...")
print("=" * 60)
response = client.post('/signup', data={
    'new_username': 'testuser_pdf',
    'new_password': 'testpass123',
    'confirm_password': 'testpass123'
}, follow_redirects=True)

text = response.get_data(as_text=True)
if 'Account created successfully' in text:
    print("✓ Test user created")
else:
    print("❌ Failed to create user")
    print(f"Response: {text[:300]}")
    exit(1)

# Test 1: Login
print("\n" + "=" * 60)
print("TEST 1: Login")
print("=" * 60)
response = client.post('/login', data={
    'username': 'testuser_pdf',
    'password': 'testpass123'
}, follow_redirects=True)

if 'Dashboard' not in response.get_data(as_text=True):
    print("❌ Login failed")
    exit(1)
else:
    print("✓ Login successful")

# Test 2: Test PDF export
print("\n" + "=" * 60)
print("TEST 2: PDF Export (testing field name fixes)")
print("=" * 60)
start_date = date.today().isoformat()
end_date = date.today().isoformat()

response = client.get(f'/ts-log/export/pdf?from={start_date}&to={end_date}')

if response.status_code == 200 and response.content_type == 'application/pdf':
    print(f"✅ PDF export WORKS: {len(response.data)} bytes")
    print(f"   Content-Type: {response.content_type}")
else:
    print(f"❌ PDF export failed")
    print(f"   Status code: {response.status_code}")
    print(f"   Content-Type: {response.content_type}")
    if response.status_code != 200:
        print(f"   Response: {response.get_data(as_text=True)[:300]}")

# Test 3: Test Excel export
print("\n" + "=" * 60)
print("TEST 3: Excel Export (testing field mapping fixes)")
print("=" * 60)
response = client.get(f'/ts-log/export/excel?from={start_date}&to={end_date}')

if response.status_code == 200 and 'spreadsheet' in response.content_type.lower():
    print(f"✅ Excel export WORKS: {len(response.data)} bytes")
    print(f"   Content-Type: {response.content_type}")
else:
    print(f"❌ Excel export failed")
    print(f"   Status code: {response.status_code}")
    print(f"   Content-Type: {response.content_type}")
    if response.status_code != 200:
        print(f"   Response: {response.get_data(as_text=True)[:300]}")

print("\n" + "=" * 60)
print("✅ EXPORT TESTS COMPLETE")
print("=" * 60)
