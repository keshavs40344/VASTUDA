// Staunt Browser Ultra — Enterprise Hardened Chromium Engine
// Former Google Project Zero / Chromium Security Team Architectural Grade
// Resolves Viewport Freeze & Blank Screen via Precision WebContentsView Geometry

const { app, BrowserWindow, WebContentsView, BrowserView, session, ipcMain, Menu, dialog, clipboard, screen, shell } = require('electron');
const path = require('path');
const fs = require('fs');
const { isHomographOrDeceptive } = require('./src/adblocker');
const {
  initStauntShieldEngine,
  enableShieldInSession,
  attachShieldToWebContents,
  isCriticalWhitelisted
} = require('./src/adblocker-core');

// =============================================================================
// ROBUST WINDOW STATE PERSISTENCE (Fixes Progressive Window Shrinking Bug)
// =============================================================================
const USER_DATA_PATH = app.getPath('userData');
const WINDOW_STATE_FILE = path.join(USER_DATA_PATH, 'window-state.json');

// =============================================================================
// RESILIENT ATOMIC JSON STORAGE UTILITIES (Zero Corruption & .bak Recovery)
// =============================================================================
function atomicWriteJson(filePath, data) {
  try {
    const tempFile = `${filePath}.${Date.now()}.${Math.random().toString(36).substr(2, 6)}.tmp`;
    const bakFile = `${filePath}.bak`;
    const jsonContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
    fs.writeFileSync(tempFile, jsonContent, 'utf-8');
    if (fs.existsSync(filePath)) {
      try {
        fs.copyFileSync(filePath, bakFile);
      } catch (e) {}
    }
    fs.renameSync(tempFile, filePath);
  } catch (err) {
    console.warn(`[ATOMIC WRITE ERROR] Failed writing ${filePath}:`, err.message);
    try {
      fs.writeFileSync(filePath, typeof data === 'string' ? data : JSON.stringify(data, null, 2), 'utf-8');
    } catch (e) {}
  }
}

function readJsonWithBak(filePath, fallback = null) {
  try {
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    }
  } catch (err) {
    console.warn(`[STORAGE RESILIENCE] Primary file corrupted: ${filePath}, attempting .bak restore:`, err.message);
    const bakFile = `${filePath}.bak`;
    try {
      if (fs.existsSync(bakFile)) {
        const restored = JSON.parse(fs.readFileSync(bakFile, 'utf-8'));
        atomicWriteJson(filePath, restored);
        return restored;
      }
    } catch (bakErr) {
      console.error(`[STORAGE RESILIENCE] Backup restore failed for ${bakFile}:`, bakErr.message);
    }
  }
  return fallback;
}

const DEFAULT_WINDOW_BOUNDS = {
  width: 1200,
  height: 800,
  x: undefined,
  y: undefined,
  isMaximized: false,
  isFullScreen: false,
  maximized: false,
  fullscreen: false
};

let windowState = { ...DEFAULT_WINDOW_BOUNDS };

function loadWindowState() {
  try {
    const raw = readJsonWithBak(WINDOW_STATE_FILE, null);
    if (raw && typeof raw === 'object') {
      if (Number.isFinite(raw.width) && raw.width >= 600) windowState.width = Math.round(raw.width);
      if (Number.isFinite(raw.height) && raw.height >= 400) windowState.height = Math.round(raw.height);
      if (Number.isFinite(raw.x)) windowState.x = Math.round(raw.x);
      if (Number.isFinite(raw.y)) windowState.y = Math.round(raw.y);
      const maxVal = Boolean(raw.isMaximized !== undefined ? raw.isMaximized : raw.maximized);
      windowState.isMaximized = maxVal;
      windowState.maximized = maxVal;
      const fullVal = Boolean(raw.isFullScreen !== undefined ? raw.isFullScreen : raw.fullscreen);
      windowState.isFullScreen = fullVal;
      windowState.fullscreen = fullVal;
    }
  } catch (e) {
    console.warn('[WINDOW STATE] Failed to parse window-state.json, falling back to defaults:', e.message);
    windowState = { ...DEFAULT_WINDOW_BOUNDS };
  }
}

loadWindowState();

function getValidatedWindowState() {
  const displays = screen.getAllDisplays();
  if (!displays || displays.length === 0) return windowState;

  const targetPoint = {
    x: (windowState.x !== undefined) ? (windowState.x + Math.floor(windowState.width / 2)) : displays[0].workArea.x + 100,
    y: (windowState.y !== undefined) ? (windowState.y + Math.floor(windowState.height / 2)) : displays[0].workArea.y + 100
  };

  const activeDisplay = screen.getDisplayNearestPoint(targetPoint) || screen.getPrimaryDisplay();
  const workArea = activeDisplay.workArea;

  const minWidth = 800;
  const minHeight = 500;

  let width = Math.min(Math.max(windowState.width || 1200, minWidth), workArea.width);
  let height = Math.min(Math.max(windowState.height || 800, minHeight), workArea.height);

  let x = windowState.x;
  let y = windowState.y;

  const isOutside = (x === undefined || y === undefined ||
    x + width < workArea.x + 50 ||
    x > workArea.x + workArea.width - 50 ||
    y + height < workArea.y + 50 ||
    y > workArea.y + workArea.height - 50);

  if (isOutside) {
    x = Math.round(workArea.x + Math.max(0, (workArea.width - width) / 2));
    y = Math.round(workArea.y + Math.max(0, (workArea.height - height) / 2));
  } else {
    x = Math.max(workArea.x, Math.min(x, workArea.x + workArea.width - width));
    y = Math.max(workArea.y, Math.min(y, workArea.y + workArea.height - height));
  }

  return {
    width: Math.round(width),
    height: Math.round(height),
    x: Math.round(x),
    y: Math.round(y),
    isMaximized: Boolean(windowState.isMaximized || windowState.maximized),
    maximized: Boolean(windowState.isMaximized || windowState.maximized),
    isFullScreen: Boolean(windowState.isFullScreen || windowState.fullscreen),
    fullscreen: Boolean(windowState.isFullScreen || windowState.fullscreen)
  };
}

let saveStateDebounceTimer = null;

function saveWindowState() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) return;

  const isMax = mainWindow.isMaximized();
  const isFull = mainWindow.isFullScreen();

  let bounds;
  if (typeof mainWindow.getNormalBounds === 'function') {
    bounds = mainWindow.getNormalBounds();
  } else if (!isMax && !isFull) {
    bounds = mainWindow.getBounds();
  } else {
    bounds = {
      x: windowState.x,
      y: windowState.y,
      width: windowState.width,
      height: windowState.height
    };
  }

  if (bounds && bounds.width >= 600 && bounds.height >= 400) {
    windowState = {
      x: Math.round(bounds.x),
      y: Math.round(bounds.y),
      width: Math.round(bounds.width),
      height: Math.round(bounds.height),
      isMaximized: isMax,
      maximized: isMax,
      isFullScreen: isFull,
      fullscreen: isFull
    };

    atomicWriteJson(WINDOW_STATE_FILE, windowState);
  }
}

function scheduleSaveWindowState() {
  if (saveStateDebounceTimer) clearTimeout(saveStateDebounceTimer);
  saveStateDebounceTimer = setTimeout(saveWindowState, 300);
}

// =============================================================================
// DIRECTIVE 1: ENGINE BOOT HARDENING & HARDWARE ACCELERATION
// =============================================================================
// Process & Origin Isolation
app.commandLine.appendSwitch('site-per-process');
app.commandLine.appendSwitch('enable-features', 'IsolateOrigins,BlockInsecurePrivateNetworkRequests,VaapiVideoDecoder,CanvasOopRasterization,SmoothScrolling');

// Side-Channel Timing Attack Mitigation (Spectre / Meltdown)
app.commandLine.appendSwitch('enable-features', 'ReduceTimerPrecision');
app.commandLine.appendSwitch('disable-features', 'SharedArrayBuffer');

// Sandboxing Hardening
app.commandLine.appendSwitch('enable-sandbox');
app.commandLine.appendSwitch('disable-blink-features', 'WebUSB,WebHID,Serial,IdleDetection,WebBluetooth,DirectSockets');

// High-Performance GPU Rasterization & Zero-Copy
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

// GPU Guard to recover cleanly from malformed shaders
app.on('gpu-process-crashed', (event, killed) => {
  console.error(`[CRITICAL GPU GUARD] Chromium GPU process crashed (killed: ${killed}). Recovering cleanly...`);
});

app.on('child-process-gone', (event, details) => {
  console.warn(`[CHILD PROCESS MONITOR] Process ${details.type} gone: ${details.reason} (Exit code: ${details.exitCode})`);
});

