// Staunt Browser Ultra — Hardened Sandboxed IPC Preload Bridge
// Strict Defense-in-Depth: Zero direct ipcRenderer exposure, parameter validation, & Object.freeze
const { contextBridge, ipcRenderer } = require('electron');

// Type Validation Helpers
function sanitizeString(val, maxLen = 4096) {
  if (typeof val !== 'string') return '';
  return val.trim().slice(0, maxLen);
}

function sanitizeNumber(val, fallback = 0) {
  const n = Number(val);
  return Number.isFinite(n) ? n : fallback;
}

const secureAPI = Object.freeze({
  // Tabs Lifecycle API
  createTab: (url, opts) => {
    const cleanUrl = sanitizeString(url, 2048) || 'staunt://newtab';
    const cleanOpts = opts && typeof opts === 'object' ? {
      isIncognito: Boolean(opts.isIncognito),
      workspaceId: sanitizeString(opts.workspaceId, 64) || 'personal',
      isPinned: Boolean(opts.isPinned)
    } : {};
    ipcRenderer.send('create-tab', cleanUrl, cleanOpts);
  },

  switchTab: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('switch-tab', id);
  },

  closeTab: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('close-tab', id);
  },

  undoCloseTab: () => {
    ipcRenderer.send('undo-close-tab');
  },

  toggleSplitView: (secId) => {
    const id = secId ? sanitizeNumber(secId, null) : null;
    ipcRenderer.send('toggle-split-view', id);
  },

  toggleMuteTab: (tabId) => {
    const id = tabId ? sanitizeNumber(tabId, null) : null;
    ipcRenderer.send('toggle-mute-tab', id);
  },

  // Navigation API (Supports both navigate-to and direct nav verbs)
  navigate: (url) => {
    const cleanUrl = sanitizeString(url, 2048);
    if (cleanUrl) ipcRenderer.send('navigate-to', cleanUrl);
  },
  navigateTo: (url) => {
    const cleanUrl = sanitizeString(url, 2048);
    if (cleanUrl) ipcRenderer.send('navigate-to', cleanUrl);
  },

  goBack: () => ipcRenderer.send('nav-back'),
  goForward: () => ipcRenderer.send('nav-forward'),
  reload: () => ipcRenderer.send('nav-reload'),

  // Find In Page API
  findInPage: (text, forward = true) => {
    const cleanText = sanitizeString(text, 256);
    if (cleanText) ipcRenderer.send('find-in-page', cleanText, Boolean(forward));
  },

  stopFindInPage: () => {
    ipcRenderer.send('stop-find-in-page');
  },

  // Zoom & PDF Exporter
  setZoom: (level) => {
    const z = Math.max(-3, Math.min(3, sanitizeNumber(level, 0)));
    ipcRenderer.send('set-zoom', z);
  },

  printToPDF: () => {
    ipcRenderer.send('print-to-pdf');
  },

  // History & Bookmarks Query API
  getHistory: () => ipcRenderer.invoke('get-history'),
  getBookmarks: () => ipcRenderer.invoke('get-bookmarks'),
  addBookmark: (item) => {
    if (item && typeof item === 'object') {
      ipcRenderer.send('add-bookmark', {
        title: sanitizeString(item.title, 256),
        url: sanitizeString(item.url, 2048),
        favicon: sanitizeString(item.favicon, 2048)
      });
    }
  },

  // Layout & Shell State
  setSidebarState: (isCollapsed) => {
    ipcRenderer.send('set-sidebar-state', Boolean(isCollapsed));
  },

  clearCache: () => {
    ipcRenderer.send('clear-browser-cache');
  },

  toggleDevTools: () => {
    ipcRenderer.send('toggle-devtools');
  },

  // Native Window Controls (Supports both win-* and window-* aliases)
  minimizeWindow: () => ipcRenderer.send('win-min'),
  maximizeWindow: () => ipcRenderer.send('win-max'),
  closeWindow: () => ipcRenderer.send('win-close'),

  // Safe Parameterized Inbound Listeners
  onUrlUpdated: (cb) => { if (typeof cb === 'function') ipcRenderer.on('url-updated', (e, d) => cb(d)); },
  onTabCreated: (cb) => { if (typeof cb === 'function') ipcRenderer.on('tab-created', (e, d) => cb(d)); },
  onTabUpdated: (cb) => { if (typeof cb === 'function') ipcRenderer.on('tab-updated', (e, d) => cb(d)); },
  onTabClosed: (cb) => { if (typeof cb === 'function') ipcRenderer.on('tab-closed', (e, d) => cb(d)); },
  onTabSwitched: (cb) => { if (typeof cb === 'function') ipcRenderer.on('tab-switched', (e, d) => cb(d)); },
  onTabCrashed: (cb) => { if (typeof cb === 'function') ipcRenderer.on('tab-crashed', (e, d) => cb(d)); },
  onSplitViewUpdated: (cb) => { if (typeof cb === 'function') ipcRenderer.on('split-view-updated', (e, d) => cb(d)); },
  onShieldUpdated: (cb) => { if (typeof cb === 'function') ipcRenderer.on('shield-updated', (e, d) => cb(d)); },
  onPermissionRequested: (cb) => { if (typeof cb === 'function') ipcRenderer.on('permission-requested', (e, d) => cb(d)); },
  onFindResult: (cb) => { if (typeof cb === 'function') ipcRenderer.on('find-result', (e, d) => cb(d)); },
  onDownloadProgress: (cb) => { if (typeof cb === 'function') ipcRenderer.on('download-progress', (e, d) => cb(d)); },
  onDownloadComplete: (cb) => { if (typeof cb === 'function') ipcRenderer.on('download-complete', (e, d) => cb(d)); }
});

// Expose both namespaces (stauntAPI & stauntSecureBridge)
contextBridge.exposeInMainWorld('stauntAPI', secureAPI);
contextBridge.exposeInMainWorld('stauntSecureBridge', secureAPI);
