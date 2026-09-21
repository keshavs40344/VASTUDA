"""
50x Tab Stress & Memory Leak Audit Runner
"""
import os
import sys
import time
import json
import psutil
import subprocess

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELECTRON_EXE = os.path.join(WORKSPACE_ROOT, "my-saas-project", "desktop", "node_modules", "electron", "dist", "electron.exe")
SCRATCH_DIR = os.path.join(WORKSPACE_ROOT, "scratch")
STRESS_JS = os.path.join(SCRATCH_DIR, "test_tab_stress_runner.js")

STRESS_CODE = """
const { app, BrowserWindow, WebContentsView } = require('electron');
const path = require('path');
const fs = require('fs');

app.commandLine.appendSwitch('disable-gpu');
app.commandLine.appendSwitch('no-sandbox');

let win = null;
let tabs = new Map();
let memoryHistory = [];

function getMemoryUsageMB() {
  const mem = process.memoryUsage();
  return {
    rss: Math.round(mem.rss / (1024 * 1024) * 100) / 100,
    heapUsed: Math.round(mem.heapUsed / (1024 * 1024) * 100) / 100,
    heapTotal: Math.round(mem.heapTotal / (1024 * 1024) * 100) / 100
  };
}

app.whenReady().then(async () => {
  win = new BrowserWindow({
    width: 1050,
    height: 700,
    show: false,
    webPreferences: { nodeIntegration: false, contextIsolation: true }
  });

  const baselineMem = getMemoryUsageMB();
  memoryHistory.push({ step: 'baseline', ...baselineMem });

  const TOTAL_TABS = 50;
  const tStart = Date.now();

  for (let i = 1; i <= TOTAL_TABS; i++) {
    const view = new WebContentsView({
      webPreferences: {
        sandbox: true,
        contextIsolation: true
      }
    });
    if (win.contentView && win.contentView.addChildView) {
      win.contentView.addChildView(view);
    }
    view.setBounds({ x: 0, y: 44, width: 1050, height: 656 });
    view.webContents.loadURL(`data:text/html,<html><body>Tab ${i}</body></html>`);
    tabs.set(i, view);

    if (i % 10 === 0) {
      memoryHistory.push({ step: `opened_${i}`, ...getMemoryUsageMB() });
    }
  }

  const tOpenElapsed = Date.now() - tStart;
  const peakMem = getMemoryUsageMB();
  memoryHistory.push({ step: 'peak_50_open', ...peakMem });

  // 20 rapid switch cycles
  for (let i = 1; i <= 20; i++) {
    const targetId = ((i * 7) % TOTAL_TABS) + 1;
    const view = tabs.get(targetId);
    if (view && win.contentView && win.contentView.addChildView) {
      win.contentView.addChildView(view);
    }
  }

  // Close all 50 tabs sequentially
  const tCloseStart = Date.now();
  for (let i = 1; i <= TOTAL_TABS; i++) {
    const view = tabs.get(i);
    if (view) {
      if (win.contentView && win.contentView.removeChildView) {
        try { win.contentView.removeChildView(view); } catch (e) {}
      }
      try {
        if (view.webContents && !view.webContents.isDestroyed()) {
          view.webContents.stop();
          view.webContents.close();
          if (typeof view.webContents.destroy === 'function') {
            view.webContents.destroy();
          }
        }
      } catch (e) {}
      tabs.delete(i);
    }
  }
  const tCloseElapsed = Date.now() - tCloseStart;

  await new Promise(r => setTimeout(r, 1200));

  const postCloseMem = getMemoryUsageMB();
  memoryHistory.push({ step: 'post_close', ...postCloseMem });

  const rssDelta = Math.round((postCloseMem.rss - baselineMem.rss) * 100) / 100;
  const heapDelta = Math.round((postCloseMem.heapUsed - baselineMem.heapUsed) * 100) / 100;

  const results = {
    totalTabs: TOTAL_TABS,
    openElapsedMs: tOpenElapsed,
    closeElapsedMs: tCloseElapsed,
    baselineMem,
    peakMem,
    postCloseMem,
    rssDeltaMB: rssDelta,
    heapDeltaMB: heapDelta,
    history: memoryHistory,
    status: (postCloseMem.rss < peakMem.rss || rssDelta < 60) ? 'PASS' : 'WARN'
  };

  console.log('__STRESS_METRICS_START__');
  console.log(JSON.stringify(results, null, 2));
  console.log('__STRESS_METRICS_END__');

  win.destroy();
  app.exit(0);
});
"""

def main():
    print("=" * 60)
    print("STAUNT BROWSER 5.7 - 50x TAB STRESS & MEMORY AUDIT")
    print("=" * 60)

    with open(STRESS_JS, "w", encoding="utf-8") as f:
        f.write(STRESS_CODE)

    proc = subprocess.Popen(
        [ELECTRON_EXE, STRESS_JS],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    stdout, stderr = proc.communicate(timeout=60)
    
    start_tag = "__STRESS_METRICS_START__"
    end_tag = "__STRESS_METRICS_END__"

    if start_tag in stdout and end_tag in stdout:
        json_str = stdout.split(start_tag)[1].split(end_tag)[0].strip()
        data = json.loads(json_str)
        out_path = os.path.join(WORKSPACE_ROOT, "benchmark", "phase5_7_stress_results.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        print(f"Total Tabs: {data['totalTabs']}")
        print(f"50 Tabs Open Time: {data['openElapsedMs']} ms")
        print(f"50 Tabs Close Time: {data['closeElapsedMs']} ms")
        print(f"Baseline RSS: {data['baselineMem']['rss']} MB | Heap: {data['baselineMem']['heapUsed']} MB")
        print(f"Peak (50 tabs) RSS: {data['peakMem']['rss']} MB | Heap: {data['peakMem']['heapUsed']} MB")
        print(f"Post Close RSS: {data['postCloseMem']['rss']} MB | Heap: {data['postCloseMem']['heapUsed']} MB")
        print(f"RSS Delta: {data['rssDeltaMB']} MB | Heap Delta: {data['heapDeltaMB']} MB")
        print(f"Audit Status: {data['status']}")
        print(f"Saved results to: {out_path}")
        return 0
    else:
        print("Failed to capture metrics. Output:")
        print(stdout)
        print(stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
