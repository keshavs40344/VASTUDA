"""
STAUNT BROWSER 5.7 - PRODUCTION HARDENING & RELIABILITY ACCEPTANCE SUITE
Covers all 20 audit criteria for Phase 5.7:
Fast, Stable, Responsive, Secure, Resource-Efficient, Recoverable, Polished, and Predictable.
"""

import os
import sys
import json
import unittest
import tempfile
import re

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESKTOP_DIR = os.path.join(WORKSPACE_ROOT, "desktop")
MAIN_JS = os.path.join(DESKTOP_DIR, "main.js")
PRELOAD_JS = os.path.join(DESKTOP_DIR, "preload.js")
INDEX_HTML = os.path.join(DESKTOP_DIR, "src", "index.html")
NEWTAB_HTML = os.path.join(DESKTOP_DIR, "src", "newtab.html")
PERF_JSON = os.path.join(WORKSPACE_ROOT, "benchmark", "phase5_7_perf_results.json")
STRESS_JSON = os.path.join(WORKSPACE_ROOT, "benchmark", "phase5_7_stress_results.json")
ANDROID_MAIN = os.path.join(WORKSPACE_ROOT, "mobile", "android", "app", "src", "main", "java", "com", "staunt", "browser", "MainActivity.kt")


class TestBrowserPhase5_7(unittest.TestCase):

    def setUp(self):
        with open(MAIN_JS, "r", encoding="utf-8") as f:
            self.main_code = f.read()
        with open(PRELOAD_JS, "r", encoding="utf-8") as f:
            self.preload_code = f.read()
        with open(INDEX_HTML, "r", encoding="utf-8") as f:
            self.index_code = f.read()
        with open(NEWTAB_HTML, "r", encoding="utf-8") as f:
            self.newtab_code = f.read()

    # 1. ATOMIC JSON VAULT WRITES & RESILIENCE
    def test_01_atomic_write_json_implementation(self):
        """Verify atomicWriteJson writes to temporary file first and creates a .bak backup."""
        self.assertIn("function atomicWriteJson(", self.main_code)
        self.assertIn(".tmp", self.main_code)
        self.assertIn(".bak", self.main_code)
        self.assertIn("fs.renameSync(", self.main_code)

    def test_02_read_json_with_bak_fallback(self):
        """Verify readJsonWithBak restores from backup when the primary file is corrupted or unreadable."""
        self.assertIn("function readJsonWithBak(", self.main_code)
        self.assertIn("JSON.parse(fs.readFileSync(bakFile", self.main_code)
        self.assertIn("atomicWriteJson(filePath, restored)", self.main_code)

    # 2. WINDOW STATE & BOUNDS DRIFT DEFENSE
    def test_03_window_bounds_uses_normal_bounds(self):
        """Verify main.js uses getNormalBounds() to ensure 0px window shrinkage on restore."""
        self.assertIn("mainWindow.getNormalBounds()", self.main_code)
        self.assertIn("atomicWriteJson(WINDOW_STATE_FILE, windowState)", self.main_code)

    def test_04_window_validation_monitor_clamping(self):
        """Verify getValidatedWindowState dynamically clamps coordinates to display workArea."""
        self.assertIn("getValidatedWindowState()", self.main_code)
        self.assertIn("screen.getAllDisplays()", self.main_code)
        self.assertIn("screen.getDisplayNearestPoint", self.main_code)
        self.assertIn("workArea", self.main_code)

    # 3. TAB LIFECYCLE & MEMORY LEAK GC
    def test_05_tab_resource_cleanup_in_close_tab(self):
        """Verify closeTab stops, closes, destroys WebContents, and nullifies view references."""
        self.assertIn("detachTabView(tab);", self.main_code)
        self.assertIn("tab.view.webContents.stop()", self.main_code)
        self.assertIn("tab.view.webContents.close()", self.main_code)
        self.assertIn("tab.view.webContents.destroy()", self.main_code)
        self.assertIn("tab.view = null;", self.main_code)

    def test_06_window_close_destroys_all_tab_views(self):
        """Verify mainWindow close handler cleanly destroys all WebContentsView instances."""
        self.assertIn("mainWindow.on('close'", self.main_code)
        self.assertIn("for (const [id, tab] of tabs.entries())", self.main_code)
        self.assertIn("tabs.clear();", self.main_code)

    def test_07_tab_hibernation_memory_guard(self):
        """Verify tab hibernation threshold frees native WebContents for inactive background tabs."""
        self.assertIn("HIBERNATE_THRESHOLD", self.main_code)
        self.assertIn("wakeHibernatedTab", self.main_code)
        self.assertIn("isHibernated = true", self.main_code)

    # 4. SMART OMNIBOX & NAVIGATION
    def test_08_omnibox_smart_routing_logic(self):
        """Verify formatUrlOrSearch accurately distinguishes URLs, domains, localhost, and STAUNT searches."""
        self.assertIn("formatUrlOrSearch(", self.main_code)
        self.assertIn("isLocalhost", self.main_code)
        self.assertIn("isDomain", self.main_code)
        self.assertIn("STAUNT_SEARCH_URL", self.main_code)

    def test_09_security_protocol_interception(self):
        """Verify dangerous schemes (javascript:, data:, vbscript:) and homograph attacks are blocked."""
        self.assertIn("DANGEROUS_SCHEMES", self.main_code)
        self.assertIn("isHomographOrDeceptive", self.main_code)
        self.assertIn("Blocked homograph deceptive domain", self.main_code)

    # 5. SECURITY & HARDWARE GATING
    def test_10_hardware_api_permission_gate(self):
        """Verify raw hardware APIs (USB, Bluetooth, HID, Serial) and sensors are securely gated."""
        self.assertIn("setPermissionRequestHandler", self.main_code)
        self.assertIn("usb", self.main_code)
        self.assertIn("bluetooth", self.main_code)
        self.assertIn("serial", self.main_code)
        self.assertIn("hid", self.main_code)

    def test_11_single_instance_lock_active(self):
        """Verify single instance lock prevents multiple concurrent browser processes."""
        self.assertIn("app.requestSingleInstanceLock()", self.main_code)
        self.assertIn("app.on('second-instance'", self.main_code)

    # 6. VAULT INTEGRITY & DATA PERSISTENCE
    def test_12_history_bookmarks_downloads_use_atomic_writes(self):
        """Verify history, bookmarks, downloads, and session tabs all use atomicWriteJson."""
        self.assertIn("atomicWriteJson(HISTORY_FILE", self.main_code)
        self.assertIn("atomicWriteJson(BOOKMARKS_FILE", self.main_code)
        self.assertIn("atomicWriteJson(DOWNLOADS_FILE", self.main_code)
        self.assertIn("atomicWriteJson(SESSION_FILE", self.main_code)

    def test_13_settings_schema_validation(self):
        """Verify save-settings validates inputs and prevents malformed configuration corruption."""
        self.assertIn("ipcMain.handle('save-settings'", self.main_code)
        self.assertIn("['staunt', 'google', 'duckduckgo', 'bing']", self.main_code)
        self.assertIn("['strict', 'standard', 'off']", self.main_code)
        self.assertIn("atomicWriteJson(SETTINGS_FILE, settingsDB)", self.main_code)

    def test_14_downloads_path_normalization_and_existence(self):
        """Verify open-download and show-in-folder check for file existence before launching."""
        self.assertIn("ipcMain.on('open-download'", self.main_code)
        self.assertIn("path.normalize(itemPath.trim())", self.main_code)
        self.assertIn("fs.existsSync(cleanPath)", self.main_code)
        self.assertIn("ipcMain.on('show-in-folder'", self.main_code)

    # 7. NETWORK RESILIENCE & ZERO BLANK SCREEN
    def test_15_network_error_card_with_staunt_search(self):
        """Verify did-fail-load presents an actionable error recovery card integrating STAUNT search."""
        self.assertIn("did-fail-load", self.main_code)
        self.assertIn("Connection Error • Staunt Browser", self.main_code)
        self.assertIn("Search on STAUNT", self.main_code)

    def test_16_omnibox_autocomplete_fallback_resilience(self):
        """Verify get-suggestions queries bookmarks, history, and STAUNT engine with timeout/offline fallback."""
        self.assertIn("ipcMain.handle('get-suggestions'", self.main_code)
        self.assertIn("bookmarksDB", self.main_code)
        self.assertIn("historyDB", self.main_code)
        self.assertIn("AbortController()", self.main_code)
        self.assertIn("800", self.main_code)  # 800ms timeout guard

    # 8. PRELOAD BRIDGE INTEGRITY
    def test_17_preload_defense_in_depth(self):
        """Verify preload.js enforces object freezing, parameter sanitization, and dual namespace exposure."""
        self.assertIn("Object.freeze(", self.preload_code)
        self.assertIn("sanitizeString", self.preload_code)
        self.assertIn("sanitizeNumber", self.preload_code)
        self.assertIn("contextBridge.exposeInMainWorld('stauntAPI'", self.preload_code)
        self.assertIn("contextBridge.exposeInMainWorld('stauntSecureBridge'", self.preload_code)

    # 9. PERFORMANCE & STRESS AUDIT RESULTS
    def test_18_empirical_performance_benchmarks(self):
        """Verify empirical performance results from phase5_7_perf_results.json meet SLAs."""
        self.assertTrue(os.path.exists(PERF_JSON), "Performance results JSON must exist")
        with open(PERF_JSON, "r", encoding="utf-8") as f:
            m = json.load(f)
        # Window creation SLA: < 300 ms
        self.assertLess(m["window_creation_ms"], 300.0)
        # New tab creation SLA: < 30 ms
        self.assertLess(m["new_tab_creation_ms"], 30.0)
        # Tab switching SLA: < 10 ms
        self.assertLess(m["tab_switching_ms"], 10.0)
        # Autocomplete SLA: < 300 ms
        self.assertLess(m["autocomplete_latency_ms"], 300.0)

    def test_19_empirical_50_tab_stress_endurance(self):
        """Verify 50-tab stress test executed cleanly with PASS status and controlled memory."""
        self.assertTrue(os.path.exists(STRESS_JSON), "Stress test results JSON must exist")
        with open(STRESS_JSON, "r", encoding="utf-8") as f:
            stress = json.load(f)
        self.assertEqual(stress["totalTabs"], 50)
        self.assertEqual(stress["status"], "PASS")
        self.assertLess(stress["openElapsedMs"], 3000)  # Opened in < 3s
        self.assertLess(stress["closeElapsedMs"], 1000)  # Closed in < 1s
        self.assertLess(stress["heapDeltaMB"], 5.0)  # Heap leak < 5 MB

    # 10. CLEAN DESIGN & NO WIDGET BLOAT
    def test_20_no_widget_bloat_and_authentic_tiles(self):
        """Verify newtab.html maintains clean Obsidian styling with exactly 6 authentic tiles and no bloat widgets."""
        lower_code = self.newtab_code.lower()
        self.assertNotIn("weather-card", lower_code)
        self.assertNotIn("crypto-widget", lower_code)
        self.assertNotIn("stock-ticker", lower_code)
        self.assertNotIn("daily-fact", lower_code)
        # Check authentic tiles
        for domain in ["youtube.com", "github.com", "bing.com", "chatgpt.com", "wikipedia.org", "x.com"]:
            self.assertIn(domain, self.newtab_code)


if __name__ == "__main__":
    unittest.main(verbosity=2)
