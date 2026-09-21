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

  duplicateTab: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('duplicate-tab', id);
  },

  pinTab: (tabId, isPinned) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('pin-tab', id, Boolean(isPinned));
  },

  closeOtherTabs: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('close-other-tabs', id);
  },

  closeTabsToRight: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('close-tabs-to-right', id);
  },

  showTabContextMenu: (tabId) => {
    const id = sanitizeNumber(tabId, -1);
    if (id > 0) ipcRenderer.send('show-tab-context-menu', id);
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
  stopNavigation: () => ipcRenderer.send('nav-stop'),
  goHome: () => ipcRenderer.send('nav-home'),

  // Autocomplete Suggestions API
  getSuggestions: (query) => {
    return ipcRenderer.invoke('get-suggestions', sanitizeString(query, 256));
  },

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

  savePage: () => {
    ipcRenderer.send('save-page');
  },

  // Tab Cycling & Reorder API
  cycleTab: (direction = 1) => {
    ipcRenderer.send('cycle-tab', sanitizeNumber(direction, 1));
  },

  reorderTabs: (ids) => {
    if (Array.isArray(ids)) {
      ipcRenderer.send('reorder-tabs', ids.map(id => sanitizeNumber(id, 0)).filter(id => id > 0));
    }
  },

  // History & Bookmarks Query API
  getHistory: () => ipcRenderer.invoke('get-history'),
  clearHistory: (range) => ipcRenderer.invoke('clear-history', sanitizeString(range, 64)),
  deleteHistoryItem: (id) => ipcRenderer.invoke('delete-history-item', sanitizeString(id, 64)),
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
  toggleBookmark: () => ipcRenderer.invoke('toggle-bookmark'),
  checkIsBookmarked: (url) => ipcRenderer.invoke('check-is-bookmarked', sanitizeString(url, 2048)),
  deleteBookmark: (id) => ipcRenderer.invoke('delete-bookmark', sanitizeString(id, 64)),

  // Downloads Vault API
  getDownloads: () => ipcRenderer.invoke('get-downloads'),
  openDownload: (itemPath) => {
    const p = sanitizeString(itemPath, 4096);
    if (p) ipcRenderer.send('open-download', p);
  },
  showInFolder: (itemPath) => {
    const p = sanitizeString(itemPath, 4096);
    if (p) ipcRenderer.send('show-in-folder', p);
  },
  clearDownloads: () => ipcRenderer.invoke('clear-downloads'),

  // Settings API
  getSettings: () => ipcRenderer.invoke('get-settings'),
  saveSettings: (settings) => ipcRenderer.invoke('save-settings', settings),

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

  showAbout: () => {
    ipcRenderer.send('show-about');
  },

  // Native Window Controls (Supports both win-* and window-* aliases)
  minimizeWindow: () => ipcRenderer.send('win-min'),
  maximizeWindow: () => ipcRenderer.send('win-max'),
  restoreWindow: () => ipcRenderer.send('win-restore'),
  toggleMaximize: () => ipcRenderer.send('window-toggle-maximize'),
  closeWindow: () => ipcRenderer.send('win-close'),
  createWindow: () => ipcRenderer.send('create-window'),
  createIncognitoWindow: () => ipcRenderer.send('create-incognito-window'),
  toggleFullscreen: () => ipcRenderer.send('toggle-fullscreen'),
  getWindowState: () => ipcRenderer.invoke('get-window-state'),

  // Safe Parameterized Inbound Listeners
  onWindowStateChanged: (cb) => { if (typeof cb === 'function') ipcRenderer.on('window-state-changed', (e, d) => cb(d)); },
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
  onDownloadComplete: (cb) => { if (typeof cb === 'function') ipcRenderer.on('download-complete', (e, d) => cb(d)); },
  onBookmarkStatusChanged: (cb) => { if (typeof cb === 'function') ipcRenderer.on('bookmark-status-changed', (e, d) => cb(d)); },
  onShowBookmarks: (cb) => { if (typeof cb === 'function') ipcRenderer.on('show-bookmarks', () => cb()); },
  onToggleFindBar: (cb) => { if (typeof cb === 'function') ipcRenderer.on('toggle-find-bar', () => cb()); }
});

// Expose both namespaces (stauntAPI & stauntSecureBridge)
contextBridge.exposeInMainWorld('stauntAPI', secureAPI);
contextBridge.exposeInMainWorld('stauntSecureBridge', secureAPI);
