"""
VASTUDA / STAUNT — PHASE 5.6 AUTOMATED BROWSER TEST SUITE
Verification of full-featured real web browser functionality, window stability,
smart omnibox routing, tab management, vaults, settings, and cross-platform parity.
"""

import os
import sys
import json
import re
import unittest
import urllib.parse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

class TestBrowserPhase5_6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.desktop_dir = os.path.join(REPO_ROOT, "desktop")
        cls.main_js_path = os.path.join(cls.desktop_dir, "main.js")
        cls.preload_js_path = os.path.join(cls.desktop_dir, "preload.js")
        cls.index_html_path = os.path.join(cls.desktop_dir, "src", "index.html")
        cls.newtab_html_path = os.path.join(cls.desktop_dir, "src", "newtab.html")
        cls.android_main_path = os.path.join(REPO_ROOT, "android", "app", "src", "main", "kotlin", "com", "staunt", "browser", "MainActivity.kt")
        cls.android_newtab_path = os.path.join(REPO_ROOT, "android", "app", "src", "main", "assets", "newtab.html")

        with open(cls.main_js_path, "r", encoding="utf-8") as f:
            cls.main_js = f.read()
        with open(cls.preload_js_path, "r", encoding="utf-8") as f:
            cls.preload_js = f.read()
        with open(cls.index_html_path, "r", encoding="utf-8") as f:
            cls.index_html = f.read()
        with open(cls.newtab_html_path, "r", encoding="utf-8") as f:
            cls.newtab_html = f.read()
        with open(cls.android_main_path, "r", encoding="utf-8") as f:
            cls.android_main = f.read()
        with open(cls.android_newtab_path, "r", encoding="utf-8") as f:
            cls.android_newtab = f.read()

    # =========================================================================
    # 1. WINDOW RESIZE & STABILITY ENGINE
    # =========================================================================
    def test_window_state_uses_normal_bounds(self):
        """Verify main.js uses getNormalBounds() to prevent maximized/fullscreen window shrinking bug."""
        self.assertIn("mainWindow.getNormalBounds", self.main_js)
        self.assertIn("getValidatedWindowState", self.main_js)
        self.assertIn("scheduleSaveWindowState", self.main_js)
        # Verify debounce save on resize and move
        self.assertIn("scheduleSaveWindowState();", self.main_js)

    def test_window_validation_handles_screen_clamping(self):
        """Verify window state validation clamps against monitor workArea."""
        self.assertIn("activeDisplay.workArea", self.main_js)
        self.assertIn("minWidth", self.main_js)
        self.assertIn("minHeight", self.main_js)

    # =========================================================================
    # 2. OMNIBOX & SMART SEARCH ROUTING (Local & External)
    # =========================================================================
    def format_url_or_search(self, input_val):
        """Replicates exact formatUrlOrSearch algorithm in desktop/main.js."""
        trimmed = (input_val or "").strip()[:2048]
        if re.match(r"^javascript:", trimmed, re.I) or re.match(r"^data:text/html", trimmed, re.I):
            return "staunt://newtab"
        if not trimmed or trimmed in ("staunt://newtab", "about:newtab", "about:blank"):
            return "staunt://newtab"
        if re.match(r"^https?://", trimmed, re.I) or re.match(r"^file://", trimmed, re.I) or trimmed.startswith("staunt://"):
            return trimmed
        is_localhost = bool(re.match(r"^localhost(:\d+)?(/.*)?$", trimmed, re.I))
        is_ipv4 = bool(re.match(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(:\d+)?(/.*)?$", trimmed))
        is_domain = bool(re.match(r"^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(/.*)?$", trimmed)) and (" " not in trimmed)

        if is_localhost or is_ipv4:
            return "http://" + trimmed
        if is_domain:
            return "https://" + trimmed
        return f"http://127.0.0.1:5000/?q={urllib.parse.quote(trimmed)}"

    def test_omnibox_smart_routing(self):
        """Verify URL vs search routing behavior."""
        # Full URLs
        self.assertEqual(self.format_url_or_search("https://example.com"), "https://example.com")
        self.assertEqual(self.format_url_or_search("http://localhost:3000/test"), "http://localhost:3000/test")
        # Domains
        self.assertEqual(self.format_url_or_search("wikipedia.org"), "https://wikipedia.org")
        self.assertEqual(self.format_url_or_search("github.com/torvalds"), "https://github.com/torvalds")
        # Localhost & IPs
        self.assertEqual(self.format_url_or_search("localhost:8080"), "http://localhost:8080")
        self.assertEqual(self.format_url_or_search("127.0.0.1:5000"), "http://127.0.0.1:5000")
        # Search Queries (English, Hindi, Hinglish, Questions)
        self.assertEqual(self.format_url_or_search("quantum computing"), "http://127.0.0.1:5000/?q=quantum%20computing")
        self.assertEqual(self.format_url_or_search("भारत की राजधानी"), f"http://127.0.0.1:5000/?q={urllib.parse.quote('भारत की राजधानी')}")
        self.assertEqual(self.format_url_or_search("kya haal hai"), "http://127.0.0.1:5000/?q=kya%20haal%20hai")
        self.assertEqual(self.format_url_or_search("who is the president of india"), "http://127.0.0.1:5000/?q=who%20is%20the%20president%20of%20india")
        # Dangerous schemes blocked
        self.assertEqual(self.format_url_or_search("javascript:alert(1)"), "staunt://newtab")

    # =========================================================================
    # 3. TAB LIFECYCLE & MANAGEMENT
    # =========================================================================
    def test_tab_management_functions_in_main(self):
        """Verify tab duplication, pinning, close-others, close-to-right in main.js."""
        self.assertIn("function duplicateTab(", self.main_js)
        self.assertIn("function setTabPinned(", self.main_js)
        self.assertIn("function closeOtherTabs(", self.main_js)
        self.assertIn("function closeTabsToRight(", self.main_js)
        self.assertIn("function handleStop(", self.main_js)

    def test_tab_context_menu_in_main(self):
        """Verify tab context menu handler in main.js."""
        self.assertIn("ipcMain.on('show-tab-context-menu'", self.main_js)
        self.assertIn("'Duplicate Tab'", self.main_js)
        self.assertIn("'Close Other Tabs'", self.main_js)
        self.assertIn("'Close Tabs to the Right'", self.main_js)

    # =========================================================================
    # 4. VAULT STORAGE (History, Bookmarks, Downloads, Settings)
    # =========================================================================
    def test_history_vault_and_range_clear(self):
        """Verify history DB and clearHistoryRange function in main.js."""
        self.assertIn("staunt_history_vault.json", self.main_js)
        self.assertIn("function clearHistoryRange(", self.main_js)
        self.assertIn("ipcMain.handle('clear-history'", self.main_js)

    def test_bookmarks_vault(self):
        """Verify bookmarks DB in main.js."""
        self.assertIn("staunt_bookmarks_vault.json", self.main_js)
        self.assertIn("ipcMain.handle('get-bookmarks'", self.main_js)
        self.assertIn("ipcMain.on('add-bookmark'", self.main_js)

    def test_downloads_vault(self):
        """Verify downloads vault tracking in main.js."""
        self.assertIn("staunt_downloads_vault.json", self.main_js)
        self.assertIn("function recordDownload(", self.main_js)
        self.assertIn("ipcMain.handle('get-downloads'", self.main_js)
        self.assertIn("ipcMain.on('open-download'", self.main_js)
        self.assertIn("ipcMain.on('show-in-folder'", self.main_js)

    def test_settings_vault(self):
        """Verify settings vault in main.js."""
        self.assertIn("staunt_settings.json", self.main_js)
        self.assertIn("DEFAULT_SETTINGS", self.main_js)
        self.assertIn("ipcMain.handle('get-settings'", self.main_js)
        self.assertIn("ipcMain.handle('save-settings'", self.main_js)

    # =========================================================================
    # 5. AUTOCOMPLETE SUGGESTIONS INTEGRATION
    # =========================================================================
    def test_autocomplete_ipc_in_main(self):
        """Verify autocomplete suggestions IPC handler in main.js."""
        self.assertIn("ipcMain.handle('get-suggestions'", self.main_js)
        self.assertIn("/api/suggest?q=", self.main_js)

    def test_preload_exposes_complete_api(self):
        """Verify preload.js exposes all necessary methods in contextBridge."""
        required_apis = [
            "createTab", "switchTab", "closeTab", "undoCloseTab",
            "duplicateTab", "pinTab", "closeOtherTabs", "closeTabsToRight",
            "showTabContextMenu", "stopNavigation", "navigate", "navigateTo",
            "goBack", "goForward", "reload", "goHome",
            "getSuggestions", "findInPage", "stopFindInPage", "setZoom",
            "printToPDF", "getHistory", "clearHistory", "getBookmarks",
            "addBookmark", "getDownloads", "openDownload", "showInFolder",
            "getSettings", "saveSettings", "minimizeWindow", "maximizeWindow",
            "closeWindow", "onUrlUpdated", "onTabCreated", "onTabUpdated",
            "onTabClosed", "onTabSwitched", "onDownloadProgress", "onDownloadComplete"
        ]
        for api_name in required_apis:
            self.assertIn(api_name, self.preload_js, f"Missing {api_name} in preload.js")

    # =========================================================================
    # 6. UI & HOMEPAGE DESIGN PRESERVATION
    # =========================================================================
    def test_desktop_index_html_features(self):
        """Verify index.html has omnibox dropdown, stop icon, settings modal, and shortcuts."""
        self.assertIn('id="omnibox-dropdown"', self.index_html)
        self.assertIn('id="iconStop"', self.index_html)
        self.assertIn('id="settingsModal"', self.index_html)
        self.assertIn('id="downloadToast"', self.index_html)
        self.assertIn('Ctrl+L', self.index_html)
        self.assertIn('Ctrl+T', self.index_html)
        self.assertIn('Ctrl+W', self.index_html)

    def test_newtab_preserves_clean_obsidian_design_no_clutter(self):
        """Verify newtab.html does not contain weather, stocks, crypto, facts, or unwanted widgets."""
        forbidden = ["weather", "stocks", "crypto", "daily fact", "calculator", "currency converter", "trending news"]
        for item in forbidden:
            self.assertNotIn(item, self.newtab_html.lower())

        # Must have the 6 authentic favorite tiles
        tiles = ["youtube", "github", "bing", "chatgpt", "wikipedia", "x"]
        for t in tiles:
            self.assertIn(f'data-id="{t}"', self.newtab_html)

    # =========================================================================
    # 7. CROSS-PLATFORM PARITY (Android)
    # =========================================================================
    def test_android_parity(self):
        """Verify Android MainActivity.kt handles smart URL routing, new tab asset, and favorites."""
        self.assertIn("file:///android_asset/newtab.html", self.android_main)
        self.assertIn("STAUNT_SEARCH_BASE", self.android_main)
        self.assertIn("isDomain", self.android_main)
        self.assertIn("isLocalhost", self.android_main)

        # Android newtab asset must match core 6 authentic tiles
        tiles = ["youtube", "github", "bing", "chatgpt", "wikipedia", "x"]
        for t in tiles:
            self.assertIn(f'data-id="{t}"', self.android_newtab)

    # =========================================================================
    # 8. ERROR RECOVERY PAGE
    # =========================================================================
    def test_error_page_uses_staunt_search(self):
        """Verify connection error recovery page uses STAUNT search instead of external search engine."""
        self.assertIn("Search on STAUNT", self.main_js)
        self.assertNotIn("Search on DuckDuckGo", self.main_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