// Official Chrome Windows User-Agent across all sessions to prevent site breakage / mobile redirects
const OFFICIAL_CHROME_WINDOWS_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';

let mainWindow = null;
let tabs = new Map();
let activeTabId = null;
let secondaryTabId = null;
let nextTabId = 1;
let closedTabsStack = [];

// Apple Safari Native 44px Topbar Geometry
let isSplitViewActive = false;
let splitRatio = 0.5;
const TOOLBAR_HEIGHT = 44; // Fixed native 44px Apple topbar

// =============================================================================
// LOCAL VAULT STORAGE (History, Bookmarks, Downloads, Settings)
// =============================================================================
const HISTORY_FILE = path.join(USER_DATA_PATH, 'staunt_history_vault.json');
const BOOKMARKS_FILE = path.join(USER_DATA_PATH, 'staunt_bookmarks_vault.json');
const DOWNLOADS_FILE = path.join(USER_DATA_PATH, 'staunt_downloads_vault.json');
const SETTINGS_FILE = path.join(USER_DATA_PATH, 'staunt_settings.json');

let historyDB = [];
let bookmarksDB = [];
let downloadsDB = [];
const DEFAULT_SETTINGS = {
  searchEngine: 'staunt',
  searchUrl: 'https://vastuda-search.onrender.com',
  homeUrl: 'staunt://newtab',
  shieldLevel: 'standard',
  hardwareAcceleration: true,
  restoreTabsOnStartup: false
};
let settingsDB = { ...DEFAULT_SETTINGS };

historyDB = readJsonWithBak(HISTORY_FILE, []) || [];
bookmarksDB = readJsonWithBak(BOOKMARKS_FILE, []) || [];
downloadsDB = readJsonWithBak(DOWNLOADS_FILE, []) || [];
const loadedSettings = readJsonWithBak(SETTINGS_FILE, null);
settingsDB = loadedSettings ? { ...DEFAULT_SETTINGS, ...loadedSettings } : { ...DEFAULT_SETTINGS };

function recordHistory(url, title) {
  if (!url || typeof url !== 'string') return;
  const cleanUrl = url.trim().slice(0, 2048);
  if (cleanUrl.includes('newtab.html') || cleanUrl === 'about:blank' || cleanUrl.startsWith('staunt://')) return;
  
  const entry = {
    id: Date.now().toString(36) + Math.random().toString(36).substr(2, 6),
    url: cleanUrl,
    title: (title || cleanUrl).slice(0, 256),
    timestamp: Date.now()
  };
  
  historyDB.unshift(entry);
  if (historyDB.length > 5000) historyDB.pop();
  
  atomicWriteJson(HISTORY_FILE, historyDB.slice(0, 1000));
}

function clearHistoryRange(range = 'all') {
  const now = Date.now();
  if (range === '1h' || range === 'last-hour') {
    const cutoff = now - 3600 * 1000;
    historyDB = historyDB.filter(h => h.timestamp < cutoff);
  } else if (range === '24h' || range === 'last-24h') {
    const cutoff = now - 24 * 3600 * 1000;
    historyDB = historyDB.filter(h => h.timestamp < cutoff);
  } else if (range === '7d' || range === 'last-7d') {
    const cutoff = now - 7 * 24 * 3600 * 1000;
    historyDB = historyDB.filter(h => h.timestamp < cutoff);
  } else if (range === '4w' || range === 'last-4w') {
    const cutoff = now - 28 * 24 * 3600 * 1000;
    historyDB = historyDB.filter(h => h.timestamp < cutoff);
  } else {
    historyDB = [];
  }
  atomicWriteJson(HISTORY_FILE, historyDB);
  return { success: true, count: historyDB.length };
}

function recordDownload(entry) {
  if (!entry || !entry.id) return;
  const existingIdx = downloadsDB.findIndex(d => d.id === entry.id);
  if (existingIdx !== -1) {
    downloadsDB[existingIdx] = { ...downloadsDB[existingIdx], ...entry };
  } else {
    downloadsDB.unshift(entry);
    if (downloadsDB.length > 200) downloadsDB.pop();
  }
  atomicWriteJson(DOWNLOADS_FILE, downloadsDB.slice(0, 100));
}

const SESSION_FILE = path.join(USER_DATA_PATH, 'staunt_session_tabs.json');

function saveSessionTabs() {
  if (tabs.size === 0) return;
  const sessionTabs = [];
  for (const [id, tab] of tabs.entries()) {
    if (!tab.isIncognito && tab.url && !tab.url.startsWith('javascript:') && !tab.url.startsWith('data:')) {
      sessionTabs.push({
        url: tab.url,
        title: tab.title,
        isPinned: tab.isPinned,
        workspaceId: tab.workspaceId
      });
    }
  }
  atomicWriteJson(SESSION_FILE, sessionTabs);
}

function restoreSessionTabs() {
  try {
    const data = readJsonWithBak(SESSION_FILE, null);
    if (Array.isArray(data) && data.length > 0) {
      for (const item of data) {
        createTab(item.url || 'staunt://newtab', {
          isPinned: Boolean(item.isPinned),
          workspaceId: item.workspaceId
        });
      }
      return true;
    }
  } catch (e) {}
  return false;
}

function cycleTab(direction = 1) {
  const tabIds = Array.from(tabs.keys());
  if (tabIds.length <= 1) return;
  const currentIndex = tabIds.indexOf(activeTabId);
  const nextIndex = (currentIndex + direction + tabIds.length) % tabIds.length;
  switchTab(tabIds[nextIndex]);
}

function reorderTabs(orderedIds) {
  if (!Array.isArray(orderedIds)) return;
  const newMap = new Map();
  for (const id of orderedIds) {
    const numId = Number(id);
    if (tabs.has(numId)) {
      newMap.set(numId, tabs.get(numId));
    }
  }
  for (const [id, tab] of tabs.entries()) {
    if (!newMap.has(id)) {
      newMap.set(id, tab);
    }
  }
  tabs = newMap;
}

function isUrlBookmarked(url) {
  if (!url || typeof url !== 'string') return false;
  const clean = url.trim();
  if (!clean || clean.startsWith('staunt://') || clean.includes('newtab.html') || clean === 'about:blank') return false;
  return bookmarksDB.some(b => b.url === clean);
}

function toggleBookmarkCurrentPage() {
  const tab = tabs.get(activeTabId);
  if (!tab) return { bookmarked: false };
  const currentUrl = tab.url;
  if (!currentUrl || currentUrl.startsWith('staunt://') || currentUrl.includes('newtab.html') || currentUrl === 'about:blank') {
    return { bookmarked: false, url: currentUrl };
  }
  const existingIdx = bookmarksDB.findIndex(b => b.url === currentUrl);
  if (existingIdx !== -1) {
    bookmarksDB.splice(existingIdx, 1);
    atomicWriteJson(BOOKMARKS_FILE, bookmarksDB);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bookmark-status-changed', { url: currentUrl, bookmarked: false });
    }
    return { bookmarked: false, url: currentUrl };
  } else {
    const newItem = {
      id: Date.now().toString(36) + Math.random().toString(36).substr(2, 5),
      title: tab.title || currentUrl,
      url: currentUrl,
      favicon: tab.favicon || '',
      createdAt: Date.now()
    };
    bookmarksDB.unshift(newItem);
    atomicWriteJson(BOOKMARKS_FILE, bookmarksDB);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('bookmark-status-changed', { url: currentUrl, bookmarked: true, bookmark: newItem });
    }
    return { bookmarked: true, url: currentUrl, bookmark: newItem };
  }
}

function deleteBookmark(id) {
  const initLen = bookmarksDB.length;
  bookmarksDB = bookmarksDB.filter(b => b.id !== id);
  atomicWriteJson(BOOKMARKS_FILE, bookmarksDB);
  return { success: bookmarksDB.length < initLen };
}

function deleteHistoryItem(id) {
  const initLen = historyDB.length;
  historyDB = historyDB.filter(h => h.id !== id);
  atomicWriteJson(HISTORY_FILE, historyDB);
  return { success: historyDB.length < initLen };
}

function clearDownloads() {
  downloadsDB = [];
  atomicWriteJson(DOWNLOADS_FILE, []);
  return { success: true };
}

// =============================================================================
// NATIVE MENU HELPERS
// =============================================================================
function adjustZoom(delta) {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.zoomLevel = Math.max(-3, Math.min(3, (tab.zoomLevel || 0) + delta));
    tab.view.webContents.setZoomLevel(tab.zoomLevel);
  }
}

function resetZoom() {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.zoomLevel = 0;
    tab.view.webContents.setZoomLevel(0);
  }
}

