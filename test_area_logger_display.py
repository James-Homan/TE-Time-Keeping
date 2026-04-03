#!/usr/bin/env python3
"""Quick test to verify area logger displays charge codes correctly."""

import APP
from models import get_db

app = APP.create_app()
client = app.test_client()
app.app_context().push()

# Login
client.post('/signup', data={
    'new_username': 'areatest_final',
    'new_password': 'testpass123',
    'confirm_password': 'testpass123'
}, follow_redirects=True)

client.post('/login', data={
    'username': 'areatest_final',
    'password': 'testpass123'
}, follow_redirects=True)

response = client.get('/area-logger/')
html = response.get_data(as_text=True)

print("=" * 70)
print("AREA LOGGER DISPLAY CHECK")
print("=" * 70)

# Look for key patterns that show charge codes are displayed
patterns = [
    ('VIG-60011', 'First charge code'),
    ('(', 'parentheses indicating dept display'),
    ('option value=', 'select options'),
    ('Vigilance Focus Factory', 'area name'),
]

found_patterns = []
for pattern, desc in patterns:
    if pattern in html:
        print(f"✓ Found: {desc}")
        found_patterns.append(desc)
    else:
        print(f"✗ Missing: {desc}")

# Check the actual select box content
start = html.find('<select name="area_id"')
if start != -1:
    end = html.find('</select>', start)
    if end != -1:
        select_content = html[start:end+9]
        print("\n" + "=" * 70)
        print("SELECT BOX CONTENT (first 500 chars):")
        print("=" * 70)
        print(select_content[:500])

        # Count options
        option_count = select_content.count('<option')
        print(f"\nTotal options: {option_count}")
        
        if 'VIG-60011' in select_content:
            print("✅ Charge codes are displayed in select options")
        else:
            print("⚠ Charge codes may not be displayed")

print("\n" + "=" * 70)
print(f"Page length: {len(html)} chars")
print("=" * 70)
