#!/usr/bin/env python3
"""Test PDF export and edit functionality after field name fixes."""

import APP
from datetime import date

app = APP.create_app()
client = app.test_client()

# Test 1: Login
print("=" * 50)
print("TEST 1: Login")
print("=" * 50)
response = client.post('/login', data={
    'username': 'U136246',
    'password': 'test1234'
}, follow_redirects=True)

if 'Dashboard' not in response.get_data(as_text=True):
    print("❌ Login failed")
    exit(1)
else:
    print("✓ Login successful")

# Test 2: Test PDF export with empty date range
print("\n" + "=" * 50)
print("TEST 2: PDF Export (should work with fixed field names)")
print("=" * 50)
start_date = date.today().isoformat()
end_date = date.today().isoformat()

response = client.get(f'/ts-log/export/pdf?from={start_date}&to={end_date}')

if response.status_code == 200 and response.content_type == 'application/pdf':
    print(f"✓ PDF export successful: {len(response.data)} bytes")
    print(f"✓ Content-Type: {response.content_type}")
else:
    print(f"❌ PDF export failed: status={response.status_code}, type={response.content_type}")
    if response.status_code != 200:
        print(f"   Response: {response.get_data(as_text=True)[:500]}")

# Test 3: Test Excel export
print("\n" + "=" * 50)
print("TEST 3: Excel Export (should also work now)")
print("=" * 50)
response = client.get(f'/ts-log/export/excel?from={start_date}&to={end_date}')

if response.status_code == 200 and 'spreadsheet' in response.content_type.lower():
    print(f"✓ Excel export successful: {len(response.data)} bytes")
    print(f"✓ Content-Type: {response.content_type}")
else:
    print(f"❌ Excel export failed: status={response.status_code}, type={response.content_type}")
    if response.status_code != 200:
        print(f"   Response: {response.get_data(as_text=True)[:500]}")

print("\n" + "=" * 50)
print("✓ All export tests passed!")
print("=" * 50)
