"""
Phase 5.7 Performance Audit Suite
Empirically measures and records browser lifecycle metrics, latency, memory, and CPU usage.
"""

import os
import sys
import time
import json
import psutil
import subprocess

ELECTRON_EXE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "my-saas-project", "desktop", "node_modules", "electron", "dist", "electron.exe"
)

SCRATCH_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
os.makedirs(SCRATCH_DIR, exist_ok=True)

PERF_SCRIPT = os.path.join(SCRATCH_DIR, "perf_benchmark_runner.js")

# Runner script to measure internal operations inside Chromium / Electron
BENCHMARK_JS = """
const { app, BrowserWindow, WebContentsView } = require('electron');
const path = require('path');
const fs = require('fs');

const metrics = {};

function hrtimeMs(start) {
  const diff = process.hrtime(start);
  return (diff[0] * 1000 + diff[1] / 1e6).toFixed(2);
}

app.whenReady().then(async () => {
  const totalStart = process.hrtime();

  // 1. Measure Window Creation
  const tWinStart = process.hrtime();
  const win = new BrowserWindow({
    width: 1100,
    height: 720,
    show: false,
    frame: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'desktop', 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true
    }
  });
  metrics['window_creation_ms'] = parseFloat(hrtimeMs(tWinStart));

  // 2. Measure UI Load Time (index.html)
  const tUiStart = process.hrtime();
  await win.loadFile(path.join(__dirname, '..', 'desktop', 'src', 'index.html'));
  metrics['ui_load_ms'] = parseFloat(hrtimeMs(tUiStart));

  // 3. Measure New Tab Creation
  const tTabStart = process.hrtime();
  const view1 = new WebContentsView({
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
  });
  win.contentView.addChildView(view1);
  view1.setBounds({ x: 0, y: 44, width: 1100, height: 676 });
  metrics['new_tab_creation_ms'] = parseFloat(hrtimeMs(tTabStart));

  // 4. Measure Navigation Latency (Local STAUNT New Tab)
  const tNavStart = process.hrtime();
  await view1.webContents.loadFile(path.join(__dirname, '..', 'desktop', 'src', 'newtab.html'));
  metrics['newtab_navigation_ms'] = parseFloat(hrtimeMs(tNavStart));

  // 5. Measure Second Tab & Tab Switching Latency
  const view2 = new WebContentsView({
    webPreferences: { nodeIntegration: false, contextIsolation: true, sandbox: true }
  });
  win.contentView.addChildView(view2);
  view2.setBounds({ x: 0, y: 44, width: 1100, height: 676 });

  const tSwitchStart = process.hrtime();
  win.contentView.addChildView(view1); // Bring view1 to top
  metrics['tab_switching_ms'] = parseFloat(hrtimeMs(tSwitchStart));

  // 6. Measure History & Bookmarks Query Latency
  const historyPath = path.join(app.getPath('userData'), 'staunt_history_vault.json');
  const tHistoryStart = process.hrtime();
  try {
    if (fs.existsSync(historyPath)) JSON.parse(fs.readFileSync(historyPath, 'utf-8'));
  } catch (e) {}
  metrics['history_query_ms'] = parseFloat(hrtimeMs(tHistoryStart));

  const bookmarksPath = path.join(app.getPath('userData'), 'staunt_bookmarks_vault.json');
  const tBookmarksStart = process.hrtime();
  try {
    if (fs.existsSync(bookmarksPath)) JSON.parse(fs.readFileSync(bookmarksPath, 'utf-8'));
  } catch (e) {}
  metrics['bookmarks_query_ms'] = parseFloat(hrtimeMs(tBookmarksStart));

  // 7. Measure Settings Opening & Parsing
  const settingsPath = path.join(app.getPath('userData'), 'staunt_settings.json');
  const tSettingsStart = process.hrtime();
  try {
    if (fs.existsSync(settingsPath)) JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
  } catch (e) {}
  metrics['settings_open_ms'] = parseFloat(hrtimeMs(tSettingsStart));

  // 8. Total Startup to Interactive
  metrics['startup_to_interactive_ms'] = parseFloat(hrtimeMs(totalStart));

  // Output JSON metrics
  console.log('__PERF_METRICS_START__');
  console.log(JSON.stringify(metrics, null, 2));
  console.log('__PERF_METRICS_END__');

  win.destroy();
  app.exit(0);
});
"""


