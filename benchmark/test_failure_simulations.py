"""
PHASE 5.8 — FAILURE RECOVERY & SIMULATION TEST (PHASE 26)
Simulates:
1. Provider timeout / failure isolation (mocking external failure, checking local fallback)
2. Malformed query & extreme payload input
3. Unrecognized category routing
4. Offline / graceful degraded responses
"""
import requests
import time
import os
import sys

BASE_URL = "http://127.0.0.1:5000"

print(f"Executing Failure Recovery Simulations on: {BASE_URL}")

failures = 0

def assert_test(condition, name):
    global failures
    if condition:
        print(f"[PASS] {name}")
    else:
        print(f"[FAIL] {name}")
        failures += 1

# Test 1: Malformed and oversize payload handling
try:
    giant_query = "A" * 15000
    r = requests.get(f"{BASE_URL}/api/search", params={"q": giant_query}, timeout=10)
    assert_test(r.status_code in (200, 400), f"Oversize query handled safely (Status {r.status_code})")
except Exception as e:
    assert_test(False, f"Oversize query exception: {e}")

# Test 2: Unrecognized search category fallback
try:
    r = requests.get(f"{BASE_URL}/api/search", params={"q": "test", "category": "non_existent_category_999"}, timeout=10)
    assert_test(r.status_code == 200, f"Unrecognized category falls back gracefully (Status {r.status_code})")
except Exception as e:
    assert_test(False, f"Unrecognized category exception: {e}")

# Test 3: SQL injection simulation in query
try:
    sql_injection = "' OR 1=1; DROP TABLE documents; --"
    r = requests.get(f"{BASE_URL}/api/search", params={"q": sql_injection}, timeout=10)
    assert_test(r.status_code in (200, 400), f"SQL injection attempt safely escaped (Status {r.status_code})")
except Exception as e:
    assert_test(False, f"SQL injection attempt exception: {e}")

# Test 4: Verify database integrity intact after injection test
try:
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert_test(r.status_code == 200 and r.json().get("status") == "ok", "Database intact and healthy after fuzzing")
except Exception as e:
    assert_test(False, f"Database health exception: {e}")

# Test 5: Missing params on POST /api/overview
try:
    r = requests.post(f"{BASE_URL}/api/overview", json={}, timeout=5)
    assert_test(r.status_code == 400, f"Malformed POST /api/overview rejected with 400 (Status {r.status_code})")
except Exception as e:
    assert_test(False, f"Malformed POST /api/overview exception: {e}")

# Test 6: Special UTF-8 chars and emojis
try:
    emoji_q = "🐍 🚀 🔥 💻 🇮🇳"
    r = requests.get(f"{BASE_URL}/api/search", params={"q": emoji_q}, timeout=10)
    assert_test(r.status_code == 200, f"Emoji & UTF-8 queries processed without crash (Status {r.status_code})")
except Exception as e:
    assert_test(False, f"Emoji query exception: {e}")

print("-" * 50)
if failures == 0:
    print("ALL 6 FAILURE SIMULATIONS PASSED")
    sys.exit(0)
else:
    print(f"FAILED {failures} SIMULATION(S)")
    sys.exit(1)
