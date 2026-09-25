"""
STAUNT — Phase 5.7: Final Render + Vercel Integration Verification Script
"""
import urllib.request
import json
import time

origin = "https://staunt.vercel.app"
render_base = "https://staunt.onrender.com"

endpoints = [
    ("/health", "Health Check", lambda d: d.get("status") == "ok" and d.get("search") is True),
    ("/api/search?q=python", "Search (python)", lambda d: len(d.get("results", [])) > 0 or d.get("destination") is not None),
    ("/api/search?q=120%2A45", "Instant Math (120*45)", lambda d: d.get("instant_answer", {}).get("result") == "5400"),
    ("/api/suggest?q=py", "Autocomplete (py)", lambda d: isinstance(d, list) and len(d) > 0 and any("py" in s.lower() for s in d)),
    ("/api/version", "Version", lambda d: "version" in d and "commit" in d),
    ("/api/trending", "Trending", lambda d: len(d.get("markets", [])) > 0 or len(d.get("news", [])) > 0),
    ("/api/weather", "Weather", lambda d: "city" in d and "temp" in d),
]

print("| Endpoint | HTTP | Latency | Valid JSON | Expected Real Data | CORS Header (`ACAO`) | Status |")
print("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")

all_pass = True
for path, label, validator in endpoints:
    url = f"{render_base}{path}"
    start = time.time()
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Origin": origin,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36 STAUNT-Audit/1.0"
            }
        )
        res = urllib.request.urlopen(req, timeout=15)
        elapsed_ms = int((time.time() - start) * 1000)
        body = res.read().decode("utf-8")
        try:
            data = json.loads(body)
            valid_json = True
        except Exception:
            valid_json = False
            data = None

        has_real_data = validator(data) if valid_json else False
        cors_acao = res.headers.get("Access-Control-Allow-Origin")
        cors_ok = (cors_acao == origin or cors_acao == "*")

        status_ok = (res.status == 200 and valid_json and has_real_data and cors_ok)
        if not status_ok:
            all_pass = False

        status_text = "PASS" if status_ok else "FAIL"
        json_str = "Yes" if valid_json else "No"
        data_str = "Yes" if has_real_data else "No"
        cors_str = cors_acao if cors_acao else "None"
        print(f"| `{path}` | `{res.status}` | `{elapsed_ms}ms` | `{json_str}` | `{data_str}` | `{cors_str}` | **{status_text}** |")
    except Exception as e:
        all_pass = False
        elapsed_ms = int((time.time() - start) * 1000)
        print(f"| `{path}` | `ERR` | `{elapsed_ms}ms` | `No` | `No` | `None` | **FAIL ({e})** |")

print()
print("INTEGRATION RESULT:", "ALL 7 ENDPOINTS PASSED PERFECTLY!" if all_pass else "SOME FAILED")