def run_performance_audit():
    print("=" * 64)
    print("  VASTUDA / STAUNT — PHASE 5.7 PERFORMANCE AUDIT")
    print("=" * 64 + "\n")

    with open(PERF_SCRIPT, "w", encoding="utf-8") as f:
        f.write(BENCHMARK_JS)

    t_start = time.perf_counter()
    proc = subprocess.Popen(
        [ELECTRON_EXE, PERF_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    # Monitor memory & CPU of the Electron process tree
    rss_mb_samples = []
    cpu_percent_samples = []

    try:
        ps_proc = psutil.Process(proc.pid)
        while proc.poll() is None:
            try:
                children = ps_proc.children(recursive=True)
                total_rss = ps_proc.memory_info().rss
                for c in children:
                    try:
                        total_rss += c.memory_info().rss
                    except Exception:
                        pass
                rss_mb_samples.append(total_rss / (1024 * 1024))
                cpu_percent_samples.append(ps_proc.cpu_percent(interval=0.05))
            except Exception:
                pass
            time.sleep(0.05)
    except Exception as e:
        pass

    stdout, stderr = proc.communicate(timeout=60)
    total_elapsed = (time.perf_counter() - t_start) * 1000

    metrics = {}
    if "__PERF_METRICS_START__" in stdout:
        raw_json = stdout.split("__PERF_METRICS_START__")[1].split("__PERF_METRICS_END__")[0].strip()
        metrics = json.loads(raw_json)

    avg_rss = sum(rss_mb_samples) / len(rss_mb_samples) if rss_mb_samples else 0.0
    peak_rss = max(rss_mb_samples) if rss_mb_samples else 0.0
    avg_cpu = sum(cpu_percent_samples) / len(cpu_percent_samples) if cpu_percent_samples else 0.0

    metrics["process_total_elapsed_ms"] = round(total_elapsed, 2)
    metrics["avg_memory_rss_mb"] = round(avg_rss, 2)
    metrics["peak_memory_rss_mb"] = round(peak_rss, 2)
    metrics["avg_cpu_percent"] = round(avg_cpu, 2)

    # Test Autocomplete & STAUNT Search Query Latency
    import urllib.request
    try:
        t_ac = time.perf_counter()
        req = urllib.request.urlopen("http://127.0.0.1:5000/api/suggest?q=mac", timeout=5)
        metrics["autocomplete_latency_ms"] = round((time.perf_counter() - t_ac) * 1000, 2)
    except Exception as e:
        metrics["autocomplete_latency_ms"] = "N/A (Server unavailable)"

    try:
        t_search = time.perf_counter()
        req = urllib.request.urlopen("http://127.0.0.1:5000/api/search?q=machine+learning", timeout=5)
        metrics["search_api_latency_ms"] = round((time.perf_counter() - t_search) * 1000, 2)
    except Exception as e:
        metrics["search_api_latency_ms"] = "N/A (Server unavailable)"

    # Print Table
    print(f"{'Metric':<36} | {'Measured Value':<20}")
    print("-" * 60)
    for k, v in metrics.items():
        unit = "ms" if "_ms" in k else ("MB" if "_mb" in k else ("%" if "_percent" in k else ""))
        formatted_key = k.replace("_", " ").title()
        print(f"{formatted_key:<36} | {v} {unit}".strip())

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "phase5_7_perf_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nSaved empirical performance measurements to: {report_path}")

    return metrics


if __name__ == "__main__":
    run_performance_audit()
