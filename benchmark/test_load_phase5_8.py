"""
PHASE 5.8 — CONTROLLED LOAD TEST (PHASE 25)
Tests concurrent queries (10, 25, 50) within safe bounds.
"""
import concurrent.futures
import requests
import time
import json
import statistics
import os

LIVE_URL_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "LIVE_URL.txt")
with open(LIVE_URL_FILE, "r", encoding="utf-8") as f:
    BASE_URL = f.read().strip()

print(f"Executing Controlled Load Test against: {BASE_URL}")

TEST_QUERIES = [
    "python",
    "machine learning",
    "india news",
    "artificial intelligence",
    "delhi weather",
    "ca foundation exam",
    "javascript tutorial",
    "open source software",
    "fast algorithms",
    "data science"
]

def make_request(query):
    t0 = time.time()
    try:
        r = requests.get(f"{BASE_URL}/api/search", params={"q": query}, timeout=15)
        ms = (time.time() - t0) * 1000
        return {
            "status": r.status_code,
            "latency_ms": ms,
            "success": r.status_code == 200,
            "error": None
        }
    except Exception as e:
        ms = (time.time() - t0) * 1000
        return {
            "status": 0,
            "latency_ms": ms,
            "success": False,
            "error": str(e)
        }

concurrency_levels = [10, 25, 50]
load_summary = {}

for concurrency in concurrency_levels:
    print(f"\n--- Testing Concurrency: {concurrency} requests ---")
    queries_to_run = [TEST_QUERIES[i % len(TEST_QUERIES)] for i in range(concurrency)]
    
    t_start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(executor.map(make_request, queries_to_run))
    t_total = time.time() - t_start
    
    successful = sum(1 for r in results if r["success"])
    rate_limited = sum(1 for r in results if r["status"] == 429)
    errors = sum(1 for r in results if not r["success"] and r["status"] != 429)
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] > 0]
    
    p50 = statistics.median(latencies) if latencies else 0
    p95 = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies, default=0)
    
    print(f"Total Time:      {t_total:.2f}s")
    print(f"Successful (200): {successful}/{concurrency} ({successful/concurrency*100:.1f}%)")
    print(f"Rate-Limited:    {rate_limited}")
    print(f"Errors:          {errors}")
    print(f"Latency p50:     {p50:.1f}ms")
    print(f"Latency p95:     {p95:.1f}ms")
    
    load_summary[f"concurrency_{concurrency}"] = {
        "concurrency": concurrency,
        "total_time_s": round(t_total, 2),
        "successful": successful,
        "rate_limited": rate_limited,
        "errors": errors,
        "latency_p50_ms": round(p50, 1),
        "latency_p95_ms": round(p95, 1)
    }

with open("benchmark/phase5_8_load_results.json", "w", encoding="utf-8") as f:
    json.dump(load_summary, f, indent=2)

print("\nLoad test summary written to benchmark/phase5_8_load_results.json")