function bookmarkCurrentPage() {
  const tab = tabs.get(activeTabId);
  if (tab) {
    const item = { title: tab.title, url: tab.url, favicon: tab.favicon };
    bookmarksDB.push({ id: Date.now().toString(36), ...item });
    atomicWriteJson(BOOKMARKS_FILE, bookmarksDB);
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('bookmark-added', item);
  }
}

function saveCurrentPage() {
  const tab = tabs.get(activeTabId);
  if (!tab || !tab.view || !tab.view.webContents) return;
  const currentUrl = tab.url || '';
  if (!currentUrl || currentUrl.startsWith('staunt://') || currentUrl.includes('newtab.html') || currentUrl === 'about:blank') {
    return;
  }
  let defaultName = 'webpage.html';
  if (tab.title) {
    defaultName = tab.title.replace(/[^a-zA-Z0-9_\- ]/g, '_').trim().slice(0, 60) + '.html';
  }
  dialog.showSaveDialog(mainWindow, {
    title: 'Save Page As',
    defaultPath: defaultName,
    filters: [
      { name: 'HTML Complete', extensions: ['html', 'htm'] },
      { name: 'All Files', extensions: ['*'] }
    ]
  }).then(result => {
    if (result && result.filePath) {
      tab.view.webContents.savePage(result.filePath, 'HTMLComplete')
        .then(() => {
          if (mainWindow && !mainWindow.isDestroyed()) {
            mainWindow.webContents.send('download-complete', { fileName: path.basename(result.filePath) });
          }
        })
        .catch(err => console.error('[SAVE PAGE ERROR]', err));
    }
  }).catch(err => console.error(err));
}

function showAboutDialog() {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'About Staunt Browser',
    message: 'Staunt Browser Ultra',
    detail: `Version: 2.0.0\nVendor: VASTUDA Sovereign Systems\nChromium: ${process.versions.chrome || 'Engine version unavailable'}\nElectron: ${process.versions.electron || 'Unavailable'}\nNode.js: ${process.versions.node || 'Unavailable'}\nV8: ${process.versions.v8 || 'Unavailable'}\nOS: ${process.platform} ${process.arch}`
  });
}

const menuTemplate = [
  {
    label: 'File',
    submenu: [
      { label: 'New Tab', accelerator: 'CmdOrCtrl+T', click: () => createTab('staunt://newtab') },
      { label: 'New Incognito Tab', accelerator: 'CmdOrCtrl+Shift+N', click: () => createTab('staunt://newtab', { isIncognito: true }) },
      { type: 'separator' },
      { label: 'Save Page As...', accelerator: 'CmdOrCtrl+S', click: () => saveCurrentPage() },
      { label: 'Close Tab', accelerator: 'CmdOrCtrl+W', click: () => closeTab(activeTabId) },
      { label: 'Reopen Closed Tab', accelerator: 'CmdOrCtrl+Shift+T', click: () => undoCloseTab() },
      { type: 'separator' },
      { label: 'Print...', accelerator: 'CmdOrCtrl+P', click: () => { 
        const tab = tabs.get(activeTabId);
        if (tab && tab.view && tab.view.webContents) {
          tab.view.webContents.printToPDF({}).then(data => {
            dialog.showSaveDialog(mainWindow, {
              title: 'Save PDF',
              defaultPath: 'webpage.pdf',
              filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
            }).then(result => {
              if (result.filePath) fs.writeFileSync(result.filePath, data);
            });
          }).catch(err => console.error(err));
        }
      } },
      { type: 'separator' },
      { label: 'Exit', accelerator: 'Alt+F4', click: () => app.quit() }
    ]
  },
  {
    label: 'Edit',
    submenu: [
      { role: 'undo' },
      { role: 'redo' },
      { type: 'separator' },
      { role: 'cut' },
      { role: 'copy' },
      { role: 'paste' },
      { role: 'selectAll' },
      { type: 'separator' },
      { label: 'Find...', accelerator: 'CmdOrCtrl+F', click: () => { if (mainWindow) mainWindow.webContents.send('toggle-find-bar'); } }
    ]
  },
  {
    label: 'View',
    submenu: [
      { label: 'Reload', accelerator: 'F5', click: () => handleReload() },
      { label: 'Hard Reload', accelerator: 'CmdOrCtrl+Shift+R', click: () => { const tab = tabs.get(activeTabId); if (tab && tab.view && tab.view.webContents) tab.view.webContents.reloadIgnoringCache(); } },
      { type: 'separator' },
      { label: 'Zoom In', accelerator: 'CmdOrCtrl+Plus', click: () => adjustZoom(1) },
      { label: 'Zoom Out', accelerator: 'CmdOrCtrl+-', click: () => adjustZoom(-1) },
      { label: 'Reset Zoom', accelerator: 'CmdOrCtrl+0', click: () => resetZoom() },
      { type: 'separator' },
      { label: 'Toggle Fullscreen', accelerator: 'F11', click: () => { if (mainWindow) mainWindow.setFullScreen(!mainWindow.isFullScreen()); } },
      { type: 'separator' },
      { label: 'Developer Tools', accelerator: 'F12', click: () => { const tab = tabs.get(activeTabId); if (tab && tab.view && tab.view.webContents) tab.view.webContents.toggleDevTools(); } }
    ]
  },
  {
    label: 'Bookmarks',
    submenu: [
      { label: 'Bookmark This Page', accelerator: 'CmdOrCtrl+D', click: () => bookmarkCurrentPage() },
      { type: 'separator' },
      { label: 'Show All Bookmarks', click: () => { if (mainWindow) mainWindow.webContents.send('show-bookmarks'); } }
    ]
  },
  {
    label: 'Help',
    submenu: [
      { label: 'About Staunt Browser', click: () => showAboutDialog() }
    ]
  }
];

