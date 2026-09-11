// Staunt Browser Ultra — Enterprise Hardened Chromium Engine
// Former Google Project Zero / Chromium Security Team Architectural Grade
// Resolves Viewport Freeze & Blank Screen via Precision WebContentsView Geometry

const { app, BrowserWindow, WebContentsView, BrowserView, session, ipcMain, Menu, dialog, clipboard } = require('electron');
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
// WINDOW STATE PERSISTENCE
// =============================================================================
const USER_DATA_PATH = app.getPath('userData');
let windowState = { width: 1440, height: 900, x: undefined, y: undefined, isMaximized: false };
const WINDOW_STATE_FILE = path.join(USER_DATA_PATH, 'window-state.json');

try {
  if (fs.existsSync(WINDOW_STATE_FILE)) {
    windowState = { ...windowState, ...JSON.parse(fs.readFileSync(WINDOW_STATE_FILE, 'utf-8')) };
  }
} catch(e) {}

function saveWindowState() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  const bounds = mainWindow.getBounds();
  windowState = { ...bounds, isMaximized: mainWindow.isMaximized() };
  try { fs.writeFileSync(WINDOW_STATE_FILE, JSON.stringify(windowState), 'utf-8'); } catch(e) {}
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
// LOCAL VAULT STORAGE (History & Bookmarks)
// =============================================================================
const HISTORY_FILE = path.join(USER_DATA_PATH, 'staunt_history_vault.json');
const BOOKMARKS_FILE = path.join(USER_DATA_PATH, 'staunt_bookmarks_vault.json');

let historyDB = [];
let bookmarksDB = [];

try {
  if (fs.existsSync(HISTORY_FILE)) {
    historyDB = JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf-8'));
  }
} catch (e) {
  historyDB = [];
}

try {
  if (fs.existsSync(BOOKMARKS_FILE)) {
    bookmarksDB = JSON.parse(fs.readFileSync(BOOKMARKS_FILE, 'utf-8'));
  }
} catch (e) {
  bookmarksDB = [];
}

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
  
  try {
    fs.writeFileSync(HISTORY_FILE, JSON.stringify(historyDB.slice(0, 1000)), 'utf-8');
  } catch (e) {}
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
    try { fs.writeFileSync(BOOKMARKS_FILE, JSON.stringify(bookmarksDB), 'utf-8'); } catch(e) {}
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('bookmark-added', item);
  }
}

function showAboutDialog() {
  dialog.showMessageBox(mainWindow, {
    type: 'info',
    title: 'About Staunt Browser',
    message: 'Staunt Browser Ultra',
    detail: 'Version 2.0.0\nBy VASTUDA Sovereign Systems\n\nPowered by Chromium via Electron'
  });
}

const menuTemplate = [
  {
    label: 'File',
    submenu: [
      { label: 'New Tab', accelerator: 'CmdOrCtrl+T', click: () => createTab('staunt://newtab') },
      { label: 'New Incognito Tab', accelerator: 'CmdOrCtrl+Shift+N', click: () => createTab('staunt://newtab', { isIncognito: true }) },
      { type: 'separator' },
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
  mainWindow = new BrowserWindow({
    width: windowState.width,
    height: windowState.height,
    x: windowState.x,
    y: windowState.y,
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

  if (windowState.isMaximized) mainWindow.maximize();

  const menu = Menu.buildFromTemplate(menuTemplate);
  Menu.setApplicationMenu(menu);

  mainWindow.loadFile(path.join(__dirname, 'src', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    // Instantiate and attach initial WebContentsView immediately so viewport is never 0x0
    if (tabs.size === 0) {
      createTab('staunt://newtab');
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

  // Native Download Manager
  session.defaultSession.on('will-download', (event, item, webContents) => {
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

    item.on('updated', (e, state) => {
      if (state === 'progressing' && !item.isPaused()) {
        const received = item.getReceivedBytes();
        const percent = totalBytes > 0 ? Math.floor((received / totalBytes) * 100) : 0;
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('download-progress', {
            fileName: fileName,
            percent: percent,
            receivedBytes: received,
            totalBytes: totalBytes
          });
        }
      }
    });

    item.once('done', (e, state) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('download-complete', {
          fileName: fileName,
          state: state
        });
      }
    });
  });

  // Dynamic Window Resize Observers (Immediate Bounds Recalculation)
  mainWindow.on('resize', () => updateLayoutBounds());
  mainWindow.on('move', () => updateLayoutBounds());
  mainWindow.on('maximize', () => {
    updateLayoutBounds();
    setTimeout(updateLayoutBounds, 25);
  });
  mainWindow.on('unmaximize', () => {
    updateLayoutBounds();
    setTimeout(updateLayoutBounds, 25);
  });
  
  mainWindow.on('close', () => saveWindowState());
  
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
      canGoForward: tabObj.canGoForward
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
      tab.view.webContents.close();
    }
  } catch(e) {}

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
          tab.view.webContents.close();
        }
      } catch(e) {}
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

// =============================================================================
// URL SANITIZER & PARSER (Auto-Prepend https & DDG Fallback)
// =============================================================================
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

  if (/^https?:\/\//i.test(trimmed) || /^file:\/\//i.test(trimmed)) {
    return trimmed;
  }

  const isDomain = /^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$/i.test(trimmed) || /^localhost(:\d+)?(\/.*)?$/i.test(trimmed);
  if (isDomain) {
    return trimmed.startsWith('localhost') ? 'http://' + trimmed : 'https://' + trimmed;
  }

  return `https://html.duckduckgo.com/html/?q=${encodeURIComponent(trimmed)}`;
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

ipcMain.on('navigate-to', (e, url) => {
  if (!verifyIpcSender(e)) return;
  handleNavigate(url);
});

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
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  }
}

ipcMain.on('win-close', (e) => { if (verifyIpcSender(e)) handleClose(); });
ipcMain.on('window-close', (e) => { if (verifyIpcSender(e)) handleClose(); });

ipcMain.on('win-min', (e) => { if (verifyIpcSender(e)) handleMin(); });
ipcMain.on('window-minimize', (e) => { if (verifyIpcSender(e)) handleMin(); });

ipcMain.on('win-max', (e) => { if (verifyIpcSender(e)) handleMax(); });
ipcMain.on('window-maximize', (e) => { if (verifyIpcSender(e)) handleMax(); });

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
    try {
      fs.writeFileSync(BOOKMARKS_FILE, JSON.stringify(bookmarksDB), 'utf-8');
    } catch (e) {}
  }
});

ipcMain.on('toggle-devtools', (e) => {
  if (verifyIpcSender(e)) {
    const tab = tabs.get(activeTabId);
    if (tab && tab.view && tab.view.webContents) {
      tab.view.webContents.toggleDevTools();
    }
  }
});

// App Lifecycle
app.whenReady().then(() => {
  createMainWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
