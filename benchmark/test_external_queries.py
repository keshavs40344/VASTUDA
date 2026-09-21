"""
PHASE 5.8 — REAL EXTERNAL TESTS (PHASE 23)
Tests endpoints and actual queries against public endpoint.
"""
import requests
import time
import json
import os

LIVE_URL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LIVE_URL.txt")
with open(LIVE_URL_FILE, "r", encoding="utf-8") as f:
    BASE_URL = f.read().strip()

print(f"Executing Real External Tests against: {BASE_URL}")

endpoints = [
    ("/", "GET"),
    ("/health", "GET"),
    ("/api/suggest?q=python", "GET"),
    ("/api/search?q=python", "GET"),
]

print("\n--- Testing API Contract Endpoints ---")
for ep, method in endpoints:
    t0 = time.time()
    try:
        r = requests.get(BASE_URL + ep, timeout=15)
        ms = int((time.time() - t0) * 1000)
        ct = r.headers.get("Content-Type", "")[:25]
        print(f"[{r.status_code}] {ep:25} | {ms:4}ms | {ct}")
    except Exception as e:
        print(f"[ERR] {ep:25} | {e}")

queries = [
    "python",
    "India",
    "Delhi",
    "CA Foundation",
    "namaste bharat",          # Hindi query
    "aaj ka mausam kaisa hai", # Hinglish query
    "what is artificial intelligence", # Question query
    "machine learning",
    "weather today",
    "github copilot",
    "how to learn coding"
]

print("\n--- Testing Specific Queries (Phase 23) ---")
print(f"{'Query':32} | {'Status':6} | {'Results':7} | {'Provider':15} | {'Latency':8}")
print("-" * 75)

query_results = []

for q in queries:
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/search", params={"q": q}, timeout=15)
        ms = int((time.time() - t0) * 1000)
        status = r.status_code
        if status == 200:
            data = r.json()
            cnt = len(data.get("results", []))
            provider = data.get("provider", "unknown")
        else:
            cnt = 0
            provider = "error"
        print(f"{q:32} | {status:<6} | {cnt:<7} | {provider:15} | {ms:5}ms")
        query_results.append({
            "query": q,
            "status": status,
            "count": cnt,
            "provider": provider,
            "latency_ms": ms
        })
    except Exception as e:
        print(f"{q:32} | FAIL   | 0       | exception       | {e}")
        query_results.append({
            "query": q,
            "status": "FAIL",
            "count": 0,
            "provider": "exception",
            "latency_ms": 0
        })

with open("benchmark/phase5_8_external_results.json", "w", encoding="utf-8") as f:
    json.dump({"base_url": BASE_URL, "results": query_results}, f, indent=2)

print("\nResults saved to benchmark/phase5_8_external_results.json")