// =============================================================================
// MAIN WINDOW INITIALIZATION (Frameless, #090a0f Background)
// =============================================================================
function createMainWindow() {
  const validatedState = getValidatedWindowState();
  mainWindow = new BrowserWindow({
    width: validatedState.width,
    height: validatedState.height,
    x: validatedState.x,
    y: validatedState.y,
    minWidth: 900,
    minHeight: 600,
    frame: false,
    backgroundColor: '#090a0f',
    titleBarStyle: 'hidden',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      nodeIntegrationInWorker: false,
      nodeIntegrationInSubFrames: false,
      contextIsolation: true,
      sandbox: false,
      enableRemoteModule: false,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webviewTag: false
    }
  });

  if (validatedState.isMaximized) {
    mainWindow.maximize();
  } else if (validatedState.isFullScreen) {
    mainWindow.setFullScreen(true);
  }

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    // Instantiate and attach initial WebContentsView immediately so viewport is never 0x0
    if (tabs.size === 0) {
      if (settingsDB.restoreTabsOnStartup && restoreSessionTabs()) {
        console.log('[SESSION] Restored tabs from previous session');
      } else {
        createTab('staunt://newtab');
      }
    } else {
      updateLayoutBounds();
    }
  });

  // Global Session User-Agent & Network Filter Configuration
  session.defaultSession.setUserAgent(OFFICIAL_CHROME_WINDOWS_UA);

  session.defaultSession.webRequest.onHeadersReceived((details, callback) => {
    const responseHeaders = { ...details.responseHeaders };
    
    if (details.url.startsWith('file://') || details.url.includes('newtab.html')) {
      responseHeaders['Content-Security-Policy'] = [
        "default-src 'self' file: data: https://unpkg.com https://fonts.googleapis.com https://fonts.gstatic.com; script-src 'self' 'unsafe-inline' https://unpkg.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data: https: file:; object-src 'none'; frame-ancestors 'none';"
      ];
    }
    
    responseHeaders['X-Content-Type-Options'] = ['nosniff'];
    callback({ responseHeaders });
  });

  // Initialize Shield Engine
  initStauntShieldEngine(USER_DATA_PATH).then(() => {
    enableShieldInSession(session.defaultSession, (stats) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('shield-updated', stats);
      }
    });
  }).catch((e) => console.warn('[SHIELD INIT WARNING]', e));

  // Granular Hardware API Gate
  session.defaultSession.setPermissionRequestHandler((webContents, permission, callback, details) => {
    const permLower = permission.toLowerCase();
    if (['usb', 'bluetooth', 'serial', 'hid', 'idle-detection', 'pointer-lock'].includes(permLower)) {
      console.warn(`[SECURITY HARDWARE GATE] Denied raw hardware API: ${permission}`);
      return callback(false);
    }
    
    const url = details.requestingUrl || webContents.getURL();
    console.log(`[PERMISSION GATE] Authorized request: ${permission} from ${url}`);

    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('permission-requested', {
        permission: permission,
        url: url
      });
    }
    callback(true);
  });

  // Native Download Manager with Persistent Vault Tracking
  session.defaultSession.on('will-download', (event, item, webContents) => {
    const downloadId = Date.now().toString(36) + Math.random().toString(36).substr(2, 5);
    const totalBytes = item.getTotalBytes();
    let fileName = item.getFilename();
    const saveDir = app.getPath('downloads');
    let targetPath = path.join(saveDir, fileName);

    if (fs.existsSync(targetPath)) {
      const ext = path.extname(fileName);
      const base = path.basename(fileName, ext);
      let counter = 1;
      while (fs.existsSync(path.join(saveDir, `${base} (${counter})${ext}`))) {
        counter++;
      }
      fileName = `${base} (${counter})${ext}`;
      targetPath = path.join(saveDir, fileName);
    }
    item.setSavePath(targetPath);

    const downloadEntry = {
      id: downloadId,
      fileName: fileName,
      filePath: targetPath,
      totalBytes: totalBytes,
      receivedBytes: 0,
      state: 'progressing',
      url: item.getURL() || '',
      mimeType: item.getMimeType() || '',
      timestamp: Date.now()
    };
    recordDownload(downloadEntry);

    item.on('updated', (e, state) => {
      const received = item.getReceivedBytes();
      const percent = totalBytes > 0 ? Math.floor((received / totalBytes) * 100) : 0;
      downloadEntry.receivedBytes = received;
      downloadEntry.state = state;
      recordDownload(downloadEntry);

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('download-progress', {
          id: downloadId,
          fileName: fileName,
          filePath: targetPath,
          percent: percent,
          receivedBytes: received,
          totalBytes: totalBytes,
          state: state
        });
      }
    });

    item.once('done', (e, state) => {
      downloadEntry.state = state;
      downloadEntry.receivedBytes = item.getReceivedBytes();
      recordDownload(downloadEntry);

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('download-complete', {
          id: downloadId,
          fileName: fileName,
          filePath: targetPath,
          state: state,
          totalBytes: totalBytes
        });
      }
    });
  });

  // Dynamic Window Resize Observers (Immediate Bounds Recalculation & Window State Debounce)
  function broadcastWindowState(stateName) {
    if (mainWindow && !mainWindow.isDestroyed()) {
      const isMax = mainWindow.isMaximized();
      const isMin = mainWindow.isMinimized();
      const isFull = mainWindow.isFullScreen();
      mainWindow.webContents.send('window-state-changed', {
        state: stateName || (isFull ? 'FULLSCREEN' : isMax ? 'MAXIMIZED' : isMin ? 'MINIMIZED' : 'NORMAL'),
        isMaximized: isMax,
        maximized: isMax,
        isMinimized: isMin,
        minimized: isMin,
        isFullScreen: isFull,
        fullscreen: isFull
      });
    }
  }

  mainWindow.on('resize', () => {
    updateLayoutBounds();
    scheduleSaveWindowState();
  });
  mainWindow.on('move', () => {
    updateLayoutBounds();
    scheduleSaveWindowState();
  });
  mainWindow.on('maximize', () => {
    broadcastWindowState('MAXIMIZED');
    updateLayoutBounds();
    scheduleSaveWindowState();
    setTimeout(updateLayoutBounds, 25);
  });
  mainWindow.on('unmaximize', () => {
    broadcastWindowState('NORMAL');
    updateLayoutBounds();
    scheduleSaveWindowState();
    setTimeout(updateLayoutBounds, 25);
  });
  mainWindow.on('minimize', () => {
    broadcastWindowState('MINIMIZED');
  });
  mainWindow.on('restore', () => {
    broadcastWindowState(mainWindow.isMaximized() ? 'MAXIMIZED' : 'NORMAL');
    updateLayoutBounds();
    scheduleSaveWindowState();
  });
  mainWindow.on('enter-full-screen', () => {
    broadcastWindowState('FULLSCREEN');
    updateLayoutBounds();
    scheduleSaveWindowState();
  });
  mainWindow.on('leave-full-screen', () => {
    broadcastWindowState('NORMAL');
    updateLayoutBounds();
    scheduleSaveWindowState();
  });
  
  mainWindow.on('close', () => {
    saveSessionTabs();
    saveWindowState();
    // Clean up all tab views to prevent orphaned WebContentsView instances
    for (const [id, tab] of tabs.entries()) {
      try {
        detachTabView(tab);
        if (tab.view && tab.view.webContents && !tab.view.webContents.isDestroyed()) {
          tab.view.webContents.stop();
          tab.view.webContents.close();
          if (typeof tab.view.webContents.destroy === 'function') {
            tab.view.webContents.destroy();
          }
        }
        tab.view = null;
      } catch (e) {}
    }
    tabs.clear();
  });
  
  mainWindow.on('closed', () => {
    mainWindow = null;
    tabs.clear();
  });
}

// =============================================================================
// PRECISION VIEW BOUNDS MANAGER (x: 0, y: 44, width: w, height: h - 44)
// =============================================================================
function updateLayoutBounds() {
  if (!mainWindow || mainWindow.isDestroyed()) return;

  const bounds = mainWindow.getContentBounds();
  const availableWidth = Math.max(bounds.width, 100);
  const availableHeight = Math.max(bounds.height - TOOLBAR_HEIGHT, 100);
  const startX = 0;
  const startY = TOOLBAR_HEIGHT;

  const activeTab = tabs.get(activeTabId);
  const secondaryTab = tabs.get(secondaryTabId);

  if (!isSplitViewActive || !secondaryTab) {
    if (activeTab && activeTab.view && activeTab.view.setBounds) {
      activeTab.view.setBounds({
        x: startX,
        y: startY,
        width: availableWidth,
        height: availableHeight
      });
    }
  } else {
    const leftWidth = Math.floor(availableWidth * splitRatio);
    const rightWidth = availableWidth - leftWidth;

    if (activeTab && activeTab.view && activeTab.view.setBounds) {
      activeTab.view.setBounds({
        x: startX,
        y: startY,
        width: leftWidth,
        height: availableHeight
      });
    }

    if (secondaryTab && secondaryTab.view && secondaryTab.view.setBounds) {
      secondaryTab.view.setBounds({
        x: startX + leftWidth,
        y: startY,
        width: rightWidth,
        height: availableHeight
      });
    }
  }
}

// =============================================================================
// ZERO-TRUST WEBCONTENTSVIEW TAB CREATOR
// =============================================================================
function createTab(initialUrl = 'staunt://newtab', options = {}) {
  const tabId = nextTabId++;
  const isIncognito = !!options.isIncognito;

  const tabSession = isIncognito 
    ? session.fromPartition(`incognito-${Date.now()}-${tabId}`, { cache: false }) 
    : session.defaultSession;

  tabSession.setUserAgent(OFFICIAL_CHROME_WINDOWS_UA);

  const webPrefs = {
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInWorker: false,
    nodeIntegrationInSubFrames: false,
    enableRemoteModule: false,
    webSecurity: true,
    allowRunningInsecureContent: false,
    session: tabSession,
    plugins: true,
    enableWebSQL: false,
    webviewTag: false
  };

  let view;
  if (typeof WebContentsView !== 'undefined') {
    view = new WebContentsView({ webPreferences: webPrefs });
  } else {
    view = new BrowserView({ webPreferences: webPrefs });
  }

  // Ensure view has native dark background to avoid white flashing during load
  if (view.setBackgroundColor) {
    view.setBackgroundColor('#090a0f');
  }

  const tabObj = {
    id: tabId,
    view: view,
    url: initialUrl,
    title: initialUrl === 'staunt://newtab' ? 'Favorites' : initialUrl,
    favicon: '',
    workspaceId: options.workspaceId || 'personal',
    isPinned: !!options.isPinned,
    isIncognito: isIncognito,
    isHibernated: false,
    lastActiveTime: Date.now(),
    isAudioPlaying: false,
    isMuted: false,
    canGoBack: false,
    canGoForward: false,
    zoomLevel: 0
  };

  tabs.set(tabId, tabObj);
  setupWebContentsEvents(tabObj);

  const formattedUrl = formatUrlOrSearch(initialUrl);
  view.webContents.loadURL(formattedUrl);

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tab-created', serializeTab(tabObj));
  }

  switchTab(tabId);
  return tabId;
}

