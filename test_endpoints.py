import requests
import time

BASE_URL = "http://127.0.0.1:5000"
time.sleep(2)  # Wait for server to fully start

print("=" * 60)
print("VALIDATION TEST SUITE")
print("=" * 60)

# Test 1: GET /
print("\n[TEST 1] GET / (Home page)")
try:
    r = requests.get(BASE_URL + "/", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        print(f"✓ No 500 error on home")
    else:
        print(f"✗ Status: {r.status_code}")
        print(f"Response: {r.text[:200]}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 2: GET /timecard (Timecard page with graph)
print("\n[TEST 2] GET /timecard (Timecard with graph)")
try:
    r = requests.get(BASE_URL + "/timecard", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        if "timecard" in r.text.lower() or "chart" in r.text.lower():
            print(f"✓ Timecard page loaded")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 3: GET /timecard-data (Graph data endpoint)
print("\n[TEST 3] GET /timecard-data (Graph JSON data)")
try:
    r = requests.get(BASE_URL + "/timecard-data", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        data = r.json()
        print(f"✓ JSON response: {list(data.keys())}")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 4: GET /area-logger (Area logger page)
print("\n[TEST 4] GET /area-logger (Area logger page)")
try:
    r = requests.get(BASE_URL + "/area-logger", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        print(f"✓ Area logger loaded")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 5: GET /ts-log (TS Log page)
print("\n[TEST 5] GET /ts-log (TS Log page)")
try:
    r = requests.get(BASE_URL + "/ts-log", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        print(f"✓ TS Log page loaded")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 6: GET /charge-codes (Charge codes page)
print("\n[TEST 6] GET /charge-codes (Charge codes list)")
try:
    r = requests.get(BASE_URL + "/charge-codes", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        print(f"✓ Charge codes page loaded")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")

# Test 7: GET /areas (Areas page)
print("\n[TEST 7] GET /areas (Areas list)")
try:
    r = requests.get(BASE_URL + "/areas", timeout=5)
    if r.status_code == 200:
        print(f"✓ Status: {r.status_code}")
        print(f"✓ Areas page loaded")
    else:
        print(f"✗ Status: {r.status_code}")
except Exception as e:
    print(f"✗ Error: {e}")


print("\n" + "=" * 60)
print("VALIDATION COMPLETE")
print("=" * 60)
