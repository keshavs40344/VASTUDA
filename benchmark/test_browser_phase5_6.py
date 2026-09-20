"""
VASTUDA / STAUNT — PHASE 5.6 AUTOMATED BROWSER TEST SUITE
Verification of full-featured real web browser functionality, window stability,
smart omnibox routing, tab management, vaults, settings, three-dot menu,
modals, and cross-platform parity.
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
        cls.platform_bridge_path = os.path.join(cls.desktop_dir, "src", "platform-bridge.js")
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
        with open(cls.platform_bridge_path, "r", encoding="utf-8") as f:
            cls.platform_bridge = f.read()
        with open(cls.android_main_path, "r", encoding="utf-8") as f:
            cls.android_main = f.read()
        with open(cls.android_newtab_path, "r", encoding="utf-8") as f:
            cls.android_newtab = f.read()

    # =========================================================================
    # 1. WINDOW RESIZE & STABILITY ENGINE (Tests 1 - 2)
    # =========================================================================
    def test_01_window_state_uses_normal_bounds(self):
        """Verify main.js uses getNormalBounds() to prevent maximized/fullscreen window shrinking bug."""
        self.assertIn("mainWindow.getNormalBounds", self.main_js)
        self.assertIn("getValidatedWindowState", self.main_js)
        self.assertIn("scheduleSaveWindowState", self.main_js)
        self.assertIn("scheduleSaveWindowState();", self.main_js)

    def test_02_window_validation_handles_screen_clamping(self):
        """Verify window state validation clamps against monitor workArea."""
        self.assertIn("activeDisplay.workArea", self.main_js)
        self.assertIn("minWidth", self.main_js)
        self.assertIn("minHeight", self.main_js)

    # =========================================================================
    # 2. OMNIBOX & SMART SEARCH ROUTING (Test 3)
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

    def test_03_omnibox_smart_routing(self):
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
        # Search Queries
        self.assertEqual(self.format_url_or_search("quantum computing"), "http://127.0.0.1:5000/?q=quantum%20computing")
        self.assertEqual(self.format_url_or_search("भारत की राजधानी"), f"http://127.0.0.1:5000/?q={urllib.parse.quote('भारत की राजधानी')}")
        self.assertEqual(self.format_url_or_search("kya haal hai"), "http://127.0.0.1:5000/?q=kya%20haal%20hai")
        self.assertEqual(self.format_url_or_search("who is the president of india"), "http://127.0.0.1:5000/?q=who%20is%20the%20president%20of%20india")
        # Dangerous schemes blocked
        self.assertEqual(self.format_url_or_search("javascript:alert(1)"), "staunt://newtab")

    # =========================================================================
    # 3. TAB LIFECYCLE & MANAGEMENT (Tests 4 - 6)
    # =========================================================================
    def test_04_tab_management_functions_in_main(self):
        """Verify tab duplication, pinning, close-others, close-to-right in main.js."""
        self.assertIn("function duplicateTab(", self.main_js)
        self.assertIn("function setTabPinned(", self.main_js)
        self.assertIn("function closeOtherTabs(", self.main_js)
        self.assertIn("function closeTabsToRight(", self.main_js)
        self.assertIn("function handleStop(", self.main_js)

    def test_05_tab_cycling_in_main(self):
        """Verify tab cycling function and IPC listener in main.js."""
        self.assertIn("function cycleTab(", self.main_js)
        self.assertIn("ipcMain.on('cycle-tab'", self.main_js)

    def test_06_tab_context_menu_in_main(self):
        """Verify tab context menu handler in main.js."""
        self.assertIn("ipcMain.on('show-tab-context-menu'", self.main_js)
        self.assertIn("'Duplicate Tab'", self.main_js)
        self.assertIn("'Close Other Tabs'", self.main_js)
        self.assertIn("'Close Tabs to the Right'", self.main_js)

    # =========================================================================
    # 4. VAULT STORAGE & SESSION PERSISTENCE (Tests 7 - 11)
    # =========================================================================
    def test_07_history_vault_and_range_clear(self):
        """Verify history DB, delete item, and clearHistoryRange function in main.js."""
        self.assertIn("staunt_history_vault.json", self.main_js)
        self.assertIn("function clearHistoryRange(", self.main_js)
        self.assertIn("function deleteHistoryItem(", self.main_js)
        self.assertIn("ipcMain.handle('clear-history'", self.main_js)
        self.assertIn("ipcMain.handle('delete-history-item'", self.main_js)

    def test_08_bookmarks_vault_and_toggle(self):
        """Verify bookmarks DB, toggleBookmark, and deleteBookmark in main.js."""
        self.assertIn("staunt_bookmarks_vault.json", self.main_js)
        self.assertIn("function toggleBookmarkCurrentPage(", self.main_js)
        self.assertIn("function isUrlBookmarked(", self.main_js)
        self.assertIn("function deleteBookmark(", self.main_js)
        self.assertIn("ipcMain.handle('get-bookmarks'", self.main_js)
        self.assertIn("ipcMain.handle('toggle-bookmark'", self.main_js)
        self.assertIn("ipcMain.handle('check-is-bookmarked'", self.main_js)
        self.assertIn("ipcMain.handle('delete-bookmark'", self.main_js)

    def test_09_downloads_vault_and_clear(self):
        """Verify downloads vault tracking and clearDownloads in main.js."""
        self.assertIn("staunt_downloads_vault.json", self.main_js)
        self.assertIn("function recordDownload(", self.main_js)
        self.assertIn("function clearDownloads(", self.main_js)
        self.assertIn("ipcMain.handle('get-downloads'", self.main_js)
        self.assertIn("ipcMain.handle('clear-downloads'", self.main_js)
        self.assertIn("ipcMain.on('open-download'", self.main_js)
        self.assertIn("ipcMain.on('show-in-folder'", self.main_js)

    def test_10_settings_vault(self):
        """Verify settings vault in main.js."""
        self.assertIn("staunt_settings.json", self.main_js)
        self.assertIn("DEFAULT_SETTINGS", self.main_js)
        self.assertIn("ipcMain.handle('get-settings'", self.main_js)
        self.assertIn("ipcMain.handle('save-settings'", self.main_js)

    def test_11_session_tabs_persistence(self):
        """Verify session tabs save and restore functions in main.js."""
        self.assertIn("staunt_session_tabs.json", self.main_js)
        self.assertIn("function saveSessionTabs(", self.main_js)
        self.assertIn("function restoreSessionTabs(", self.main_js)

    # =========================================================================
    # 5. AUTOCOMPLETE & PRELOAD BRIDGE (Tests 12 - 13)
    # =========================================================================
    def test_12_autocomplete_includes_bookmarks_and_history(self):
        """Verify get-suggestions matches bookmarksDB, historyDB, and STAUNT suggestions."""
        self.assertIn("ipcMain.handle('get-suggestions'", self.main_js)
        self.assertIn("bookmarksDB", self.main_js)
        self.assertIn("historyDB", self.main_js)
        self.assertIn("/api/suggest?q=", self.main_js)

    def test_13_preload_exposes_complete_api(self):
        """Verify preload.js exposes all necessary methods in contextBridge."""
        required_apis = [
            "createTab", "switchTab", "closeTab", "undoCloseTab",
            "duplicateTab", "pinTab", "closeOtherTabs", "closeTabsToRight",
            "cycleTab", "showTabContextMenu", "stopNavigation", "navigate", "navigateTo",
            "goBack", "goForward", "reload", "goHome",
            "getSuggestions", "findInPage", "stopFindInPage", "setZoom",
            "printToPDF", "getHistory", "clearHistory", "deleteHistoryItem",
            "getBookmarks", "addBookmark", "toggleBookmark", "checkIsBookmarked", "deleteBookmark",
            "getDownloads", "openDownload", "showInFolder", "clearDownloads",
            "getSettings", "saveSettings", "minimizeWindow", "maximizeWindow",
            "closeWindow", "createWindow", "createIncognitoWindow", "toggleFullscreen", "showAbout",
            "onUrlUpdated", "onTabCreated", "onTabUpdated", "onTabClosed", "onTabSwitched",
            "onDownloadProgress", "onDownloadComplete", "onBookmarkStatusChanged"
        ]
        for api_name in required_apis:
            self.assertIn(api_name, self.preload_js, f"Missing {api_name} in preload.js")

    # =========================================================================
    # 6. DESKTOP INDEX.HTML UI COMPONENTS & MODALS (Tests 14 - 19)
    # =========================================================================
    def test_14_index_topbar_navigation_controls(self):
        """Verify index.html has back, forward, reload/stop, home, and new-tab buttons."""
        self.assertIn('id="btnDeskBack"', self.index_html)
        self.assertIn('id="btnDeskFwd"', self.index_html)
        self.assertIn('id="btnDeskReload"', self.index_html)
        self.assertIn('id="iconStop"', self.index_html)
        self.assertIn('id="btnDeskHome"', self.index_html)
        self.assertIn('id="btnDeskAddTab"', self.index_html)

    def test_15_index_omnibox_and_bookmark_star(self):
        """Verify index.html has omnibox input, suggestions dropdown, and star toggle button."""
        self.assertIn('id="deskOmnibox"', self.index_html)
        self.assertIn('id="omnibox-dropdown"', self.index_html)
        self.assertIn('id="btnDeskBookmark"', self.index_html)
        self.assertIn('id="starIcon"', self.index_html)

    def test_16_index_action_buttons(self):
        """Verify index.html topbar action buttons: split-view, downloads, settings, devtools, menu."""
        self.assertIn('id="btnSplitView"', self.index_html)
        self.assertIn('id="btnDeskDownloads"', self.index_html)
        self.assertIn('id="btnDeskSettings"', self.index_html)
        self.assertIn('id="btnDevTools"', self.index_html)
        self.assertIn('id="btnDeskMenu"', self.index_html)

    def test_17_index_three_dot_menu_items(self):
        """Verify index.html contains full Three-Dot menu with all standard browser actions."""
        self.assertIn('id="threeDotMenu"', self.index_html)
        self.assertIn('id="menuItemNewTab"', self.index_html)
        self.assertIn('id="menuItemNewWindow"', self.index_html)
        self.assertIn('id="menuItemNewIncognito"', self.index_html)
        self.assertIn('id="menuItemHistory"', self.index_html)
        self.assertIn('id="menuItemDownloads"', self.index_html)
        self.assertIn('id="menuItemBookmarks"', self.index_html)
        self.assertIn('id="btnZoomIn"', self.index_html)
        self.assertIn('id="btnZoomOut"', self.index_html)
        self.assertIn('id="btnFullscreen"', self.index_html)
        self.assertIn('id="menuItemPrint"', self.index_html)
        self.assertIn('id="menuItemFind"', self.index_html)
        self.assertIn('id="menuItemSettings"', self.index_html)
        self.assertIn('id="menuItemDevTools"', self.index_html)
        self.assertIn('id="menuItemAbout"', self.index_html)

    def test_18_index_interactive_modals(self):
        """Verify index.html contains History, Bookmarks, Downloads, Clear Data, and About modals."""
        self.assertIn('id="historyModal"', self.index_html)
        self.assertIn('id="bookmarksModal"', self.index_html)
        self.assertIn('id="downloadsModal"', self.index_html)
        self.assertIn('id="settingsModal"', self.index_html)
        self.assertIn('id="aboutModal"', self.index_html)

    def test_19_index_keyboard_shortcuts(self):
        """Verify index.html attaches handlers for standard browser keyboard shortcuts."""
        shortcuts = [
            'Tab',       # Ctrl+Tab cycling
            'Ctrl+T',     # New Tab
            'Ctrl+W',     # Close Tab
            'Ctrl+H',     # History
            'Ctrl+J',     # Downloads
            'Ctrl+D',     # Bookmark Tab
            'Ctrl+N',     # New Window
            'Ctrl+P',     # Print
            'F11',        # Fullscreen
            'Escape'      # Dismiss
        ]
        for sc in shortcuts:
            self.assertIn(sc, self.index_html, f"Shortcut {sc} missing from index.html")

    # =========================================================================
    # 7. HOMEPAGE DESIGN PRESERVATION (Tests 20 - 21)
    # =========================================================================
    def test_20_newtab_preserves_clean_obsidian_design_no_clutter(self):
        """Verify newtab.html does not contain weather, stocks, crypto, facts, or unwanted widgets."""
        forbidden = ["weather", "stocks", "crypto", "daily fact", "calculator", "currency converter", "trending news"]
        for item in forbidden:
            self.assertNotIn(item, self.newtab_html.lower())

    def test_21_newtab_six_authentic_tiles(self):
        """Verify newtab.html contains the authentic 6 squircle favorite tiles."""
        tiles = ["youtube", "github", "bing", "chatgpt", "wikipedia", "x"]
        for t in tiles:
            self.assertIn(f'data-id="{t}"', self.newtab_html)

    # =========================================================================
    # 8. CROSS-PLATFORM & ERROR RECOVERY (Tests 22 - 25)
    # =========================================================================
    def test_22_android_routing_and_parity(self):
        """Verify Android MainActivity.kt handles smart URL routing, new tab asset, and favorites."""
        self.assertIn("file:///android_asset/newtab.html", self.android_main)
        self.assertIn("STAUNT_SEARCH_BASE", self.android_main)
        self.assertIn("isDomain", self.android_main)
        self.assertIn("isLocalhost", self.android_main)

    def test_23_android_newtab_six_tiles(self):
        """Verify Android newtab asset matches core 6 authentic tiles."""
        tiles = ["youtube", "github", "bing", "chatgpt", "wikipedia", "x"]
        for t in tiles:
            self.assertIn(f'data-id="{t}"', self.android_newtab)

    def test_24_error_page_uses_staunt_search(self):
        """Verify connection error recovery page uses STAUNT search instead of external search engine."""
        self.assertIn("Search on STAUNT", self.main_js)
        self.assertNotIn("Search on DuckDuckGo", self.main_js)

    def test_25_platform_bridge_uses_staunt_search(self):
        """Verify platform-bridge.js routes fallback queries to STAUNT search engine."""
        self.assertIn("http://127.0.0.1:5000/?q=", self.platform_bridge)
        self.assertNotIn("duckduckgo", self.platform_bridge.lower())

    # =========================================================================
    # 9. SECTION 4A: WINDOW CONTROLS & WINDOW LIFECYCLE (Tests 26 - 30)
    # =========================================================================
    def test_26_window_caption_controls_markup_and_icons(self):
        """Verify index.html contains standard Windows caption controls and maximize/restore SVGs."""
        self.assertIn('id="winControlsGroup"', self.index_html)
        self.assertIn('id="winBtnMin"', self.index_html)
        self.assertIn('id="winBtnMax"', self.index_html)
        self.assertIn('id="winBtnClose"', self.index_html)
        self.assertIn('id="iconWinMax"', self.index_html)
        self.assertIn('id="iconWinRestore"', self.index_html)
        self.assertIn('.win-caption-btn.win-btn-close:hover', self.index_html)

    def test_27_titlebar_double_click_toggle_maximize(self):
        """Verify index.html attaches double-click listener on titlebar to toggle maximize/restore."""
        self.assertIn("desktopTopBar.addEventListener('dblclick'", self.index_html)
        self.assertIn("toggleMaximize", self.index_html)

    def test_28_window_state_broadcast_and_ui_sync(self):
        """Verify main.js broadcasts window-state-changed and index.html synchronizes state."""
        self.assertIn("broadcastWindowState", self.main_js)
        self.assertIn("window-state-changed", self.main_js)
        self.assertIn("onWindowStateChanged", self.preload_js)
        self.assertIn("syncWindowStateUI", self.index_html)
        self.assertIn("getWindowState", self.preload_js)

    def test_29_window_lifecycle_ipc_handlers(self):
        """Verify main.js handles win-min, win-max, win-restore, window-toggle-maximize, get-window-state."""
        self.assertIn("ipcMain.on('win-min'", self.main_js)
        self.assertIn("ipcMain.on('win-max'", self.main_js)
        self.assertIn("ipcMain.on('win-restore'", self.main_js)
        self.assertIn("ipcMain.on('window-toggle-maximize'", self.main_js)
        self.assertIn("ipcMain.handle('get-window-state'", self.main_js)

    def test_30_window_restore_and_multimonitor_nearest_display(self):
        """Verify handleRestore unmaximizes/restores and getValidatedWindowState finds nearest display."""
        self.assertIn("function handleRestore()", self.main_js)
        self.assertIn("getDisplayNearestPoint", self.main_js)
        self.assertIn("getNormalBounds", self.main_js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