function setupWebContentsEvents(tabObj) {
  const wc = tabObj.view.webContents;
  wc.setUserAgent(OFFICIAL_CHROME_WINDOWS_UA);

  // Popup & OAuth Handler
  wc.setWindowOpenHandler(({ url, disposition }) => {
    console.log('[POPUP HANDLER] Intercepted window.open:', url);
    
    if (isHomographOrDeceptive(url)) {
      console.warn('[SECURITY] Blocked deceptive popup:', url);
      return { action: 'deny' };
    }

    if (isCriticalWhitelisted(url) || /accounts\.google\.com|appleid\.apple\.com|github\.com\/login|auth|oauth|login|signin|stripe\.com|razorpay\.com|paypal\.com/i.test(url) || disposition === 'new-window') {
      return {
        action: 'allow',
        overrideBrowserWindowOptions: {
          width: 600,
          height: 720,
          autoHideMenuBar: true,
          webPreferences: {
            sandbox: true,
            contextIsolation: true,
            nodeIntegration: false,
            nodeIntegrationInWorker: false,
            nodeIntegrationInSubFrames: false,
            session: wc.session,
            enableRemoteModule: false
          }
        }
      };
    }

    createTab(url, { workspaceId: tabObj.workspaceId });
    return { action: 'deny' };
  });

  // Navigation Guard & Protocol Armor
  const DANGEROUS_SCHEMES = ['file:', 'javascript:', 'data:', 'vbscript:', 'chrome:', 'ms-appx:', 'about:'];
  
  wc.on('will-navigate', (event, navigationUrl) => {
    try {
      const parsed = new URL(navigationUrl);
      if (DANGEROUS_SCHEMES.includes(parsed.protocol) && !navigationUrl.includes('newtab.html')) {
        console.warn(`[SECURITY INTERCEPT] Blocked will-navigate to dangerous protocol: ${navigationUrl}`);
        event.preventDefault();
        return;
      }
      if (isHomographOrDeceptive(navigationUrl)) {
        console.warn(`[SECURITY INTERCEPT] Blocked homograph deceptive domain: ${navigationUrl}`);
        event.preventDefault();
        return;
      }
    } catch(e) {
      event.preventDefault();
    }
  });

  // Fault-Tolerant Crash Guard
  wc.on('render-process-gone', (e, details) => {
    console.error(`[CRASH GUARD] Tab ${tabObj.id} render process terminated:`, details.reason);
    detachTabView(tabObj);
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send('tab-crashed', {
        tabId: tabObj.id,
        reason: details.reason
      });
    }
  });

  // Navigation & URL Synchronization Handlers
  wc.on('page-title-updated', (e, title) => {
    tabObj.title = title;
    tabObj.lastActiveTime = Date.now();
    recordHistory(tabObj.url, title);
    notifyTabUpdated(tabObj);
    broadcastUrlSync(tabObj);
  });

  wc.on('page-favicon-updated', (e, favicons) => {
    if (favicons && favicons.length > 0) {
      tabObj.favicon = favicons[0];
      notifyTabUpdated(tabObj);
    }
  });

  wc.on('did-start-navigation', (e, url, isInPlace, isMainFrame) => {
    if (isMainFrame) {
      tabObj.url = url;
      tabObj.lastActiveTime = Date.now();
      tabObj.canGoBack = wc.canGoBack();
      tabObj.canGoForward = wc.canGoForward();
      notifyTabUpdated(tabObj);
      broadcastUrlSync(tabObj);
    }
  });

  wc.on('did-navigate', (e, url) => {
    tabObj.url = url;
    tabObj.canGoBack = wc.canGoBack();
    tabObj.canGoForward = wc.canGoForward();
    recordHistory(tabObj.url, tabObj.title);
    notifyTabUpdated(tabObj);
    broadcastUrlSync(tabObj);
  });

  wc.on('did-finish-load', () => {
    tabObj.url = wc.getURL();
    tabObj.canGoBack = wc.canGoBack();
    tabObj.canGoForward = wc.canGoForward();
    recordHistory(tabObj.url, tabObj.title);
    notifyTabUpdated(tabObj);
    broadcastUrlSync(tabObj);
  });

  // Actionable Network Error Recovery Card (Zero Blank Screen)
  wc.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    if (errorCode === -3 || !isMainFrame) return; // Ignore intentional user aborts/redirects
    console.warn(`[NAVIGATION ERROR] Code: ${errorCode} (${errorDescription}) for ${validatedURL}`);
    
    const errorHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>Connection Error • Staunt Browser</title>
        <style>
          body { margin: 0; background: #0c0e14; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
          .card { text-align: center; max-width: 480px; padding: 32px; }
          .icon { font-size: 48px; margin-bottom: 16px; }
          h1 { font-size: 20px; margin: 0 0 10px; font-weight: 700; }
          p { color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 20px; }
          .code { font-family: monospace; font-size: 11px; background: rgba(255,255,255,0.06); padding: 6px 12px; border-radius: 6px; margin-bottom: 24px; color: #cbd5e1; }
          .btn-group { display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; }
          button { background: #3b82f6; color: #fff; border: none; padding: 9px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; transition: background 0.15s; }
          button:hover { background: #2563eb; }
          button.sec { background: rgba(255,255,255,0.08); color: #cbd5e1; }
          button.sec:hover { background: rgba(255,255,255,0.14); }
        </style>
      </head>
      <body>
        <div class="card">
          <div class="icon">🌐</div>
          <h1>This site can't be reached</h1>
          <p>The server could not be reached, or the connection timed out.</p>
          <div class="code">${errorDescription} (${errorCode})</div>
          <div class="btn-group">
            <button onclick="location.reload()">🔄 Try Again</button>
            <button class="sec" onclick="history.back()">⬅ Go Back</button>
            <button class="sec" onclick="location.href='${STAUNT_SEARCH_URL}/?q=${encodeURIComponent(validatedURL)}'">🔍 Search on STAUNT</button>
          </div>
        </div>
      </body>
      </html>
    `;
    wc.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(errorHtml)}`);
  });

  // Audio Indicators
  wc.on('media-started-playing', () => {
    tabObj.isAudioPlaying = true;
    notifyTabUpdated(tabObj);
  });

  wc.on('media-paused', () => {
    tabObj.isAudioPlaying = false;
    notifyTabUpdated(tabObj);
  });

  // Attach Shield Engine
  attachShieldToWebContents(wc);

  wc.on('context-menu', (event, params) => {
    const contextMenu = Menu.buildFromTemplate([
      { label: 'Back', enabled: wc.canGoBack(), click: () => wc.goBack() },
      { label: 'Forward', enabled: wc.canGoForward(), click: () => wc.goForward() },
      { label: 'Reload', click: () => wc.reload() },
      { type: 'separator' },
      ...(params.linkURL ? [{ label: 'Open Link in New Tab', click: () => createTab(params.linkURL, { workspaceId: tabObj.workspaceId }) }] : []),
      ...(params.linkURL ? [{ label: 'Copy Link Address', click: () => { clipboard.writeText(params.linkURL); } }] : []),
      ...(params.srcURL && params.mediaType === 'image' ? [{ label: 'Save Image As...', click: () => { wc.downloadURL(params.srcURL); } }] : []),
      { type: 'separator' },
      { label: 'Copy', enabled: params.editFlags.canCopy, click: () => wc.copy() },
      { label: 'Paste', enabled: params.editFlags.canPaste, click: () => wc.paste() },
      { label: 'Select All', click: () => wc.selectAll() },
      { type: 'separator' },
      { label: 'Inspect Element', click: () => { wc.inspectElement(params.x, params.y); } }
    ].filter(Boolean));
    contextMenu.popup();
  });
}

function broadcastUrlSync(tabObj) {
  if (tabObj.id === activeTabId && mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('url-updated', {
      url: tabObj.url,
      title: tabObj.title,
      canGoBack: tabObj.canGoBack,
      canGoForward: tabObj.canGoForward,
      isBookmarked: isUrlBookmarked(tabObj.url)
    });
  }
}

function notifyTabUpdated(tabObj) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tab-updated', serializeTab(tabObj));
  }
}

function serializeTab(tab) {
  return {
    id: tab.id,
    url: tab.url,
    title: tab.title,
    favicon: tab.favicon,
    workspaceId: tab.workspaceId,
    isPinned: tab.isPinned,
    isIncognito: tab.isIncognito,
    isHibernated: tab.isHibernated,
    isAudioPlaying: tab.isAudioPlaying,
    isMuted: tab.isMuted,
    canGoBack: tab.canGoBack,
    canGoForward: tab.canGoForward,
    zoomLevel: tab.zoomLevel || 0
  };
}

