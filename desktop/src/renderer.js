// Staunt Core — Universal Responsive Shell Controller
(function() {
  'use strict';

  const bridge = window.StauntBridge;
  let activeTab = null;
  let tabCountNum = 1;
  let isOverviewOpen = false;

  document.addEventListener('DOMContentLoaded', () => {
    // Desktop Controls
    const btnWinClose = document.getElementById('btnWinClose');
    const btnWinMin = document.getElementById('btnWinMin');
    const btnWinMax = document.getElementById('btnWinMax');
    const btnBack = document.getElementById('btnBack');
    const btnForward = document.getElementById('btnForward');
    const btnReload = document.getElementById('btnReload');
    const btnNewTabDesktop = document.getElementById('btnNewTabDesktop');
    const btnTabCounter = document.getElementById('btnTabCounter');
    const btnSettings = document.getElementById('btnSettings');

    // Desktop Omnibox Elements
    const desktopCapsule = document.getElementById('desktopOmniboxCapsule');
    const desktopDisplay = document.getElementById('desktopOmniboxDisplay');
    const desktopInput = document.getElementById('desktopOmniboxInput');

    // Mobile Elements
    const mobileBottomBar = document.getElementById('mobileBottomBar');
    const btnMobileBack = document.getElementById('btnMobileBack');
    const btnMobileForward = document.getElementById('btnMobileForward');
    const btnMobileShare = document.getElementById('btnMobileShare');
    const btnMobileTabCounter = document.getElementById('btnMobileTabCounter');
    const mobileCapsule = document.getElementById('mobileOmniboxCapsule');
    const mobileDisplay = document.getElementById('mobileOmniboxDisplay');
    const mobileInput = document.getElementById('mobileOmniboxInput');

    // Tab Overview & Settings Overlays
    const tabOverviewOverlay = document.getElementById('tabOverviewOverlay');
    const btnCloseOverview = document.getElementById('btnCloseOverview');
    const btnOverviewNewTab = document.getElementById('btnOverviewNewTab');
    const overviewGrid = document.getElementById('overviewGrid');

    const settingsOverlay = document.getElementById('settingsOverlay');
    const btnCloseSettings = document.getElementById('btnCloseSettings');
    const btnClearData = document.getElementById('btnClearData');

    // Bind Window Controls
    if (btnWinClose) btnWinClose.addEventListener('click', () => bridge.closeWindow());
    if (btnWinMin) btnWinMin.addEventListener('click', () => bridge.minimizeWindow());
    if (btnWinMax) btnWinMax.addEventListener('click', () => bridge.maximizeWindow());

    // Bind Navigation (Desktop & Mobile)
    const handleBack = () => bridge.goBack();
    const handleForward = () => bridge.goForward();
    const handleReload = () => bridge.reload();

    if (btnBack) btnBack.addEventListener('click', handleBack);
    if (btnForward) btnForward.addEventListener('click', handleForward);
    if (btnReload) btnReload.addEventListener('click', handleReload);

    if (btnMobileBack) btnMobileBack.addEventListener('click', handleBack);
    if (btnMobileForward) btnMobileForward.addEventListener('click', handleForward);

    if (btnMobileShare) {
      btnMobileShare.addEventListener('click', () => {
        if (navigator.share && activeTab?.url) {
          navigator.share({ title: activeTab.title, url: activeTab.url }).catch(() => {});
        } else if (activeTab?.url) {
          navigator.clipboard.writeText(activeTab.url);
          mobileDisplay.textContent = 'Copied!';
          setTimeout(() => updateDisplays(activeTab), 1500);
        }
      });
    }

    // New Tab
    const handleNewTab = () => {
      closeOverview();
      bridge.createTab('staunt://newtab');
    };
    if (btnNewTabDesktop) btnNewTabDesktop.addEventListener('click', handleNewTab);
    if (btnOverviewNewTab) btnOverviewNewTab.addEventListener('click', handleNewTab);

    // Tab Overview Toggle
    const handleToggleOverview = () => {
      isOverviewOpen = !isOverviewOpen;
      if (isOverviewOpen) {
        renderOverviewGrid();
        tabOverviewOverlay.classList.remove('hidden');
      } else {
        closeOverview();
      }
    };
    if (btnTabCounter) btnTabCounter.addEventListener('click', handleToggleOverview);
    if (btnMobileTabCounter) btnMobileTabCounter.addEventListener('click', handleToggleOverview);
    if (btnCloseOverview) btnCloseOverview.addEventListener('click', closeOverview);

    function closeOverview() {
      isOverviewOpen = false;
      tabOverviewOverlay.classList.add('hidden');
    }

    // Settings Modal
    if (btnSettings) {
      btnSettings.addEventListener('click', () => settingsOverlay.classList.remove('hidden'));
    }
    if (btnCloseSettings) {
      btnCloseSettings.addEventListener('click', () => settingsOverlay.classList.add('hidden'));
    }
    if (btnClearData) {
      btnClearData.addEventListener('click', () => {
        try { localStorage.clear(); } catch(e) {}
        alert('Privacy cache and local history cleared.');
        settingsOverlay.classList.add('hidden');
      });
    }

    // ================= OMNIBOX INTERACTION (DESKTOP) =================
    if (desktopCapsule && desktopInput) {
      desktopCapsule.addEventListener('click', () => {
        desktopCapsule.classList.add('focused');
        desktopDisplay.classList.add('hidden');
        desktopInput.classList.remove('hidden');
        desktopInput.value = (activeTab?.url && !activeTab.url.includes('newtab.html') && activeTab.url !== 'staunt://newtab') ? activeTab.url : '';
        desktopInput.focus();
        desktopInput.select();
      });

      desktopInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          submitNavigation(desktopInput.value.trim());
          deactivateDesktopOmnibox();
        } else if (e.key === 'Escape') {
          deactivateDesktopOmnibox();
        }
      });

      desktopInput.addEventListener('blur', () => setTimeout(deactivateDesktopOmnibox, 160));
    }

    function deactivateDesktopOmnibox() {
      desktopCapsule.classList.remove('focused');
      desktopInput.classList.add('hidden');
      desktopDisplay.classList.remove('hidden');
      if (activeTab) updateDisplays(activeTab);
    }

    // ================= OMNIBOX INTERACTION (MOBILE) =================
    if (mobileCapsule && mobileInput) {
      mobileCapsule.addEventListener('click', () => {
        mobileCapsule.classList.add('focused');
        mobileDisplay.classList.add('hidden');
        mobileInput.classList.remove('hidden');
        mobileInput.value = (activeTab?.url && !activeTab.url.includes('newtab.html') && activeTab.url !== 'staunt://newtab') ? activeTab.url : '';
        mobileInput.focus();
        mobileInput.select();
      });

      mobileInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
          submitNavigation(mobileInput.value.trim());
          deactivateMobileOmnibox();
        } else if (e.key === 'Escape') {
          deactivateMobileOmnibox();
        }
      });

      mobileInput.addEventListener('blur', () => setTimeout(deactivateMobileOmnibox, 160));
    }

    function deactivateMobileOmnibox() {
      mobileCapsule.classList.remove('focused');
      mobileInput.classList.add('hidden');
      mobileDisplay.classList.remove('hidden');
      if (activeTab) updateDisplays(activeTab);
    }

    function submitNavigation(val) {
      if (!val) return;
      bridge.navigate(val);
    }

    function updateDisplays(tab) {
      if (!tab) return;
      let display = 'Search or enter website name';
      let mobileDisp = 'Search';

      if (tab.url && !tab.url.includes('newtab.html') && tab.url !== 'staunt://newtab') {
        try {
          const u = new URL(tab.url);
          display = u.hostname.replace(/^www\./, '');
          mobileDisp = display;
        } catch(e) {
          display = tab.url;
          mobileDisp = tab.url;
        }
      }

      if (desktopDisplay) desktopDisplay.textContent = display;
      if (mobileDisplay) mobileDisplay.textContent = mobileDisp;
    }

    // ================= MOBILE RESILIENT VIEWPORT & SWIPE GESTURES =================
    // 1. Smooth keyboard visualViewport adaptation
    bridge.bindVisualViewport(mobileBottomBar);

    // 2. Mobile Edge-Swipe Gestures (Back on swipe-right, Forward on swipe-left)
    bridge.setupEdgeGestures(document.body, handleBack, handleForward);

    // ================= TAB OVERVIEW GRID =================
    function renderOverviewGrid() {
      if (!overviewGrid) return;
      overviewGrid.innerHTML = '';

      const allTabs = bridge.getTabs();
      tabCountNum = allTabs.size || 1;
      updateTabBadges(tabCountNum);

      allTabs.forEach((tab) => {
        const card = document.createElement('div');
        card.className = `tab-card \${tab.id === activeTab?.id ? 'active' : ''}`;
        
        let domain = 'Start Page';
        try {
          if (tab.url && !tab.url.includes('newtab.html') && tab.url !== 'staunt://newtab') {
            domain = new URL(tab.url).hostname.replace(/^www\./, '');
          }
        } catch(e) {}

        card.innerHTML = \`
          <div class="tab-card-header">
            <div class="tab-card-info">
              <img class="tab-card-favicon" src="\${tab.favicon || 'https://www.google.com/favicon.ico'}" onerror="this.src='https://www.google.com/favicon.ico'" />
              <span class="tab-card-title">\${tab.title || domain}</span>
            </div>
            <button class="tab-card-close" title="Close Tab">&times;</button>
          </div>
          <div class="tab-card-body">
            <span>\${domain}</span>
          </div>
        \`;

        card.querySelector('.tab-card-close').addEventListener('click', (e) => {
          e.stopPropagation();
          bridge.closeTab(tab.id);
          renderOverviewGrid();
        });

        card.addEventListener('click', () => {
          bridge.switchTab(tab.id);
          closeOverview();
        });

        overviewGrid.appendChild(card);
      });
    }

    function updateTabBadges(count) {
      const desktopBadge = document.getElementById('tabCount');
      const mobileBadge = document.getElementById('mobileTabCount');
      if (desktopBadge) desktopBadge.textContent = count;
      if (mobileBadge) mobileBadge.textContent = count;
    }

    // ================= BRIDGE EVENT SUBSCRIPTIONS =================
    bridge.onTabCreated((tab) => {
      activeTab = tab;
      tabCountNum++;
      updateTabBadges(tabCountNum);
      if (isOverviewOpen) renderOverviewGrid();
    });

    bridge.onTabUpdated((tab) => {
      activeTab = tab;
      updateDisplays(tab);
      if (isOverviewOpen) renderOverviewGrid();
    });

    bridge.onTabClosed(() => {
      tabCountNum = Math.max(1, tabCountNum - 1);
      updateTabBadges(tabCountNum);
      if (isOverviewOpen) renderOverviewGrid();
    });

    bridge.onTabSwitched((data) => {
      const tabs = bridge.getTabs();
      if (tabs.has(data.activeTabId)) {
        activeTab = tabs.get(data.activeTabId);
        updateDisplays(activeTab);
      }
      if (isOverviewOpen) renderOverviewGrid();
    });

    // Keyboard Shortcuts (⌘L, ⌘T, ⌘W, ⇧⌘T, ⌘R)
    window.addEventListener('keydown', (e) => {
      const isMeta = e.metaKey || e.ctrlKey;
      if (isMeta && e.key.toLowerCase() === 'l') {
        e.preventDefault();
        if (window.innerWidth > 768) {
          desktopCapsule?.click();
        } else {
          mobileCapsule?.click();
        }
      } else if (isMeta && e.key.toLowerCase() === 't') {
        e.preventDefault();
        handleNewTab();
      } else if (isMeta && e.key.toLowerCase() === 'w') {
        e.preventDefault();
        if (activeTab) bridge.closeTab(activeTab.id);
      } else if (isMeta && e.shiftKey && e.key.toLowerCase() === 't') {
        e.preventDefault();
        bridge.undoCloseTab();
      } else if (isMeta && e.key.toLowerCase() === 'r') {
        e.preventDefault();
        bridge.reload();
      } else if (isMeta && e.key === '\\') {
        e.preventDefault();
        handleToggleOverview();
      }
    });

    // Initialize first tab
    bridge.createTab('staunt://newtab');
  });
})();
