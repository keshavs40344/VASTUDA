"""
VASTUDA SaaS Core - Background Worker & Scraper Daemon (Thread-Safe)
"""

import time
import os
import requests

class BackgroundWorkerDaemon:
    def __init__(self):
        self.is_running = False
        self.started_at = time.time()
        self.iteration_count = 0
        self.collected_data = []

    def start_loop(self):
        self.is_running = True
        print(f"[DAEMON] Threaded worker daemon active at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        while self.is_running:
            try:
                self.iteration_count += 1
                self.perform_scheduled_task()
                time.sleep(60) # Interval 60s
            except Exception as e:
                print(f"[DAEMON ERROR] {e}")
                time.sleep(10)

    def perform_scheduled_task(self):
        timestamp = time.strftime("%H:%M:%S")
        if self.iteration_count % 5 == 0:
            print(f"[DAEMON] Heartbeat checkpoint #{self.iteration_count} at {timestamp}")

    def execute_scrape_job(self, url: str) -> dict:
        start_t = time.time()
        try:
            resp = requests.get(url, timeout=5, headers={"User-Agent": "VASTUDA-Bot/2.0"})
            status_code = resp.status_code
            content_length = len(resp.text)
        except Exception as e:
            status_code = 0
            content_length = 0

        latency_ms = int((time.time() - start_t) * 1000)
        return {
            "target": url,
            "status_code": status_code,
            "bytes_fetched": content_length,
            "latency_ms": latency_ms,
            "harvested_at": time.time()
        }

    def get_memory_usage(self) -> str:
        try:
            import resource
            usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            return f"{usage_kb / 1024:.2f} MB"
        except Exception:
            return "Active (Normal)"

    def get_stats(self) -> dict:
        return {
            "uptime_seconds": int(time.time() - self.started_at),
            "iteration_count": self.iteration_count,
            "daemon_active": self.is_running,
            "engine": "Flask/Gunicorn Worker",
            "cloud_provider": os.environ.get("RENDER_INSTANCE_ID", "Cloud Native")
        }

    def stop(self):
        self.is_running = False
        print("[DAEMON] Worker stopped gracefully.")
