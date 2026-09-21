# PHASE 5.7 FEATURE INVENTORY & AUDIT MANIFEST

| Feature | Current Behavior | Status | Performance Issue | Reliability Issue | Security Issue | UX Issue | Action |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **Window State Persistence** | Saves dimensions to `window-state.json` using `getNormalBounds()` | PASS | None (debounced save) | Risk of corruption on power cutoff | None | None | **HARDEN** (Atomic write via temp file) |
| **Window Controls (Min/Max/Restore/Close)** | Frameless custom window caption controls dispatching native IPC | PASS | None (immediate native IPC) | None (0px drift verified) | Strict IPC sender validation | Clean hover states | **KEEP** |
| **Single Instance Lock** | `app.requestSingleInstanceLock()` focuses main window on second launch | PASS | None | None | Prevents multiple conflicting processes | None | **KEEP** |
| **Tab Creation (+ / Ctrl+T)** | Dynamically provisions `WebContentsView` with `staunt://newtab` | PASS | Slight view instantiation overhead | Must ensure clean GC on heavy tab churn | Isolated sandboxed session | Clean animation | **OPTIMIZE** |
| **Tab Switching** | Swaps foreground `WebContentsView` and brings to top | PASS | Immediate (0ms blanking) | None | Zero cross-tab state leakage | Clear visual indicator | **KEEP** |
| **Tab Closing (× / Ctrl+W / Middle-click)** | Closes active tab, pushes to `closedTabsStack` (depth 20) | PASS | None | Needs explicit `view.webContents.destroy()` on removal | None | Smooth closing | **HARDEN** (Explicit view resource cleanup) |
| **Tab Reopen (Ctrl+Shift+T)** | Restores tab URL from `closedTabsStack` | PASS | None | None | Re-sanitizes restored URL | Quick feedback | **KEEP** |
| **Tab Drag & Drop Reordering** | HTML5 drag-and-drop on `tabEl`, calls `api.reorderTabs` | PASS | None | Need bounds check on ID array | Input sanitization | Visual ghost styling | **HARDEN** |
| **Tab Muting / Audio Indicator** | Toggles `webContents.setAudioMuted` and listens to media events | PASS | None | None | None | Audible indicator icon | **KEEP** |
| **Smart Omnibox Routing** | Regex parsing for URLs, localhost, IPs, domains, search queries | PASS | Sub-millisecond evaluation | None | Blocks dangerous `javascript:` / data URLs | Focus selection on click | **KEEP** |
| **Autocomplete Suggestions** | Merges bookmarks, history, and STAUNT suggestions | PASS | Remote fetch has 1.5s timeout | If STAUNT backend is down, must still return local | Input string length capped | Dropdown keyboard nav | **HARDEN** (Offline-first fallback) |
| **Navigation Actions (Back/Fwd/Reload/Stop)** | Native Chromium navigation calls on active WebContents | PASS | Native speed | None | None | Dynamic reload/stop toggle | **KEEP** |
| **Homepage Navigation** | Navigates to `settingsDB.homeUrl || 'staunt://newtab'` | PASS | None | None | Validates custom homepage URL | Clean New Tab page | **KEEP** |
| **Three-Dot Menu (16 Actions)** | Custom dropdown menu with zoom, devtools, fullscreen, modals | PASS | Zero layout thrashing | None | None | Keyboard dismiss (Escape) | **KEEP** |
| **History Vault (`staunt_history_vault.json`)** | Records navigation visits, searchable modal, item delete | PASS | Array filter fast (<10k) | Synchronous `fs.writeFileSync` on every visit | None | Grouped timestamp view | **OPTIMIZE** (Debounced/Atomic disk sync) |
| **Bookmarks Vault (`staunt_bookmarks_vault.json`)** | ⭐ button & `Ctrl+D` toggle, searchable manager | PASS | Fast | Sync JSON write | URL format check | Visual star feedback | **HARDEN** (Atomic file write) |
| **Downloads Manager** | Chromium `will-download` stream tracking, open/folder actions | PASS | Real-time percent update | Name collisions handled (`base (1).ext`) | Prevents automatic execution | Toast notifications | **HARDEN** (Verify file existence before open) |
| **Settings Management** | Homepage URL, Default Search, Session restore, Shield level | PASS | In-memory with JSON sync | Invalid input could corrupt config | Validates strings & booleans | Live save toast | **HARDEN** (Schema validation) |
| **Session Restoration** | Saves open tab URLs on exit, restores on startup if enabled | PASS | Fast startup parse | Risk of blank tab if URL invalid | Blocks dangerous scheme restore | Preserves active tab index | **HARDEN** |
| **Save Page As... (`Ctrl+S`)** | Native Chromium `webContents.savePage` (HTMLComplete) | PASS | Native disk write | Shows native Windows Save As dialog | User-chosen safe directory | Completion toast | **KEEP** |
| **Print / Export PDF (`Ctrl+P`)** | Native Chromium `webContents.printToPDF` | PASS | Fast buffer generation | Shows save dialog | Safe PDF container | Clean print layout | **KEEP** |
| **STAUNT Shield Engine** | Request filtering against ad/tracker domain lists | PASS | Fast trie/hash lookup | Whitelists critical CDNs/auth endpoints | Prevents tracking & ad scripts | Blocked counter in UI | **KEEP** |
| **Incognito Mode** | In-memory isolated partition session (`persist:false`) | PASS | Lightweight | Storage clears on window destruction | Zero cookie/history disk persistence | Clear incognito UI icon | **KEEP** |
| **Connection Error Recovery** | Custom error page on navigation failure (DNS, offline) | PASS | Instant local rendering | Provides Retry, Back, Search with STAUNT | No tech leak to remote | Actionable recovery | **KEEP** |
| **Security Hardening** | `site-per-process`, `enable-sandbox`, `verifyIpcSender` | PASS | Zero overhead | Process crashes isolated cleanly | Comprehensive defense-in-depth | None | **HARDEN** |
| **Installer / Packaging** | Genuine Solid LZMA NSIS installer (`makensis.exe`) | PASS | Solid compression (~83 MB) | CRC32 valid (`0xBB1D7159`) | Standard user privileges required | Clean desktop shortcuts | **KEEP** |
