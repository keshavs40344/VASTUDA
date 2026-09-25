"""
STAUNT — Production Smoke Test Suite
Verifies all public endpoints and core features against the live production deployment.
"""
import urllib.request
import urllib.error
import json
import time
import sys

BASE_URL = "https://staunt.vercel.app"

results = []

def run_test(name, path, validate_fn, follow_redirects=True):
    url = f"{BASE_URL}{path}"
    start = time.time()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) STAUNT-SmokeTest/1.0"}
    
    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def http_error_302(self, req, fp, code, msg, headers):
            return fp
        http_error_301 = http_error_302
        http_error_307 = http_error_302

    opener = urllib.request.build_opener() if follow_redirects else urllib.request.build_opener(NoRedirectHandler)
    req = urllib.request.Request(url, headers=headers)
    
    try:
        resp = opener.open(req, timeout=12)
        elapsed_ms = int((time.time() - start) * 1000)
        status = resp.status if hasattr(resp, "status") else resp.code
        body = resp.read()
        resp_headers = resp.headers
        
        ok, detail = validate_fn(status, body, resp_headers)
        results.append({
            "name": name,
            "path": path,
            "status": status,
            "elapsed_ms": elapsed_ms,
            "ok": ok,
            "detail": detail
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name} ({path}) -> {status} in {elapsed_ms}ms: {detail}")
    except urllib.error.HTTPError as e:
        elapsed_ms = int((time.time() - start) * 1000)
        body = e.read()
        ok, detail = validate_fn(e.code, body, e.headers)
        results.append({
            "name": name,
            "path": path,
            "status": e.code,
            "elapsed_ms": elapsed_ms,
            "ok": ok,
            "detail": detail
        })
        print(f"[{'PASS' if ok else 'FAIL'}] {name} ({path}) -> {e.code} in {elapsed_ms}ms: {detail}")
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        results.append({
            "name": name,
            "path": path,
            "status": "ERR",
            "elapsed_ms": elapsed_ms,
            "ok": False,
            "detail": str(e)
        })
        print(f"[FAIL] {name} ({path}) -> Exception: {e}")

print(f"--- RUNNING STAUNT PRODUCTION SMOKE TESTS ({BASE_URL}) ---")

# 1. Health check (/health)
def val_health(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        if data.get("status") == "ok" and data.get("search") is True:
            return True, f"Service '{data.get('service')}' status ok"
        return False, f"Missing expected fields: {data}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Health Check Root", "/health", val_health)

# 2. Health check (/api/health)
run_test("Health Check API", "/api/health", val_health)

# 3. Terms of Service (/terms)
def val_terms(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    text = body.decode("utf-8", errors="ignore")
    if "Terms of Service" in text and "VASTUDA" in text and "container" in text:
        return True, f"Served genuine Terms page ({len(text)} bytes)"
    if "search-box" in text or "Search the Web" in text:
        return False, "Regressed to index.html homepage fallback"
    return False, f"Unexpected body content (length: {len(text)})"
run_test("Legal Terms of Service", "/terms", val_terms)

# 4. Privacy Policy (/privacy)
def val_privacy(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    text = body.decode("utf-8", errors="ignore")
    if "Privacy Policy" in text and "VASTUDA" in text:
        return True, f"Served genuine Privacy page ({len(text)} bytes)"
    if "search-box" in text or "Search the Web" in text:
        return False, "Regressed to index.html homepage fallback"
    return False, f"Unexpected body content (length: {len(text)})"
run_test("Legal Privacy Policy", "/privacy", val_privacy)

# 5. Download Windows (/download/windows)
def val_download_win(status, body, headers):
    loc = headers.get("Location", "")
    ct = headers.get("Content-Type", "")
    if status in (301, 302, 307, 308) and "STAUNT-Windows-Setup.exe" in loc:
        return True, f"Redirects to binary: {loc}"
    if status == 200 and ("application/octet-stream" in ct or "application/x-msdownload" in ct or len(body) > 1000000):
        return True, f"Streams binary directly (length: {len(body)})"
    return False, f"Status {status}, location: '{loc}', ct: '{ct}'"
run_test("Windows Binary Download", "/download/windows", val_download_win, follow_redirects=False)

# 6. Download Android (/download/android)
def val_download_apk(status, body, headers):
    loc = headers.get("Location", "")
    ct = headers.get("Content-Type", "")
    if status in (301, 302, 307, 308) and "STAUNT-Android.apk" in loc:
        return True, f"Redirects to binary: {loc}"
    if status == 200 and ("application/vnd.android.package-archive" in ct or "application/octet-stream" in ct or len(body) > 1000000):
        return True, f"Streams binary directly (length: {len(body)})"
    return False, f"Status {status}, location: '{loc}', ct: '{ct}'"
run_test("Android APK Download", "/download/android", val_download_apk, follow_redirects=False)

# 7. Releases API (/api/releases)
def val_releases(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        if isinstance(data, list) and len(data) >= 3:
            return True, f"Found {len(data)} releases in manifest"
        return False, f"Unexpected data format: {data}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Releases Manifest API", "/api/releases", val_releases)

# 8. Local Math Solver (/api/search?q=120*45)
def val_math(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        inst = data.get("instant_answer", {})
        if str(inst.get("result")) == "5400":
            return True, f"Instant calculation: {inst.get('expression')} = {inst.get('result')}"
        return False, f"Math result missing or incorrect: {inst}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Instant Math Query", "/api/search?q=120*45", val_math)

# 9. Real Search Query (/api/search?q=python)
def val_search(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        res = data.get("results", [])
        if len(res) >= 1:
            first = res[0]
            return True, f"Returned {len(res)} results; Top: '{first.get('title')}' ({first.get('url')})"
        return False, f"No results returned: {data}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Web Search API (python)", "/api/search?q=python", val_search)

# 10. Suggestions API (/api/suggest?q=py)
def val_suggest(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        if isinstance(data, list) and len(data) >= 1:
            return True, f"Returned {len(data)} suggestions: {data[:3]}"
        if isinstance(data, dict) and "suggestions" in data:
            return True, f"Returned {len(data['suggestions'])} suggestions: {data['suggestions'][:3]}"
        return False, f"Empty suggestions: {data}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Autocomplete Suggestions", "/api/suggest?q=py", val_suggest)

# 11. Trending API (/api/trending)
def val_trending(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        if "markets" in data or "news" in data or "topics" in data:
            return True, f"Markets: {len(data.get('markets', []))}, News: {len(data.get('news', []))}"
        return False, f"Missing trending categories: {data.keys()}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Trending API", "/api/trending", val_trending)

# 12. Weather API (/api/weather)
def val_weather(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        if "city" in data and "temp" in data:
            return True, f"City: {data.get('city')}, Temp: {data.get('temp')}"
        return False, f"Missing weather fields: {data}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Weather API", "/api/weather", val_weather)

# 13. Version API (/api/version)
def val_version(status, body, headers):
    if status != 200:
        return False, f"Expected 200, got {status}"
    try:
        data = json.loads(body)
        return True, f"Commit: {data.get('commit')}, Environment: {data.get('environment')}"
    except Exception as e:
        return False, f"Invalid JSON: {e}"
run_test("Version API", "/api/version", val_version)

print("\n--- SUMMARY OF PRODUCTION TESTS ---")
all_ok = all(r["ok"] for r in results)
passed_count = sum(1 for r in results if r["ok"])
print(f"Total: {len(results)} | Passed: {passed_count} | Failed: {len(results) - passed_count}")

if not all_ok:
    sys.exit(1)
print("ALL PRODUCTION TESTS PASSED!")
