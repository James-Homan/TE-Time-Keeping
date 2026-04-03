#!/usr/bin/env python3
"""Test PDF and Excel export functionality after all fixes."""

import APP
from datetime import date

app = APP.create_app()
client = app.test_client()

# Test 1: Login
print("=" * 60)
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
print("TEST 2: PDF Export (fixed field names)")
print("=" * 60)
start_date = date.today().isoformat()
end_date = date.today().isoformat()

response = client.get(f'/ts-log/export/pdf?from={start_date}&to={end_date}')

if response.status_code == 200 and response.content_type == 'application/pdf':
    print(f"✅ PDF export WORKS: {len(response.data)} bytes")
    print(f"   Content-Type: {response.content_type}")
else:
    print(f"❌ PDF export failed: {response.status_code}, {response.content_type}")

# Test 3: Test Excel export
print("\n" + "=" * 60)
print("TEST 3: Excel Export (fixed field names and sheet title)")
print("=" * 60)
response = client.get(f'/ts-log/export/excel?from={start_date}&to={end_date}')

if response.status_code == 200 and 'spreadsheet' in response.content_type.lower():
    print(f"✅ Excel export WORKS: {len(response.data)} bytes")
    print(f"   Content-Type: {response.content_type}")
else:
    print(f"❌ Excel export failed: {response.status_code}")
    print(f"   Content-Type: {response.content_type}")

print("\n" + "=" * 60)
print("✅ EXPORT TESTS COMPLETE")
print("=" * 60)
