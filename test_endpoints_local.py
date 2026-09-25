import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "search-engine", "backend"))
os.environ["VERCEL"] = "1"

from server import app
from werkzeug.test import Client
from werkzeug.wrappers import Response

client = Client(app, Response)

tests = [
    ("/health", 200, lambda r: r.json and r.json.get("service") == "staunt-search-api" and r.json.get("search") is True),
    ("/api/health", 200, lambda r: r.json and r.json.get("service") == "staunt-search-api" and r.json.get("search") is True),
    ("/terms", 200, lambda r: "terms of service" in r.text.lower()),
    ("/privacy", 200, lambda r: "privacy policy" in r.text.lower()),
    ("/download/windows", 302, lambda r: "STAUNT-Windows-Setup.exe" in r.headers.get("Location", "")),
    ("/download/android", 302, lambda r: "STAUNT-Android.apk" in r.headers.get("Location", "")),
    ("/download/windows-portable", 302, lambda r: "STAUNT-Windows-Portable.zip" in r.headers.get("Location", "")),
    ("/api/releases", 200, lambda r: "STAUNT-Windows-Setup.exe" in r.text),
    ("/api/search?q=120*45", 200, lambda r: "5400" in r.text),
    ("/api/version", 200, lambda r: "version" in r.text),
]

all_passed = True
for path, expected_status, validator in tests:
    res = client.get(path)
    ok = (res.status_code == expected_status) and validator(res)
    status_str = "PASS" if ok else "FAIL"
    print(f"[{status_str}] {path} -> {res.status_code} (expected {expected_status})")
    if not ok:
        all_passed = False
        print(f"   Payload preview: {res.text[:120]}")

print("\nOVERALL RESULT:", "ALL PASSED!" if all_passed else "SOME TESTS FAILED!")
if not all_passed:
    sys.exit(1)