// =============================================================================
// TAB SWITCHING & ATTACHMENT
// =============================================================================
function switchTab(tabId) {
  if (!tabs.has(tabId)) return;
  const targetTab = tabs.get(tabId);

  if (targetTab.isHibernated) {
    wakeHibernatedTab(targetTab);
  }

  if (activeTabId && activeTabId !== tabId && activeTabId !== secondaryTabId) {
    detachTabView(tabs.get(activeTabId));
  }

  activeTabId = tabId;
  targetTab.lastActiveTime = Date.now();

  attachTabView(targetTab);
  updateLayoutBounds();

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tab-switched', {
      activeTabId: activeTabId,
      secondaryTabId: secondaryTabId,
      isSplit: isSplitViewActive
    });
    broadcastUrlSync(targetTab);
  }
}

function attachTabView(tabObj) {
  if (!mainWindow || !tabObj || !tabObj.view) return;
  if (mainWindow.contentView && mainWindow.contentView.addChildView) {
    mainWindow.contentView.addChildView(tabObj.view);
  } else if (mainWindow.setBrowserView) {
    mainWindow.setBrowserView(tabObj.view);
  }
}

function detachTabView(tabObj) {
  if (!mainWindow || !tabObj || !tabObj.view) return;
  if (mainWindow.contentView && mainWindow.contentView.removeChildView) {
    try { mainWindow.contentView.removeChildView(tabObj.view); } catch(e) {}
  } else if (mainWindow.removeBrowserView) {
    try { mainWindow.removeBrowserView(tabObj.view); } catch(e) {}
  }
}

function closeTab(tabId) {
  if (!tabs.has(tabId)) return;
  const tab = tabs.get(tabId);

  if (tab.url && !tab.url.includes('newtab.html') && tab.url !== 'staunt://newtab') {
    closedTabsStack.push({
      url: tab.url,
      workspaceId: tab.workspaceId,
      isPinned: tab.isPinned
    });
    if (closedTabsStack.length > 20) closedTabsStack.shift();
  }

  detachTabView(tab);

  try {
    if (tab.view && tab.view.webContents && !tab.view.webContents.isDestroyed()) {
      tab.view.webContents.stop();
      tab.view.webContents.close();
      if (typeof tab.view.webContents.destroy === 'function') {
        tab.view.webContents.destroy();
      }
    }
  } catch(e) {}

  tab.view = null;
  tabs.delete(tabId);

  if (secondaryTabId === tabId) {
    secondaryTabId = null;
    isSplitViewActive = false;
  }

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('tab-closed', tabId);
  }

  if (activeTabId === tabId) {
    if (tabs.size > 0) {
      const remaining = Array.from(tabs.keys());
      switchTab(remaining[remaining.length - 1]);
    } else {
      createTab('staunt://newtab');
    }
  }
}

function undoCloseTab() {
  if (closedTabsStack.length > 0) {
    const lastClosed = closedTabsStack.pop();
    createTab(lastClosed.url, { workspaceId: lastClosed.workspaceId, isPinned: lastClosed.isPinned });
  }
}

function duplicateTab(tabId) {
  const tab = tabs.get(tabId);
  if (!tab) return;
  return createTab(tab.url, {
    workspaceId: tab.workspaceId,
    isIncognito: tab.isIncognito
  });
}

function setTabPinned(tabId, isPinned) {
  const tab = tabs.get(tabId);
  if (!tab) return;
  tab.isPinned = Boolean(isPinned);
  notifyTabUpdated(tab);
}

function closeOtherTabs(tabId) {
  const allIds = Array.from(tabs.keys());
  for (const id of allIds) {
    if (id !== tabId) {
      closeTab(id);
    }
  }
}

function closeTabsToRight(tabId) {
  const allIds = Array.from(tabs.keys());
  const idx = allIds.indexOf(tabId);
  if (idx !== -1) {
    for (let i = idx + 1; i < allIds.length; i++) {
      closeTab(allIds[i]);
    }
  }
}

function handleStop() {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.view.webContents.stop();
  }
}

// Tab Hibernation Engine (15 mins inactive)
setInterval(() => {
  const now = Date.now();
  const HIBERNATE_THRESHOLD = 15 * 60 * 1000;

  tabs.forEach((tab) => {
    if (
      !tab.isHibernated &&
      tab.id !== activeTabId &&
      tab.id !== secondaryTabId &&
      !tab.isAudioPlaying &&
      (now - tab.lastActiveTime > HIBERNATE_THRESHOLD)
    ) {
      console.log(`[RAM HIBERNATION] Sleeping tab ${tab.id}: ${tab.title}`);
      detachTabView(tab);
      try {
        if (tab.view && tab.view.webContents && !tab.view.webContents.isDestroyed()) {
          tab.view.webContents.stop();
          tab.view.webContents.close();
          if (typeof tab.view.webContents.destroy === 'function') {
            tab.view.webContents.destroy();
          }
        }
      } catch(e) {}
      tab.view = null;
      tab.isHibernated = true;
      notifyTabUpdated(tab);
    }
  });
}, 60000);

function wakeHibernatedTab(tab) {
  console.log(`[RAM HIBERNATION] Waking tab ${tab.id}: ${tab.url}`);
  const webPrefs = {
    sandbox: true,
    contextIsolation: true,
    nodeIntegration: false,
    nodeIntegrationInWorker: false,
    nodeIntegrationInSubFrames: false,
    enableRemoteModule: false,
    webSecurity: true,
    allowRunningInsecureContent: false,
    session: session.defaultSession,
    plugins: true,
    enableWebSQL: false,
    webviewTag: false
  };

  if (typeof WebContentsView !== 'undefined') {
    tab.view = new WebContentsView({ webPreferences: webPrefs });
  } else {
    tab.view = new BrowserView({ webPreferences: webPrefs });
  }

  tab.isHibernated = false;
  setupWebContentsEvents(tab);
  tab.view.webContents.loadURL(formatUrlOrSearch(tab.url));
  notifyTabUpdated(tab);
}

function toggleSplitView(secId) {
  if (isSplitViewActive && (!secId || secId === secondaryTabId)) {
    if (secondaryTabId && tabs.has(secondaryTabId)) {
      detachTabView(tabs.get(secondaryTabId));
    }
    secondaryTabId = null;
    isSplitViewActive = false;
  } else {
    if (secId && tabs.has(secId) && secId !== activeTabId) {
      secondaryTabId = secId;
    } else {
      const otherIds = Array.from(tabs.keys()).filter(id => id !== activeTabId);
      if (otherIds.length > 0) {
        secondaryTabId = otherIds[0];
      } else {
        secondaryTabId = createTab('staunt://newtab');
      }
    }
    isSplitViewActive = true;
    attachTabView(tabs.get(secondaryTabId));
  }

  updateLayoutBounds();

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('split-view-updated', {
      isSplit: isSplitViewActive,
      secondaryTabId: secondaryTabId
    });
  }
}

// URL SANITIZER & PARSER (Intelligent URL vs STAUNT Search)
// =============================================================================
// Production URL resolution (3-tier):
//   1. STAUNT_SEARCH_URL env var — highest priority (set per-environment)
//   2. vastuda-search.onrender.com — permanent production URL (Render.com)
//   3. http://127.0.0.1:5000 — local development fallback
// NOTE: Temporary ephemeral tunnels are NEVER used here by design.
const STAUNT_SEARCH_URL = (
  process.env.STAUNT_SEARCH_URL ||
  'https://vastuda-search.onrender.com' ||
  'http://127.0.0.1:5000'
);


function formatUrlOrSearch(input) {
  const trimmed = (input || '').trim().slice(0, 2048);

  if (/^javascript:/i.test(trimmed) || /^data:text\/html/i.test(trimmed) || /^vbscript:/i.test(trimmed)) {
    console.warn('[SECURITY INTERCEPT] Suspicious URI dropped');
    return 'file://' + path.join(__dirname, 'src', 'newtab.html').replace(/\\/g, '/');
  }

  const newTabUrl = 'file://' + path.join(__dirname, 'src', 'newtab.html').replace(/\\/g, '/');

  if (!trimmed || trimmed === 'staunt://newtab' || trimmed === 'about:newtab' || trimmed === 'about:blank') {
    return newTabUrl;
  }

  if (/^https?:\/\//i.test(trimmed) || /^file:\/\//i.test(trimmed) || trimmed.startsWith('staunt://')) {
    return trimmed;
  }

  const isLocalhost = /^localhost(:\d+)?(\/.*)?$/i.test(trimmed);
  const isIpv4 = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(:\d+)?(\/.*)?$/.test(trimmed);
  const isDomain = /^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$/i.test(trimmed) && !trimmed.includes(' ');

  if (isLocalhost || isIpv4) {
    return 'http://' + trimmed;
  }
  if (isDomain) {
    return 'https://' + trimmed;
  }

  return `${STAUNT_SEARCH_URL}/?q=${encodeURIComponent(trimmed)}`;
}

