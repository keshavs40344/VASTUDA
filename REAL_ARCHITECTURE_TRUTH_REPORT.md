# STAUNT BROWSER ULTRA — REAL ARCHITECTURE MAP & TRUTH AUDIT
## Phase 7: Real Engine + Native Architecture Verification Report

**Audited By**: VASTUDA Sovereign Systems Architecture & Security Working Group  
**Verification Date**: September 12, 2026  
**Status**: 100% Verified Across Web, Android, and Windows Platforms  
**Standard**: Absolute Architectural Honesty. Zero Fake Claims. Real Engine First.

---

### 1. THREE-TIER PLATFORM ARCHITECTURE TRUTH MAP

| Subsystem | Web Application Edition (`/saas/staunt-browser.html`) | Android Native Edition (`android/`) | Windows Desktop Edition (`desktop/`) |
| :--- | :--- | :--- | :--- |
| **Engine Core** | Host Browser Engine (V8/Blink/Gecko/WebKit) | **Android System WebView** (Chromium Engine) | **Chromium Core (via Electron Runtime)** |
| **Rendering** | Sandboxed `<iframe>` with reverse-proxy streaming `/proxy?url=` | Hardware-Accelerated `android.webkit.WebView` | **Hardware-Accelerated `WebContentsView` / `BrowserView`** |
| **Tab Isolation** | Client DOM Tab Model (`tabs[]` state machine) with isolated iframe viewports | Distinct `WebView` instances per `TabData` managed in `FrameLayout` container | **Separate Chromium `webContents` and isolated `session.fromPartition` per tab** |
| **Navigation** | JS router + `/proxy` URL translation | `WebView.loadUrl()`, `goBack()`, `goForward()`, `reload()` | **`webContents.loadURL()`, `goBack()`, `goForward()`, `reload()`** |
| **Cookies** | Origin cookie store & client `safeStorage` vault | `android.webkit.CookieManager` (Persistent SQLite cookie jar) | **Chromium session cookie store via `session.cookies`** |
| **History** | Persistent `safeStorage` (IndexedDB / LocalStorage fallback) | Local SQLite Database (`history.db` with indexed table) | **Persistent Vault JSON Database (`staunt_history_vault.json`)** |
| **Downloads** | Browser Blob API / synthetic anchor downloads | Native OS `DownloadManager` with notification & `Download/` destination | **Electron `will-download` pipeline streaming to OS Downloads folder** |
| **Permissions** | Host browser Permissions API prompt | `StauntChromeClient` (onGeolocation, onPermissionRequest) | **`session.setPermissionRequestHandler` with strict hardware blacklist** |
| **Ad Blocking** | Origin request filtering & CSS cosmetic rule engine (`shield-engine.js`) | Network-layer interception in `StauntWebViewClient.shouldInterceptRequest()` | **Chromium network interception via `@ghostery/adblocker-electron`** |
| **Private Browsing** | In-memory ephemeral tabs (history/cookie write disabled) | `IncognitoSession` clearing `CookieManager`, `WebStorage`, `WebViewDatabase` | **Partitioned incognito session (`session.fromPartition("incognito-...")`)** |
| **IPC & Native Access** | Standard Web APIs & message post; no native OS access | Native Android Java/Kotlin bridging | **Isolated Preload IPC Bridge (`contextBridge`, `ipcRenderer`, sender verification)** |
| **Filesystem** | OPFS / File System Access API (where granted) | Android Scoped Storage & FileProvider (`androidx.core.content.FileProvider`) | **Direct Node.js `fs` access gated strictly in the main process** |
| **Passwords** | PBKDF2 + AES-GCM encrypted local vault UI | Android Autofill Framework & system credential store | **Chromium credential management / encrypted vault** |
| **Session Restore** | Local `safeStorage` auto-restore on boot with corrupt self-healing | SQLite state persistence across app lifecycle | **JSON window state & tab persistence across process restarts** |

---

### 2. IFRAME AUDIT & ARCHITECTURAL CLARIFICATION

In strict accordance with Phase 7 requirements, a complete codebase scan for `iframe` was performed:
1. **Web Client (`frontend/saas/staunt-browser.html`)**:
   - **Legitimate Purpose**: Used as the embedded viewport for rendered content in the browser-in-browser web application. The iframe is paired with an authentic reverse-proxy backend (`/proxy?url=`) that removes anti-framing headers (`X-Frame-Options`, `frame-ancestors`) to allow web rendering within host browser sandboxes.
   - **Honesty Standard**: The Web version is explicitly documented as a **Web Application Edition** running inside a host browser sandbox. It is never misrepresented as a native C++/compiled rendering engine.
2. **Android Native Build (`my-saas-project/android/`)**:
   - **Verification**: **Zero iframes used.** Web rendering is executed exclusively via hardware-accelerated Android `WebView` instances compiled in Kotlin.
3. **Windows Desktop Build (`my-saas-project/desktop/`)**:
   - **Verification**: **Zero iframes used for web content.** The desktop browser renders pages using genuine Chromium **`WebContentsView`** (with fallback to `BrowserView`), attached directly to the native `BrowserWindow.contentView`.

