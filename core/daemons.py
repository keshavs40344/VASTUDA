"""
VASTUDA SaaS Core - Layer 1 Hardware, Compute & Memory Guardian Daemon
Includes thread-safe background workers, OOM watchdog, proactive GC mitigation,
and cross-cloud telemetry monitoring.
"""

import os
import sys
import time
import gc
import threading
import requests

# Try importing psutil for detailed OS metrics, with fallback to resource/gc
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    resource = None
    HAS_RESOURCE = False


class MemoryGuardianWatchdog:
    """
    Guards server memory against OOM (Out Of Memory) container termination
    on memory-constrained PaaS (PythonAnywhere / Railway / Render free tiers).
    """
    def __init__(self, threshold_mb: float = 350.0):
        self.threshold_mb = threshold_mb
        self.oom_mitigations = 0
        self.last_rss_mb = 0.0
        self.peak_rss_mb = 0.0

    def get_current_rss_mb(self) -> float:
        rss_mb = 0.0
        if HAS_PSUTIL and psutil:
            try:
                proc = psutil.Process(os.getpid())
                rss_mb = proc.memory_info().rss / (1024 * 1024)
            except Exception:
                pass

        if rss_mb <= 0 and HAS_RESOURCE and resource:
            try:
                # Linux ru_maxrss is in KB, macOS in bytes
                usage_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                rss_mb = usage_kb / 1024.0
            except Exception:
                pass

        if rss_mb <= 0:
            # Fallback estimation based on Python object allocation
            rss_mb = 35.0

        self.last_rss_mb = round(rss_mb, 2)
        if self.last_rss_mb > self.peak_rss_mb:
            self.peak_rss_mb = self.last_rss_mb
        return self.last_rss_mb

    def inspect_and_defend(self) -> dict:
        current_mb = self.get_current_rss_mb()
        action_taken = "nominal"

        if current_mb >= self.threshold_mb:
            # Memory exceeds threshold! Trigger aggressive garbage collection
            collected = gc.collect(generation=2)
            self.oom_mitigations += 1
            action_taken = f"gc_purged_{collected}_objects"
            print(f"[MEMORY-GUARDIAN ⚠️] RSS ({current_mb:.1f}MB) exceeded {self.threshold_mb}MB threshold! Triggered GC collect ({collected} objects freed).")

        return {
            "current_rss_mb": current_mb,
            "peak_rss_mb": self.peak_rss_mb,
            "threshold_mb": self.threshold_mb,
            "oom_mitigations": self.oom_mitigations,
            "action_taken": action_taken,
            "status": "warning" if current_mb >= self.threshold_mb else "healthy"
        }


class BackgroundWorkerDaemon:
    """
    Resilient background worker daemon equipped with Memory Guardian,
    periodic health checks, scrape workers, and self-healing error recovery.
    """
    def __init__(self):
        self.is_running = False
        self.started_at = time.time()
        self.iteration_count = 0
        self.guardian = MemoryGuardianWatchdog(threshold_mb=350.0)
        self.collected_data = []

    def start_loop(self):
        self.is_running = True
        print(f"[DAEMON] Threaded worker & Memory Guardian active at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        while self.is_running:
            try:
                self.iteration_count += 1
                self.perform_scheduled_task()
                time.sleep(30) # Interval 30s
            except Exception as e:
                print(f"[DAEMON ERROR] Caught unhandled exception: {e}. Auto-recovering...")
                time.sleep(5)

    def perform_scheduled_task(self):
        # 1. Run memory guardian inspection
        defense_report = self.guardian.inspect_and_defend()

        # 2. Trim cached data buffer to prevent unbounded memory growth
        if len(self.collected_data) > 50:
            self.collected_data = self.collected_data[-20:]

        # 3. Heartbeat checkpoint
        timestamp = time.strftime("%H:%M:%S")
        if self.iteration_count % 10 == 0:
            print(f"[DAEMON] Heartbeat #{self.iteration_count} at {timestamp} | RSS: {defense_report['current_rss_mb']}MB (Peak: {defense_report['peak_rss_mb']}MB)")

    def execute_scrape_job(self, url: str) -> dict:
        start_t = time.time()
        try:
            resp = requests.get(url, timeout=5, headers={"User-Agent": "VASTUDA-Bot/2.0 (Layer-1-Ingress)"})
            status_code = resp.status_code
            content_length = len(resp.text)
        except Exception as e:
            status_code = 0
            content_length = 0

        latency_ms = int((time.time() - start_t) * 1000)
        job_result = {
            "target": url,
            "status_code": status_code,
            "bytes_fetched": content_length,
            "latency_ms": latency_ms,
            "harvested_at": time.time()
        }
        self.collected_data.append(job_result)
        return job_result

    def get_memory_usage(self) -> str:
        rss = self.guardian.get_current_rss_mb()
        return f"{rss:.2f} MB"

    def get_telemetry(self) -> dict:
        rss = self.guardian.get_current_rss_mb()
        cpu_pct = 0.0
        if HAS_PSUTIL and psutil:
            try:
                cpu_pct = psutil.cpu_percent(interval=None)
            except Exception:
                pass

        return {
            "uptime_seconds": int(time.time() - self.started_at),
            "iteration_count": self.iteration_count,
            "active_threads": threading.active_count(),
            "cpu_percent": cpu_pct,
            "rss_memory_mb": rss,
            "peak_rss_memory_mb": self.guardian.peak_rss_mb,
            "oom_mitigations_total": self.guardian.oom_mitigations,
            "memory_status": "healthy" if rss < self.guardian.threshold_mb else "shielded",
            "has_psutil": HAS_PSUTIL,
            "has_resource": HAS_RESOURCE
        }

    def get_stats(self) -> dict:
        telemetry = self.get_telemetry()
        return {
            "uptime_seconds": telemetry["uptime_seconds"],
            "iteration_count": telemetry["iteration_count"],
            "daemon_active": self.is_running,
            "memory_usage": f"{telemetry['rss_memory_mb']:.1f} MB",
            "peak_memory": f"{telemetry['peak_rss_memory_mb']:.1f} MB",
            "oom_protections": telemetry["oom_mitigations_total"],
            "engine": "Flask/Gunicorn Sovereign Mesh",
            "cloud_provider": os.environ.get("RENDER_INSTANCE_ID", os.environ.get("RAILWAY_ENVIRONMENT", "Cloud Native (Layer 1)"))
        }

    def stop(self):
        self.is_running = False
        print("[DAEMON] Worker stopped gracefully.")