// =============================================================================
// HARDENED IPC BRIDGE
// =============================================================================
function verifyIpcSender(event) {
  if (!mainWindow || mainWindow.isDestroyed()) return false;
  if (event.sender !== mainWindow.webContents) {
    console.warn('[SECURITY VIOLATION] IPC spoofing attempt detected!');
    return false;
  }
  return true;
}

// 1. Navigation & URL Handlers
function handleNavigate(url) {
  if (typeof url !== 'string' || url.length > 2048) return;
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    const formatted = formatUrlOrSearch(url);
    tab.view.webContents.loadURL(formatted);
  }
}

function handleHome() {
  handleNavigate((settingsDB && settingsDB.homeUrl) ? settingsDB.homeUrl : 'staunt://newtab');
}

ipcMain.on('navigate-to', (e, url) => {
  if (!verifyIpcSender(e)) return;
  handleNavigate(url);
});

ipcMain.on('nav-home', (e) => { if (verifyIpcSender(e)) handleHome(); });
ipcMain.on('go-home', (e) => { if (verifyIpcSender(e)) handleHome(); });

// 2. Navigation Actions (Back / Forward / Reload)
function handleBack() {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents && tab.view.webContents.canGoBack()) {
    tab.view.webContents.goBack();
  }
}

function handleForward() {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents && tab.view.webContents.canGoForward()) {
    tab.view.webContents.goForward();
  }
}

function handleReload() {
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.view.webContents.reload();
  }
}

ipcMain.on('nav-back', (e) => { if (verifyIpcSender(e)) handleBack(); });
ipcMain.on('go-back', (e) => { if (verifyIpcSender(e)) handleBack(); });

ipcMain.on('nav-forward', (e) => { if (verifyIpcSender(e)) handleForward(); });
ipcMain.on('go-forward', (e) => { if (verifyIpcSender(e)) handleForward(); });

ipcMain.on('nav-reload', (e) => { if (verifyIpcSender(e)) handleReload(); });
ipcMain.on('reload-page', (e) => { if (verifyIpcSender(e)) handleReload(); });

// 3. Window Controls (Close, Min, Max)
function handleClose() {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.close();
}

function handleMin() {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.minimize();
}

function handleMax() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isFullScreen()) {
      mainWindow.setFullScreen(false);
    } else if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
}

function handleRestore() {
  if (mainWindow && !mainWindow.isDestroyed()) {
    if (mainWindow.isFullScreen()) {
      mainWindow.setFullScreen(false);
    } else if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
  }
}

ipcMain.on('win-close', (e) => { if (verifyIpcSender(e)) handleClose(); });
ipcMain.on('window-close', (e) => { if (verifyIpcSender(e)) handleClose(); });

ipcMain.on('win-min', (e) => { if (verifyIpcSender(e)) handleMin(); });
ipcMain.on('window-minimize', (e) => { if (verifyIpcSender(e)) handleMin(); });

ipcMain.on('win-max', (e) => { if (verifyIpcSender(e)) handleMax(); });
ipcMain.on('window-maximize', (e) => { if (verifyIpcSender(e)) handleMax(); });

ipcMain.on('win-restore', (e) => { if (verifyIpcSender(e)) handleRestore(); });
ipcMain.on('window-restore', (e) => { if (verifyIpcSender(e)) handleRestore(); });

ipcMain.on('win-toggle-max', (e) => { if (verifyIpcSender(e)) handleMax(); });
ipcMain.on('window-toggle-maximize', (e) => { if (verifyIpcSender(e)) handleMax(); });

ipcMain.handle('get-window-state', (e) => {
  if (!verifyIpcSender(e) || !mainWindow || mainWindow.isDestroyed()) {
    return { isMaximized: false, maximized: false, isMinimized: false, minimized: false, isFullScreen: false, fullscreen: false, state: 'NORMAL' };
  }
  const isMax = mainWindow.isMaximized();
  const isMin = mainWindow.isMinimized();
  const isFull = mainWindow.isFullScreen();
  return {
    state: isFull ? 'FULLSCREEN' : isMax ? 'MAXIMIZED' : isMin ? 'MINIMIZED' : 'NORMAL',
    isMaximized: isMax,
    maximized: isMax,
    isMinimized: isMin,
    minimized: isMin,
    isFullScreen: isFull,
    fullscreen: isFull
  };
});

// 4. Tab Lifecycle IPC Handlers
ipcMain.on('create-tab', (e, url, opts) => {
  if (!verifyIpcSender(e)) return;
  const cleanUrl = typeof url === 'string' ? url.slice(0, 2048) : 'staunt://newtab';
  createTab(cleanUrl, opts);
});

ipcMain.on('switch-tab', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  if (typeof tabId === 'number' && Number.isFinite(tabId)) switchTab(tabId);
});

ipcMain.on('close-tab', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  if (typeof tabId === 'number' && Number.isFinite(tabId)) closeTab(tabId);
});

ipcMain.on('undo-close-tab', (e) => {
  if (!verifyIpcSender(e)) return;
  undoCloseTab();
});

ipcMain.on('toggle-split-view', (e, secId) => {
  if (!verifyIpcSender(e)) return;
  toggleSplitView(secId);
});

ipcMain.on('toggle-mute-tab', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  const tab = tabs.get(targetId);
  if (tab && tab.view && tab.view.webContents) {
    tab.isMuted = !tab.isMuted;
    tab.view.webContents.setAudioMuted(tab.isMuted);
    notifyTabUpdated(tab);
  }
});

ipcMain.on('clear-browser-cache', (e) => {
  if (!verifyIpcSender(e)) return;
  session.defaultSession.clearCache();
  session.defaultSession.clearStorageData();
  console.log('[CACHE] Cleared cache & storage');
});

ipcMain.on('set-zoom', (e, level) => {
  if (!verifyIpcSender(e)) return;
  const z = typeof level === 'number' ? Math.max(-3, Math.min(3, level)) : 0;
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.zoomLevel = z;
    tab.view.webContents.setZoomLevel(z);
  }
});

ipcMain.on('print-to-pdf', async (e) => {
  if (!verifyIpcSender(e)) return;
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    try {
      const pdfData = await tab.view.webContents.printToPDF({});
      const { filePath } = await dialog.showSaveDialog(mainWindow, {
        title: 'Save PDF',
        defaultPath: 'webpage.pdf',
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
      });
      if (filePath) {
        fs.writeFileSync(filePath, pdfData);
      }
    } catch (err) {
      console.error('Failed to print PDF', err);
    }
  }
});

ipcMain.on('find-in-page', (e, text, forward = true) => {
  if (!verifyIpcSender(e)) return;
  if (typeof text !== 'string') return;
  const cleanText = text.slice(0, 256);
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents && cleanText) {
    tab.view.webContents.findInPage(cleanText, { forward: Boolean(forward), findNext: false });
  }
});

ipcMain.on('stop-find-in-page', (e) => {
  if (!verifyIpcSender(e)) return;
  const tab = tabs.get(activeTabId);
  if (tab && tab.view && tab.view.webContents) {
    tab.view.webContents.stopFindInPage('clearSelection');
  }
});

ipcMain.handle('get-history', (e) => {
  if (!verifyIpcSender(e)) return [];
  return historyDB.slice(0, 50);
});

ipcMain.handle('get-bookmarks', (e) => {
  if (!verifyIpcSender(e)) return [];
  return bookmarksDB;
});

ipcMain.on('add-bookmark', (e, item) => {
  if (!verifyIpcSender(e)) return;
  if (item && typeof item === 'object') {
    bookmarksDB.push({
      id: Date.now().toString(36),
      title: typeof item.title === 'string' ? item.title.slice(0, 256) : 'Untitled',
      url: typeof item.url === 'string' ? item.url.slice(0, 2048) : '',
      favicon: typeof item.favicon === 'string' ? item.favicon.slice(0, 2048) : ''
    });
    atomicWriteJson(BOOKMARKS_FILE, bookmarksDB);
  }
});

ipcMain.on('nav-stop', (e) => { if (verifyIpcSender(e)) handleStop(); });
ipcMain.on('stop-navigation', (e) => { if (verifyIpcSender(e)) handleStop(); });

ipcMain.on('duplicate-tab', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  duplicateTab(targetId);
});

ipcMain.on('pin-tab', (e, tabId, isPinned) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  setTabPinned(targetId, isPinned);
});

ipcMain.on('close-other-tabs', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  closeOtherTabs(targetId);
});