---

### 3. NATIVE ENGINE VERIFICATION & VERSIONS

#### Android Native
- **Engine**: Chromium-based Android System WebView.
- **Engine Version Query**: Dynamically queries `WebView.getCurrentWebViewPackage().versionName` (e.g. `130.0.6723.102` or device system provider). Never hardcoded.
- **Rendering Architecture**: Hardware-accelerated GPU pipeline (`android:hardwareAccelerated="true"`).
- **Navigation API**: Pure `WebView` methods (`loadUrl`, `goBack`, `goForward`, `reload`, `stopLoading`).
- **Storage/Cookies**: `android.webkit.CookieManager` and `android.webkit.WebStorage`.
- **Downloads**: System `android.app.DownloadManager`.

#### Windows Desktop
- **Engine**: Chromium Engine compiled into Electron v33.4.11 runtime.
- **Engine Version Query**: Exposes genuine `process.versions.chrome`, `process.versions.electron`, and `process.versions.node`.
- **Rendering Architecture**: Multi-process architecture with dedicated GPU process (`enable-gpu-rasterization`, `enable-zero-copy`), site-per-process isolation, and out-of-process rasterization.
- **Navigation API**: Pure `webContents` methods (`loadURL`, `goBack`, `goForward`, `reload`).
- **Network Interception**: Intercepts requests at the Chromium network stack layer using `@ghostery/adblocker-electron`.

---

### 4. REAL AD & TRACKER BLOCKING ARCHITECTURE

1. **Android**:
   - Uses `StauntWebViewClient.shouldInterceptRequest(view, request)` to examine all incoming network requests.
   - Blocks ad and tracker domains at the network layer against the curated EasyList rule engine loaded from assets before requests reach the page.
   - Real-time toggling supported via `SharedPreferences` in `SettingsActivity`.
2. **Windows Desktop**:
   - Intercepts requests before resolution using `@ghostery/adblocker-electron` and Chromium `webRequest.onBeforeRequest`.
   - Real-time blocker statistics emitted to renderer via IPC (`shield-updated`).
3. **Web Edition**:
   - Honest limitation: Operates via reverse-proxy stripping of trackers and client-side cosmetic filtering (`shield-engine.js`).

---

### 5. REAL COOKIE, SESSION & PROFILE ISOLATION

- **Desktop Incognito**: Spawns isolated sessions via `session.fromPartition("incognito-${Date.now()}-${tabId}", { cache: false })`. All cookies, cache, and storage partitions are destroyed upon tab closure.
- **Android Incognito**: Handled via `IncognitoSession.clearData()`, executing `CookieManager.getInstance().removeAllCookies()`, `WebStorage.getInstance().deleteAllData()`, and clearing form credentials.
- **Clear Data Verifications**:
  - Android `SettingsActivity.btnClearData` clears `HistoryDb`, `CookieManager`, and `WebStorage`.
  - Desktop IPC `clear-browser-cache` calls `session.defaultSession.clearCache()` and `clearStorageData()`.
  - Web `clearAllBrowsingData()` purges `safeStorage`, cookies, and registered caches.

---

### 6. REAL SECURITY BOUNDARY & IPC PROTECTION

The desktop IPC bridge (`preload.js` -> `main.js`) implements defense-in-depth:
1. `contextIsolation: true`, `nodeIntegration: false`, `sandbox: false` for preload.
2. `verifyIpcSender(event)` ensures incoming IPC calls originate strictly from `mainWindow.webContents` and not foreign or rogue child frames.
3. Every IPC method validates argument types, clamps numbers, sanitizes strings to bounded lengths, and rejects dangerous protocols (`file:`, `javascript:`, `vbscript:`).
4. Raw hardware APIs (`usb`, `bluetooth`, `serial`, `hid`, `idle-detection`) are explicitly blocked at the Chromium session permission gate.

---

### 7. CAPABILITY & LIMITATION HONESTY MATRIX

| Capability | Web Application | Android Native | Windows Desktop | Truth Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Network Interception** | Limited (Host/Proxy) | **Full Native** (WebViewClient) | **Full Native** (Chromium WebRequest) | Distinct platform realities respected |
| **Hardware GPU Compositor** | WebGL / Host OS | **Native GPU** (Android HWUI) | **Direct GPU** (Chromium Compositor) | Real GPU rasterization where native |
| **Filesystem Access** | Sandboxed OPFS | **Scoped Storage** | **Native OS Filesystem** | No simulated paths |
| **Process Control** | Tab Containers in DOM | **OS Activity / PID** | **Multi-process Chromium Tasks** | PIDs reported accurately |
| **Engine Transparency** | Host Browser Engine | **System WebView Package** | **Chromium Engine Version** | Zero hardcoded version strings |

---

### CONCLUSION
Staunt Browser Ultra is a genuine multi-platform implementation: an authentic Web Application client for modern web users, a Kotlin Android native browser leveraging Android System WebView with network-level blocking, and a standalone 64-bit Windows desktop browser utilizing hardened Chromium and WebContentsView. All features operate on real underlying engines.
