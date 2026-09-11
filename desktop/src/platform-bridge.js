/**
 * Staunt Core — Universal Platform Abstraction Bridge (v2.0 Enterprise)
 * Provides transparent, unified native bridge across:
 * - Desktop: Electron 33+ (Chromium) / Tauri v2 (WebView2 / WebKit)
 * - iOS: Swift Native WKWebView (window.webkit.messageHandlers)
 * - Android: Kotlin Native WebView (window.AndroidBridge)
 * - Web/PWA: Fallback sandbox with tab state synchronization
 */

(function(global) {
  'use strict';

  // 1. Runtime Detection
  const isElectron = Boolean(window.stauntSecureBridge || window.stauntAPI || (window.process && window.process.type));
  const isTauri = Boolean(window.__TAURI__ || window.__TAURI_INTERNALS__);
  const isIOS = Boolean(window.webkit && window.webkit.messageHandlers && window.webkit.messageHandlers.stauntIOS);
  const isAndroid = Boolean(window.AndroidBridge && typeof window.AndroidBridge.postMessage === 'function');
  const isMobileViewport = () => window.innerWidth <= 768 || ('ontouchstart' in window && window.innerWidth <= 1024);

  // In-memory fallback tab state for Web / PWA / Mobile wrapper mode
  let localTabs = new Map();
  let activeTabId = 1;
  let nextId = 2;
  const subscribers = {
    tabCreated: [],
    tabUpdated: [],
    tabClosed: [],
    tabSwitched: [],
    findResult: []
  };

  // Seed default tab if standalone web
  if (!isElectron) {
    localTabs.set(1, {
      id: 1,
      url: 'staunt://newtab',
      title: 'Favorites',
      favicon: '',
      canGoBack: false,
      canGoForward: false,
      isAudioPlaying: false,
      isMuted: false
    });
  }

  // 2. Anonymized Search Sanitizer (DuckDuckGo Lite / Brave Zero-Telemetry)
  function formatCleanSearch(input) {
    const trimmed = (input || '').trim();
    if (!trimmed || trimmed === 'staunt://newtab' || trimmed === 'about:blank') {
      return 'staunt://newtab';
    }

    if (/^https?:\/\//i.test(trimmed)) {
      return trimmed;
    }

    const isDomain = /^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$/i.test(trimmed) || /^localhost(:\d+)?/i.test(trimmed);
    if (isDomain) {
      return 'https://' + trimmed;
    }

    // Zero-telemetry query forwarder (DuckDuckGo Lite parameter-stripped)
    return `https://html.duckduckgo.com/html/?q=${encodeURIComponent(trimmed)}`;
  }

  // 3. Platform Unified Methods
  const Bridge = {
    getPlatform() {
      if (isElectron) return 'electron';
      if (isTauri) return 'tauri';
      if (isIOS) return 'ios';
      if (isAndroid) return 'android';
      return 'web';
    },

    isMobile() {
      return isMobileViewport();
    },

    // Navigation Commands
    navigate(rawUrl) {
      const url = formatCleanSearch(rawUrl);
      
      if (isElectron && (window.stauntSecureBridge || window.stauntAPI)) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.navigate(url);
      }

      if (isTauri && window.__TAURI__?.invoke) {
        return window.__TAURI__.invoke('navigate', { url });
      }

      if (isIOS) {
        window.webkit.messageHandlers.stauntIOS.postMessage({ action: 'navigate', url });
        return;
      }

      if (isAndroid) {
        window.AndroidBridge.postMessage(JSON.stringify({ action: 'navigate', url }));
        return;
      }

      // Web/Iframe Fallback
      const cur = localTabs.get(activeTabId);
      if (cur) {
        cur.url = url;
        cur.title = url.startsWith('http') ? new URL(url).hostname : url;
        cur.canGoBack = true;
        this._emit('tabUpdated', cur);
      }
      
      const frame = document.getElementById('webHostFrame');
      if (frame) {
        if (url === 'staunt://newtab') {
          frame.src = 'newtab.html';
        } else {
          // In web preview, route through safe webview/proxy if available or direct URL
          frame.src = url;
        }
      }
    },

    goBack() {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.goBack();
      }
      if (isTauri) return window.__TAURI__.invoke('go_back');
      if (isIOS) return window.webkit.messageHandlers.stauntIOS.postMessage({ action: 'goBack' });
      if (isAndroid) return window.AndroidBridge.postMessage(JSON.stringify({ action: 'goBack' }));

      const frame = document.getElementById('webHostFrame');
      if (frame && frame.contentWindow) {
        try { frame.contentWindow.history.back(); } catch(e) {}
      }
    },

    goForward() {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.goForward();
      }
      if (isTauri) return window.__TAURI__.invoke('go_forward');
      if (isIOS) return window.webkit.messageHandlers.stauntIOS.postMessage({ action: 'goForward' });
      if (isAndroid) return window.AndroidBridge.postMessage(JSON.stringify({ action: 'goForward' }));

      const frame = document.getElementById('webHostFrame');
      if (frame && frame.contentWindow) {
        try { frame.contentWindow.history.forward(); } catch(e) {}
      }
    },

    reload() {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.reload();
      }
      if (isTauri) return window.__TAURI__.invoke('reload');
      if (isIOS) return window.webkit.messageHandlers.stauntIOS.postMessage({ action: 'reload' });
      if (isAndroid) return window.AndroidBridge.postMessage(JSON.stringify({ action: 'reload' }));

      const frame = document.getElementById('webHostFrame');
      if (frame) {
        frame.src = frame.src;
      }
    },

    // Tab Management
    createTab(url = 'staunt://newtab', options = {}) {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.createTab(url, options);
      }
      if (isTauri) return window.__TAURI__.invoke('create_tab', { url, options });

      const newId = nextId++;
      const tab = {
        id: newId,
        url: url,
        title: url === 'staunt://newtab' ? 'Favorites' : url,
        favicon: '',
        canGoBack: false,
        canGoForward: false,
        isAudioPlaying: false,
        isMuted: false
      };
      localTabs.set(newId, tab);
      this._emit('tabCreated', tab);
      this.switchTab(newId);
      return newId;
    },

    closeTab(tabId) {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.closeTab(tabId);
      }
      if (isTauri) return window.__TAURI__.invoke('close_tab', { tabId });

      localTabs.delete(tabId);
      this._emit('tabClosed', tabId);

      if (activeTabId === tabId) {
        const remaining = Array.from(localTabs.keys());
        if (remaining.length > 0) {
          this.switchTab(remaining[remaining.length - 1]);
        } else {
          this.createTab('staunt://newtab');
        }
      }
    },

    switchTab(tabId) {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.switchTab(tabId);
      }
      if (isTauri) return window.__TAURI__.invoke('switch_tab', { tabId });

      if (localTabs.has(tabId)) {
        activeTabId = tabId;
        const cur = localTabs.get(tabId);
        this._emit('tabSwitched', { activeTabId: tabId, secondaryTabId: null, isSplit: false });
        
        const frame = document.getElementById('webHostFrame');
        if (frame) {
          frame.src = cur.url === 'staunt://newtab' ? 'newtab.html' : cur.url;
        }
      }
    },

    getTabs() {
      if (isElectron) {
        // Handled via IPC events
        return localTabs;
      }
      return localTabs;
    },

    undoCloseTab() {
      if (isElectron) {
        const api = window.stauntSecureBridge || window.stauntAPI;
        return api.undoCloseTab();
      }
    },

    // Window Controls
    closeWindow() {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).closeWindow();
      if (isTauri) return window.__TAURI__.window.appWindow.close();
      window.close();
    },

    minimizeWindow() {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).minimizeWindow();
      if (isTauri) return window.__TAURI__.window.appWindow.minimize();
    },

    maximizeWindow() {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).maximizeWindow();
      if (isTauri) return window.__TAURI__.window.appWindow.toggleMaximize();
    },

    // Event Subscriptions
    onTabCreated(cb) {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).onTabCreated(cb);
      subscribers.tabCreated.push(cb);
    },

    onTabUpdated(cb) {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).onTabUpdated(cb);
      subscribers.tabUpdated.push(cb);
    },

    onTabClosed(cb) {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).onTabClosed(cb);
      subscribers.tabClosed.push(cb);
    },

    onTabSwitched(cb) {
      if (isElectron) return (window.stauntSecureBridge || window.stauntAPI).onTabSwitched(cb);
      subscribers.tabSwitched.push(cb);
    },

    _emit(event, data) {
      if (subscribers[event]) {
        subscribers[event].forEach(fn => {
          try { fn(data); } catch(e) { console.error(e); }
        });
      }
    },

    // ================= MOBILE / TOUCH ERGONOMICS =================
    
    // Dynamic Viewport Adjustment for Mobile Keyboard (window.visualViewport)
    bindVisualViewport(bottomBarElement) {
      if (!window.visualViewport || !bottomBarElement) return;

      const onResize = () => {
        const vv = window.visualViewport;
        const offsetFromBottom = window.innerHeight - (vv.height + vv.offsetTop);
        if (offsetFromBottom > 0) {
          // Keyboard is open — lift bottom bar smoothly without viewport jump
          bottomBarElement.style.transform = `translateY(-${Math.max(0, offsetFromBottom)}px)`;
        } else {
          bottomBarElement.style.transform = 'translateY(0)';
        }
      };

      window.visualViewport.addEventListener('resize', onResize);
      window.visualViewport.addEventListener('scroll', onResize);
    },

    // Edge-Swipe Gestures (Back & Forward)
    setupEdgeGestures(touchSurface, onBack, onForward) {
      if (!touchSurface) return;

      let startX = 0;
      let startY = 0;
      let isEdgeSwipe = false;
      let swipeDirection = null;

      touchSurface.addEventListener('touchstart', (e) => {
        if (e.touches.length !== 1) return;
        const touch = e.touches[0];
        startX = touch.clientX;
        startY = touch.clientY;

        const screenWidth = window.innerWidth;
        // Edge threshold: within 35px of either left or right bezel
        if (startX <= 35) {
          isEdgeSwipe = true;
          swipeDirection = 'back';
        } else if (startX >= screenWidth - 35) {
          isEdgeSwipe = true;
          swipeDirection = 'forward';
        } else {
          isEdgeSwipe = false;
          swipeDirection = null;
        }
      }, { passive: true });

      touchSurface.addEventListener('touchend', (e) => {
        if (!isEdgeSwipe || !swipeDirection) return;
        const endTouch = e.changedTouches[0];
        const deltaX = endTouch.clientX - startX;
        const deltaY = Math.abs(endTouch.clientY - startY);

        // Confirm horizontal intent (deltaX > 75px, vertical deviation < 60px)
        if (deltaY < 60) {
          if (swipeDirection === 'back' && deltaX > 75) {
            if (typeof onBack === 'function') onBack();
            else this.goBack();
          } else if (swipeDirection === 'forward' && deltaX < -75) {
            if (typeof onForward === 'function') onForward();
            else this.goForward();
          }
        }

        isEdgeSwipe = false;
        swipeDirection = null;
      }, { passive: true });
    }
  };

  // Attach to global window
  global.StauntBridge = Bridge;

})(typeof window !== 'undefined' ? window : this);