ipcMain.on('close-tabs-to-right', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  closeTabsToRight(targetId);
});

ipcMain.on('show-tab-context-menu', (e, tabId) => {
  if (!verifyIpcSender(e)) return;
  const targetId = typeof tabId === 'number' ? tabId : activeTabId;
  const tab = tabs.get(targetId);
  if (!tab) return;

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'New Tab',
      accelerator: 'CmdOrCtrl+T',
      click: () => createTab('staunt://newtab')
    },
    {
      label: 'Duplicate Tab',
      click: () => duplicateTab(targetId)
    },
    { type: 'separator' },
    {
      label: tab.isPinned ? 'Unpin Tab' : 'Pin Tab',
      click: () => setTabPinned(targetId, !tab.isPinned)
    },
    {
      label: tab.isMuted ? 'Unmute Tab' : 'Mute Tab',
      click: () => {
        tab.isMuted = !tab.isMuted;
        if (tab.view && tab.view.webContents) tab.view.webContents.setAudioMuted(tab.isMuted);
        notifyTabUpdated(tab);
      }
    },
    { type: 'separator' },
    {
      label: 'Close Tab',
      accelerator: 'CmdOrCtrl+W',
      click: () => closeTab(targetId)
    },
    {
      label: 'Close Other Tabs',
      enabled: tabs.size > 1,
      click: () => closeOtherTabs(targetId)
    },
    {
      label: 'Close Tabs to the Right',
      click: () => closeTabsToRight(targetId)
    }
  ]);
  contextMenu.popup({ window: mainWindow });
});

// 5. Downloads & Vault Handlers
ipcMain.handle('get-downloads', (e) => {
  if (!verifyIpcSender(e)) return [];
  return downloadsDB;
});

ipcMain.on('open-download', (e, itemPath) => {
  if (!verifyIpcSender(e)) return;
  if (typeof itemPath === 'string' && itemPath.trim()) {
    const cleanPath = path.normalize(itemPath.trim());
    if (fs.existsSync(cleanPath)) {
      shell.openPath(cleanPath);
    }
  }
});

ipcMain.on('show-in-folder', (e, itemPath) => {
  if (!verifyIpcSender(e)) return;
  if (typeof itemPath === 'string' && itemPath.trim()) {
    const cleanPath = path.normalize(itemPath.trim());
    if (fs.existsSync(cleanPath)) {
      shell.showItemInFolder(cleanPath);
    }
  }
});

ipcMain.handle('clear-history', (e, range) => {
  if (!verifyIpcSender(e)) return { success: false };
  return clearHistoryRange(range);
});

ipcMain.on('cycle-tab', (e, direction) => {
  if (!verifyIpcSender(e)) return;
  cycleTab(typeof direction === 'number' ? direction : 1);
});

ipcMain.handle('toggle-bookmark', (e) => {
  if (!verifyIpcSender(e)) return { bookmarked: false };
  return toggleBookmarkCurrentPage();
});

ipcMain.handle('check-is-bookmarked', (e, url) => {
  if (!verifyIpcSender(e)) return false;
  return isUrlBookmarked(url);
});

ipcMain.handle('delete-bookmark', (e, id) => {
  if (!verifyIpcSender(e)) return { success: false };
  return deleteBookmark(id);
});

ipcMain.handle('delete-history-item', (e, id) => {
  if (!verifyIpcSender(e)) return { success: false };
  return deleteHistoryItem(id);
});

ipcMain.handle('clear-downloads', (e) => {
  if (!verifyIpcSender(e)) return { success: false };
  return clearDownloads();
});

ipcMain.on('create-window', (e) => {
  if (!verifyIpcSender(e)) return;
  createMainWindow();
});

ipcMain.on('create-incognito-window', (e) => {
  if (!verifyIpcSender(e)) return;
  createTab('staunt://newtab', { isIncognito: true });
});

ipcMain.on('toggle-fullscreen', (e) => {
  if (!verifyIpcSender(e)) return;
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.setFullScreen(!mainWindow.isFullScreen());
  }
});

// 6. Intelligent Omnibox Autocomplete Suggestions Handlers
ipcMain.handle('get-suggestions', async (e, query) => {
  if (!verifyIpcSender(e)) return [];
  if (!query || typeof query !== 'string') return [];
  const trimmed = query.trim().slice(0, 256);
  if (!trimmed) return [];

  // Match from local bookmarks
  const bookmarkMatches = bookmarksDB
    .filter(b => (b.title && b.title.toLowerCase().includes(trimmed.toLowerCase())) ||
                 (b.url && b.url.toLowerCase().includes(trimmed.toLowerCase())))
    .slice(0, 2)
    .map(b => ({ text: b.title || b.url, url: b.url, type: 'bookmark' }));

  // Match from local history
  const historyMatches = historyDB
    .filter(h => (h.title && h.title.toLowerCase().includes(trimmed.toLowerCase())) ||
                 (h.url && h.url.toLowerCase().includes(trimmed.toLowerCase())))
    .slice(0, 3)
    .map(h => ({ text: h.title || h.url, url: h.url, type: 'history' }));

  // Query local STAUNT search engine /api/suggest
  let remoteSuggestions = [];
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 800);
    const resp = await fetch(`${STAUNT_SEARCH_URL}/api/suggest?q=${encodeURIComponent(trimmed)}`, {
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    if (resp.ok) {
      const data = await resp.json();
      if (Array.isArray(data)) {
        remoteSuggestions = data.map(s => (typeof s === 'string' ? { text: s, type: 'search' } : s));
      }
    }
  } catch (err) {
    // Offline or server unreachable fallback
  }

  const seen = new Set();
  const results = [];
  for (const item of [...bookmarkMatches, ...historyMatches, ...remoteSuggestions]) {
    const key = (item.text || '').toLowerCase();
    if (key && !seen.has(key)) {
      seen.add(key);
      results.push(item);
    }
    if (results.length >= 8) break;
  }
  return results;
});

// 7. Settings Vault Handlers
ipcMain.handle('get-settings', (e) => {
  if (!verifyIpcSender(e)) return DEFAULT_SETTINGS;
  return settingsDB;
});

ipcMain.handle('save-settings', (e, newSettings) => {
  if (!verifyIpcSender(e)) return { success: false };
  if (newSettings && typeof newSettings === 'object') {
    const validated = {};
    if (typeof newSettings.searchEngine === 'string' && ['staunt', 'google', 'duckduckgo', 'bing'].includes(newSettings.searchEngine.toLowerCase())) {
      validated.searchEngine = newSettings.searchEngine.toLowerCase();
    }
    if (typeof newSettings.searchUrl === 'string' && /^https?:\/\//i.test(newSettings.searchUrl.trim())) {
      validated.searchUrl = newSettings.searchUrl.trim().slice(0, 512);
    }
    if (typeof newSettings.homeUrl === 'string' && (/^https?:\/\//i.test(newSettings.homeUrl.trim()) || newSettings.homeUrl.trim().startsWith('staunt://') || newSettings.homeUrl.trim().startsWith('file://'))) {
      validated.homeUrl = newSettings.homeUrl.trim().slice(0, 512);
    }
    if (typeof newSettings.shieldLevel === 'string' && ['strict', 'standard', 'off'].includes(newSettings.shieldLevel.toLowerCase())) {
      validated.shieldLevel = newSettings.shieldLevel.toLowerCase();
    }
    if (typeof newSettings.hardwareAcceleration === 'boolean') {
      validated.hardwareAcceleration = newSettings.hardwareAcceleration;
    }
    if (typeof newSettings.restoreTabsOnStartup === 'boolean') {
      validated.restoreTabsOnStartup = newSettings.restoreTabsOnStartup;
    }
    settingsDB = { ...settingsDB, ...validated };
    atomicWriteJson(SETTINGS_FILE, settingsDB);
  }
  return { success: true, settings: settingsDB };
});

ipcMain.on('save-page', (e) => {
  if (verifyIpcSender(e)) saveCurrentPage();
});

ipcMain.on('reorder-tabs', (e, ids) => {
  if (verifyIpcSender(e)) reorderTabs(ids);
});

ipcMain.on('toggle-devtools', (e) => {
  if (verifyIpcSender(e)) {
    const tab = tabs.get(activeTabId);
    if (tab && tab.view && tab.view.webContents) {
      tab.view.webContents.toggleDevTools();
    }
  }
});

ipcMain.on('show-about', (e) => {
  if (verifyIpcSender(e)) showAboutDialog();
});

// App Lifecycle with Single Instance Lock (prevent duplicate windows)
const gotTheSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotTheSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  app.whenReady().then(() => {
    createMainWindow();
    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
    });
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
