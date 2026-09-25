// VASTUDA — Independent AI Discovery & Neural Web Engine Client Logic

document.addEventListener("DOMContentLoaded", () => {
  // Centralized Backend Resolution: Route Vercel Frontend Traffic to Render Backend
  const RENDER_BACKEND_URL = "https://staunt.onrender.com";
  const isVercel = window.location.hostname.endsWith(".vercel.app") || window.location.hostname === "staunt.vercel.app";
  const API_BASE = (window.STAUNT_BACKEND_URL !== undefined) ? window.STAUNT_BACKEND_URL : (isVercel ? RENDER_BACKEND_URL : "");

  async function apiFetch(path, options) {
    if (API_BASE && typeof path === "string" && path.startsWith("/api/")) {
      const fullUrl = `${API_BASE}${path}`;
      try {
        const resp = await fetch(fullUrl, options);
        if (resp.ok) return resp;
      } catch (err) {
        console.warn(`[STAUNT] Backend request to ${fullUrl} failed, falling back to local:`, err);
      }
    }
    return fetch(path, options);
  }

  // State
  let currentQuery = "";
  let activeTab = "all";
  let currentUser = null;
  let userCollections = [];
  let pendingSaveItem = null;
  let currentReaderFontSize = 1.15; // rem

  // DOM Elements - Navigation & Header
  const header = document.querySelector(".app-header");
  const brandLogo = document.getElementById("brandLogo");
  const homeView = document.getElementById("homeView");
  const resultsView = document.getElementById("resultsView");
  const headerSearchWrap = document.getElementById("headerSearchWrap");

  const homeInput = document.getElementById("homeSearchInput");
  const homeForm = document.getElementById("homeSearchForm");
  const homeClearBtn = document.getElementById("homeClearBtn");
  const homeVoiceBtn = document.getElementById("homeVoiceBtn");

  const headerInput = document.getElementById("headerSearchInput");
  const headerForm = document.getElementById("headerSearchForm");
  const headerClearBtn = document.getElementById("headerClearBtn");
  const headerVoiceBtn = document.getElementById("headerVoiceBtn");

  const suggestBoxHome = document.getElementById("suggestBoxHome");
  const suggestBoxHeader = document.getElementById("suggestBoxHeader");

  const tabBtns = document.querySelectorAll(".tab-btn");
  const themeToggle = document.getElementById("themeToggle");
  const userAuthBtn = document.getElementById("userAuthBtn");
  const userAuthText = document.getElementById("userAuthText");
  const dashboardBtn = document.getElementById("dashboardBtn");

  // Results Sections
  const instantAnswerCard = document.getElementById("instantAnswerCard");
  const calcExpr = document.getElementById("calcExpr");
  const calcResult = document.getElementById("calcResult");

  const destinationCard = document.getElementById("destinationCard");
  const destHeroImgWrap = document.getElementById("destHeroImgWrap");
  const destHeroImg = document.getElementById("destHeroImg");
  const destTitle = document.getElementById("destTitle");
  const destCountry = document.getElementById("destCountry");
  const destWeather = document.getElementById("destWeather");
  const destTagline = document.getElementById("destTagline");
  const destBestTime = document.getElementById("destBestTime");
  const destDuration = document.getElementById("destDuration");
  const destAttractions = document.getElementById("destAttractions");
  const destMapsBtn = document.getElementById("destMapsBtn");
  const destHotelsBtn = document.getElementById("destHotelsBtn");
  const destFlightsBtn = document.getElementById("destFlightsBtn");

  const visualStripContainer = document.getElementById("visualStripContainer");
  const visualStripScroll = document.getElementById("visualStripScroll");
  const visualStripMoreBtn = document.getElementById("visualStripMoreBtn");

  const aiOverviewCard = document.getElementById("aiOverviewCard");

  const aiContent = document.getElementById("aiContent");
  const aiSources = document.getElementById("aiSources");
  const copyOverviewBtn = document.getElementById("copyOverviewBtn");

  const researchCard = document.getElementById("researchCard");
  const researchHeading = document.getElementById("researchHeading");
  const researchSummary = document.getElementById("researchSummary");
  const researchFindings = document.getElementById("researchFindings");
  const researchMethodology = document.getElementById("researchMethodology");
  const researchLimitations = document.getElementById("researchLimitations");

  const webResultsSection = document.getElementById("webResultsSection");
  const codeSection = document.getElementById("codeSection");
  const docsSection = document.getElementById("docsSection");
  const shoppingSection = document.getElementById("shoppingSection");
  const jobsSection = document.getElementById("jobsSection");
  const videosSection = document.getElementById("videosSection");
  const imagesSection = document.getElementById("imagesSection");
  const emptyState = document.getElementById("emptyState");
  const relatedQueriesList = document.getElementById("relatedQueriesList");

  // Modals
  const authModal = document.getElementById("authModal");
  const closeAuthModal = document.getElementById("closeAuthModal");
  const tabSignIn = document.getElementById("tabSignIn");
  const tabRegister = document.getElementById("tabRegister");
  const authForm = document.getElementById("authForm");
  const nameGroup = document.getElementById("nameGroup");
  const authName = document.getElementById("authName");
  const authEmail = document.getElementById("authEmail");
  const authPassword = document.getElementById("authPassword");
  const authSubmitBtn = document.getElementById("authSubmitBtn");
  const authErrorMsg = document.getElementById("authErrorMsg");

  const dashboardModal = document.getElementById("dashboardModal");
  const closeDashboardModal = document.getElementById("closeDashboardModal");
  const dashAvatar = document.getElementById("dashAvatar");
  const dashUserName = document.getElementById("dashUserName");
  const dashUserEmail = document.getElementById("dashUserEmail");
  const dashTabs = document.querySelectorAll(".dash-tab");
  const dashPanes = document.querySelectorAll(".dash-view-pane");

  const collectionsGrid = document.getElementById("collectionsGrid");
  const newCollectionBtn = document.getElementById("newCollectionBtn");
  const historyList = document.getElementById("historyList");
  const clearHistoryBtn = document.getElementById("clearHistoryBtn");
  const toggleHistoryBtn = document.getElementById("toggleHistoryBtn");
  const savedResultsList = document.getElementById("savedResultsList");
  const savedFilterSelect = document.getElementById("savedFilterSelect");

  const prefSafeSearch = document.getElementById("prefSafeSearch");
  const prefNewTab = document.getElementById("prefNewTab");
  const prefHistoryEnabled = document.getElementById("prefHistoryEnabled");
  const prefPersonalized = document.getElementById("prefPersonalized");
  const exportDataBtn = document.getElementById("exportDataBtn");
  const signOutBtn = document.getElementById("signOutBtn");

  const saveResultModal = document.getElementById("saveResultModal");
  const closeSaveResultModal = document.getElementById("closeSaveResultModal");
  const saveItemTitle = document.getElementById("saveItemTitle");
  const saveCollectionSelect = document.getElementById("saveCollectionSelect");
  const confirmSaveBtn = document.getElementById("confirmSaveBtn");

  const readerModal = document.getElementById("readerModal");
  const closeReaderBtn = document.getElementById("closeReaderBtn");
  const readerTitle = document.getElementById("readerTitle");
  const readerBody = document.getElementById("readerBody");
  const readerDomainBadge = document.getElementById("readerDomainBadge");
  const readerTimeBadge = document.getElementById("readerTimeBadge");
  const readerExternalLink = document.getElementById("readerExternalLink");
  const readerFontDec = document.getElementById("readerFontDec");
  const readerFontInc = document.getElementById("readerFontInc");

  const lightboxModal = document.getElementById("lightboxModal");
  const closeLightboxBtn = document.getElementById("closeLightboxBtn");
  const lightboxImg = document.getElementById("lightboxImg");
  const lightboxTitle = document.getElementById("lightboxTitle");
  const lightboxVisitBtn = document.getElementById("lightboxVisitBtn");

  // --- Theme Management ---
  const savedTheme = localStorage.getItem("vastuda_theme") || "dark";
  document.documentElement.setAttribute("data-theme", savedTheme);
  updateThemeIcon(savedTheme);

  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("vastuda_theme", next);
    updateThemeIcon(next);
  });

  function updateThemeIcon(theme) {
    themeToggle.innerHTML = theme === "dark" 
      ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>`
      : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
  }

  // --- Clear Buttons Setup ---
  function setupClearBtn(input, btn) {
    input.addEventListener("input", () => {
      btn.style.display = input.value.length > 0 ? "flex" : "none";
    });
    btn.addEventListener("click", () => {
      input.value = "";
      btn.style.display = "none";
      input.focus();
    });
  }
  setupClearBtn(homeInput, homeClearBtn);
  setupClearBtn(headerInput, headerClearBtn);

  // Logo returns to home view
  brandLogo.addEventListener("click", () => {
    document.body.classList.remove("in-search-mode");
    resultsView.classList.remove("active");
    resultsView.style.display = "none";
    homeView.style.display = "flex";
    headerSearchWrap.style.display = "none";
    homeInput.value = "";
    headerInput.value = "";
    currentQuery = "";
  });

  // --- Guest Local Search History (Phase 4 & 11) ---
  const GUEST_HISTORY_KEY = "vastuda_guest_history";

  function getGuestHistory() {
    try {
      return JSON.parse(localStorage.getItem(GUEST_HISTORY_KEY) || "[]");
    } catch (e) {
      return [];
    }
  }

  function addGuestHistory(query, category = "all") {
    if (!query || query.trim().length === 0) return;
    const cleanQ = query.trim();
    let history = getGuestHistory();
    history = history.filter(item => item.query.toLowerCase() !== cleanQ.toLowerCase());
    history.unshift({ query: cleanQ, category, timestamp: Date.now() });
    if (history.length > 30) history = history.slice(0, 30);
    try {
      localStorage.setItem(GUEST_HISTORY_KEY, JSON.stringify(history));
    } catch (e) {}
    renderHomeRecentSearches();
  }

  function clearGuestHistory() {
    try {
      localStorage.removeItem(GUEST_HISTORY_KEY);
    } catch (e) {}
    renderHomeRecentSearches();
  }

  function renderHomeRecentSearches() {
    const wrap = document.getElementById("homeRecentWrap");
    const chipsContainer = document.getElementById("homeRecentChips");
    if (!wrap || !chipsContainer) return;

    const history = getGuestHistory();
    if (history.length === 0) {
      wrap.style.display = "none";
      chipsContainer.innerHTML = "";
      return;
    }

    wrap.style.display = "block";
    chipsContainer.innerHTML = history.slice(0, 8).map(item => `
      <button class="home-recent-chip" type="button" data-q="${escapeHtml(item.query)}" data-cat="${escapeHtml(item.category || 'all')}">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
        <span>${escapeHtml(item.query)}</span>
      </button>
    `).join("");

    chipsContainer.querySelectorAll(".home-recent-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        const cat = chip.getAttribute("data-cat") || "all";
        homeInput.value = q;
        headerInput.value = q;
        executeSearch(q, cat, currentTimeFilter);
      });
    });
  }

  const clearHomeRecentBtn = document.getElementById("clearHomeRecentBtn");
  if (clearHomeRecentBtn) {
    clearHomeRecentBtn.addEventListener("click", clearGuestHistory);
  }
  renderHomeRecentSearches();

  // --- Functional Search Vertical Shortcuts (Phase 10) ---
  const homeVerticalShortcuts = document.getElementById("homeVerticalShortcuts");
  if (homeVerticalShortcuts) {
    homeVerticalShortcuts.querySelectorAll("button.pill").forEach(btn => {
      btn.addEventListener("click", () => {
        const tab = btn.getAttribute("data-tab");
        const currentVal = homeInput.value.trim();
        if (currentVal) {
          executeSearch(currentVal, tab, currentTimeFilter);
        } else {
          activeTab = tab;
          tabBtns.forEach(b => {
            b.classList.toggle("active", b.getAttribute("data-tab") === tab);
          });
          const span = btn.querySelector("span");
          homeInput.placeholder = `Search in ${span ? span.textContent : tab}...`;
          homeInput.focus();
        }
      });
    });
  }

  // --- Header Apps Menu & Quick Settings (Phase 12 & 13) ---
  const appsMenuDropdown = document.getElementById("appsMenuDropdown");
  const menuOpenDashboard = document.getElementById("menuOpenDashboard");
  const menuOpenSettings = document.getElementById("menuOpenSettings");

  if (dashboardBtn && appsMenuDropdown) {
    dashboardBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = appsMenuDropdown.style.display === "block";
      appsMenuDropdown.style.display = isVisible ? "none" : "block";
    });

    document.addEventListener("click", (e) => {
      if (appsMenuDropdown && !appsMenuDropdown.contains(e.target) && e.target !== dashboardBtn) {
        appsMenuDropdown.style.display = "none";
      }
    });
  }

  if (menuOpenDashboard) {
    menuOpenDashboard.addEventListener("click", () => {
      if (appsMenuDropdown) appsMenuDropdown.style.display = "none";
      openDashboard();
    });
  }

  if (menuOpenSettings) {
    menuOpenSettings.addEventListener("click", () => {
      if (appsMenuDropdown) appsMenuDropdown.style.display = "none";
      if (!currentUser) {
        dashboardModal.classList.add("open");
        dashTabs.forEach(t => t.classList.remove("active"));
        dashPanes.forEach(p => p.classList.remove("active"));
        const prefTab = document.querySelector('.dash-tab[data-view="preferences"]');
        const prefPane = document.getElementById("panePreferences");
        if (prefTab) prefTab.classList.add("active");
        if (prefPane) prefPane.classList.add("active");
      } else {
        openDashboard();
        const prefTab = document.querySelector('.dash-tab[data-view="preferences"]');
        if (prefTab) prefTab.click();
      }
    });
  }

  // --- Voice Search Support ---
  function setupVoiceSearch(btn, input) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      btn.style.display = "none";
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    btn.addEventListener("click", () => {
      btn.style.color = "#ff453a";
      recognition.start();
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      input.value = transcript;
      btn.style.color = "";
      executeSearch(transcript, activeTab, currentTimeFilter);
    };

    recognition.onerror = () => {
      btn.style.color = "";
    };
    recognition.onend = () => {
      btn.style.color = "";
    };
  }
  setupVoiceSearch(homeVoiceBtn, homeInput);
  setupVoiceSearch(headerVoiceBtn, headerInput);

  // --- Search Suggestions with Full Keyboard Navigation (Phase 3) ---
  function setupSuggestions(input, box) {
    let timeout = null;
    let selectedIndex = -1;
    let currentItems = [];

    function renderSuggestions(items, isRecent = false) {
      currentItems = items || [];
      selectedIndex = -1;
      if (currentItems.length === 0) {
        box.classList.remove("active");
        box.innerHTML = "";
        return;
      }
      box.innerHTML = currentItems.map((s, idx) => `
        <div class="suggest-item ${isRecent ? 'recent-type' : ''}" data-idx="${idx}">
          ${isRecent ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>' : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'}
          <span>${escapeHtml(s)}</span>
        </div>
      `).join("");
      box.classList.add("active");

      box.querySelectorAll(".suggest-item").forEach((item) => {
        item.addEventListener("click", () => {
          const idx = parseInt(item.getAttribute("data-idx"), 10);
          const text = currentItems[idx];
          input.value = text;
          box.classList.remove("active");
          executeSearch(text, activeTab, currentTimeFilter);
        });
      });
    }

    // Show recent searches on focus when input is empty
    input.addEventListener("focus", () => {
      if (input.value.trim().length === 0) {
        const recents = getGuestHistory().slice(0, 5).map(h => h.query);
        if (recents.length > 0) {
          renderSuggestions(recents, true);
        }
      }
    });

    input.addEventListener("input", () => {
      const val = input.value.trim();
      clearTimeout(timeout);
      if (val.length === 0) {
        const recents = getGuestHistory().slice(0, 5).map(h => h.query);
        if (recents.length > 0) {
          renderSuggestions(recents, true);
        } else {
          box.classList.remove("active");
          box.innerHTML = "";
        }
        return;
      }
      if (val.length < 2) {
        box.classList.remove("active");
        box.innerHTML = "";
        return;
      }
      timeout = setTimeout(async () => {
        try {
          const resp = await apiFetch(`/api/suggest?q=${encodeURIComponent(val)}`);
          const items = await resp.json();
          renderSuggestions(items, false);
        } catch (e) {
          box.classList.remove("active");
        }
      }, 150);
    });

    input.addEventListener("keydown", (e) => {
      if (!box.classList.contains("active") || currentItems.length === 0) {
        if (e.key === "Escape") box.classList.remove("active");
        return;
      }

      if (e.key === "ArrowDown") {
        e.preventDefault();
        selectedIndex = (selectedIndex + 1) % currentItems.length;
        updateSelection();
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        selectedIndex = (selectedIndex - 1 + currentItems.length) % currentItems.length;
        updateSelection();
      } else if (e.key === "Enter") {
        if (selectedIndex >= 0 && selectedIndex < currentItems.length) {
          e.preventDefault();
          const text = currentItems[selectedIndex];
          input.value = text;
          box.classList.remove("active");
          executeSearch(text, activeTab, currentTimeFilter);
        }
      } else if (e.key === "Escape") {
        box.classList.remove("active");
      }
    });

    function updateSelection() {
      const domItems = box.querySelectorAll(".suggest-item");
      domItems.forEach((el, idx) => {
        if (idx === selectedIndex) {
          el.classList.add("selected");
          el.classList.add("highlighted");
          input.value = currentItems[idx];
        } else {
          el.classList.remove("selected");
          el.classList.remove("highlighted");
        }
      });
    }

    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !box.contains(e.target)) {
        box.classList.remove("active");
      }
    });
  }
  setupSuggestions(homeInput, suggestBoxHome);
  setupSuggestions(headerInput, suggestBoxHeader);

  // --- Homepage Vertical Navigation Modes ---
  const homeModeBtns = document.querySelectorAll(".mode-nav-btn");
  homeModeBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      homeModeBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.getAttribute("data-tab") || "all";
      activeTab = tab;
      const q = homeInput.value.trim();
      if (q) {
        headerInput.value = q;
        executeSearch(q, activeTab, currentTimeFilter);
      } else {
        homeInput.focus();
      }
    });
  });

  // --- Category Tabs Switching (Results Page) ---
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.getAttribute("data-tab");
      if (currentQuery) {
        executeSearch(currentQuery, activeTab, currentTimeFilter);
      }
    });
  });

  // --- Search Filters Dropdown (UI/UX 2.0) ---
  let currentTimeFilter = "";
  const filterTimeBtn = document.getElementById("filterTimeBtn");
  const filterTimeMenu = document.getElementById("filterTimeMenu");
  const filterTimeLabel = document.getElementById("filterTimeLabel");
  const filterMenuItems = document.querySelectorAll(".filter-menu-item");
  const filterChips = document.querySelectorAll(".filter-chip");
  const resultsCountNotice = document.getElementById("resultsCountNotice");

  if (filterTimeBtn && filterTimeMenu) {
    filterTimeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isVisible = filterTimeMenu.style.display === "block";
      filterTimeMenu.style.display = isVisible ? "none" : "block";
      filterTimeBtn.setAttribute("aria-expanded", String(!isVisible));
    });

    filterMenuItems.forEach(item => {
      item.addEventListener("click", () => {
        filterMenuItems.forEach(m => m.classList.remove("active"));
        item.classList.add("active");
        currentTimeFilter = item.getAttribute("data-time") || "";
        if (filterTimeLabel) {
          filterTimeLabel.textContent = item.textContent.trim();
        }
        filterTimeMenu.style.display = "none";
        filterTimeBtn.setAttribute("aria-expanded", "false");
        if (currentQuery) {
          executeSearch(currentQuery, activeTab, currentTimeFilter);
        }
      });
    });

    document.addEventListener("click", (e) => {
      if (!filterTimeBtn.contains(e.target) && !filterTimeMenu.contains(e.target)) {
        filterTimeMenu.style.display = "none";
        filterTimeBtn.setAttribute("aria-expanded", "false");
      }
    });
  }

  // Fallback for filter chips if present
  filterChips.forEach(chip => {
    chip.addEventListener("click", () => {
      filterChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      currentTimeFilter = chip.getAttribute("data-time") || "";
      if (currentQuery) {
        executeSearch(currentQuery, activeTab, currentTimeFilter);
      }
    });
  });

  if (visualStripMoreBtn) {
    visualStripMoreBtn.addEventListener("click", () => {
      const imgTab = document.querySelector('button.tab-btn[data-tab="images"]');
      if (imgTab) imgTab.click();
    });
  }


  // --- Search Forms Submission ---
  homeForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = homeInput.value.trim();
    if (q) {
      headerInput.value = q;
      executeSearch(q, activeTab);
    }
  });

  headerForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const q = headerInput.value.trim();
    if (q) {
      homeInput.value = q;
      executeSearch(q, activeTab);
    }
  });

  // --- Core Search Execution ---
  async function executeSearch(query, category = "all", time = "") {
    currentQuery = query;
    activeTab = category;
    currentTimeFilter = time || "";

    // Sync tab button active states
    tabBtns.forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === category);
    });

    // Sync homepage mode buttons
    homeModeBtns.forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-tab") === category);
    });

    // Sync filter menu items and label
    filterMenuItems.forEach(m => {
      const isAct = (m.getAttribute("data-time") || "") === currentTimeFilter;
      m.classList.toggle("active", isAct);
      if (isAct && filterTimeLabel) {
        filterTimeLabel.textContent = m.textContent.trim();
      }
    });

    // Sync filter chips active states
    filterChips.forEach(c => {
      c.classList.toggle("active", (c.getAttribute("data-time") || "") === currentTimeFilter);
    });

    // Record search in guest history
    addGuestHistory(query, category);

    // Switch view to results
    document.body.classList.add("in-search-mode");
    homeView.style.display = "none";
    resultsView.style.display = "block";
    resultsView.classList.add("active");
    headerSearchWrap.style.display = "flex";
    headerInput.value = query;

    // Sync URL without reload
    try {
      const url = new URL(window.location);
      url.searchParams.set("q", query);
      if (category && category !== "all") {
        url.searchParams.set("category", category);
      } else {
        url.searchParams.delete("category");
      }
      if (currentTimeFilter) {
        url.searchParams.set("time", currentTimeFilter);
      } else {
        url.searchParams.delete("time");
      }
      window.history.replaceState({ query, category, time: currentTimeFilter }, "", url);
    } catch (e) {}

    // Reset section visibilities
    instantAnswerCard.style.display = "none";
    destinationCard.style.display = "none";
    destHeroImgWrap.style.display = "none";
    visualStripContainer.style.display = "none";
    aiOverviewCard.style.display = "none";
    researchCard.style.display = "none";
    webResultsSection.style.display = "none";
    codeSection.style.display = "none";
    docsSection.style.display = "none";
    shoppingSection.style.display = "none";
    jobsSection.style.display = "none";
    videosSection.style.display = "none";
    imagesSection.style.display = "none";
    emptyState.style.display = "none";
    if (resultsCountNotice) resultsCountNotice.textContent = "Searching...";

    // Show loading skeleton in web results
    webResultsSection.style.display = "flex";
    webResultsSection.innerHTML = `
      <div class="result-card">
        <div class="skeleton" style="height: 18px; width: 40%; margin-bottom: 8px;"></div>
        <div class="skeleton" style="height: 24px; width: 70%; margin-bottom: 10px;"></div>
        <div class="skeleton" style="height: 14px; width: 95%; margin-bottom: 6px;"></div>
        <div class="skeleton" style="height: 14px; width: 85%;"></div>
      </div>
      <div class="result-card">
        <div class="skeleton" style="height: 18px; width: 35%; margin-bottom: 8px;"></div>
        <div class="skeleton" style="height: 24px; width: 65%; margin-bottom: 10px;"></div>
        <div class="skeleton" style="height: 14px; width: 90%; margin-bottom: 6px;"></div>
        <div class="skeleton" style="height: 14px; width: 75%;"></div>
      </div>
    `;

    try {
      let fetchUrl = `/api/search?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`;
      if (currentTimeFilter) {
        fetchUrl += `&time=${encodeURIComponent(currentTimeFilter)}`;
      }
      const resp = await apiFetch(fetchUrl);
      const data = await resp.json();

      webResultsSection.innerHTML = "";

      // Count notification
      if (resultsCountNotice) {
        const count = (data.results || data.images || data.videos || data.documents || data.repositories || []).length;
        resultsCountNotice.textContent = "";
      }

      // Route rendering according to category
      if (category === "all") {
        renderAllCategory(data, query);
      } else if (category === "ai") {
        renderAiCategory(data, query);
      } else if (category === "research") {
        renderResearchCategory(data, query);
      } else if (category === "news") {
        renderNewsCategory(data);
      } else if (category === "images") {
        renderImagesCategory(data);
      } else if (category === "videos") {
        renderVideosCategory(data);
      } else if (category === "docs") {
        renderDocsCategory(data);
      } else if (category === "code") {
        renderCodeCategory(data);
      } else if (category === "shopping") {
        renderShoppingCategory(data);
      } else if (category === "jobs") {
        renderJobsCategory(data);
      } else if (category === "places") {
        renderPlacesCategory(data);
      }

      // Update sidebar related queries
      updateRelatedQueries(query);

    } catch (err) {
      console.error("Search failed:", err);
      webResultsSection.innerHTML = `<p style="color:var(--text-secondary); padding: 20px;">Search request failed. Please check connection.</p>`;
      if (resultsCountNotice) resultsCountNotice.textContent = "";
    }
  }

  // --- Category Renderers ---

  // 1. ALL Category (Web + Instant Answer + Destination + AI Overview)
  function renderAllCategory(data, query) {
    // Instant Math
    if (data.instant_answer) {
      calcExpr.textContent = `${data.instant_answer.expression} =`;
      calcResult.textContent = data.instant_answer.result;
      instantAnswerCard.style.display = "block";
    }

    // Destination Card
    if (data.destination) {
      populateDestinationCard(data.destination);
      destinationCard.style.display = "block";
    }

    // Visual Discovery Strip (All Tab)
    const previewImages = data.images || [];
    if (previewImages.length > 0) {
      visualStripScroll.innerHTML = previewImages.slice(0, 6).map(img => `
        <div class="visual-strip-item" title="${escapeHtml(img.title || query)}">
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.title || query)}" referrerpolicy="no-referrer" onerror="this.parentElement.style.display='none'" />
        </div>
      `).join("");
      visualStripContainer.style.display = "block";

      visualStripScroll.querySelectorAll(".visual-strip-item").forEach((el, idx) => {
        el.addEventListener("click", () => {
          const img = previewImages[idx];
          lightboxImg.src = img.url;
          lightboxTitle.textContent = img.title || query;
          lightboxVisitBtn.href = img.url;
          lightboxModal.classList.add("open");
        });
      });
    } else {
      visualStripContainer.style.display = "none";
    }

    // Render Web Results
    const results = data.results || [];
    if (results.length > 0) {
      webResultsSection.style.display = "flex";
      results.forEach(item => {
        webResultsSection.appendChild(createWebResultCard(item));
      });

      // Trigger AI Overview async
      aiOverviewCard.style.display = "block";
      aiContent.innerHTML = `<div class="skeleton" style="height: 16px; width: 90%; margin-bottom: 8px;"></div><div class="skeleton" style="height: 16px; width: 75%;"></div>`;
      aiSources.innerHTML = "";
      fetchAiOverview(query, results);

    } else if (!data.instant_answer && !data.destination && previewImages.length === 0) {
      emptyState.style.display = "block";
    }

  }

  // 2. AI Category
  function renderAiCategory(data, query) {
    aiOverviewCard.style.display = "block";
    aiContent.innerHTML = formatMarkdown(data.overview || "");
    
    // Render source cards
    aiSources.innerHTML = (data.sources || []).map(s => `
      <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="source-chip" title="${escapeHtml(s.title)}">
        <span class="source-num">${s.index}</span>
        <span class="source-name">${escapeHtml(s.domain || "Source")}</span>
      </a>
    `).join("");

    // Also display web results underneath
    if (data.results && data.results.length > 0) {
      webResultsSection.style.display = "flex";
      data.results.forEach(item => {
        webResultsSection.appendChild(createWebResultCard(item));
      });
    }
  }

  // 3. Research Category
  function renderResearchCategory(data, query) {
    const research = data.research || {};
    researchCard.style.display = "block";
    researchHeading.textContent = `Scholarly Consensus: ${query}`;
    researchSummary.textContent = research.summary || "Synthesizing research evidence...";

    const findingsList = research.key_findings || [];
    researchFindings.innerHTML = findingsList.map(f => `<li>${escapeHtml(f)}</li>`).join("");

    researchMethodology.textContent = research.methodology_and_evidence || "Synthesized from peer-reviewed literature, preprints, and academic databases.";
    researchLimitations.textContent = research.counter_arguments_limitations || "Ongoing research continues to evaluate sample constraints, methodology variations, and edge cases.";

    // Render underlying research papers
    if (data.results && data.results.length > 0) {
      webResultsSection.style.display = "flex";
      data.results.forEach(item => {
        webResultsSection.appendChild(createWebResultCard(item));
      });
    }
  }

  // 4. News Category
  function renderNewsCategory(data) {
    const results = data.results || [];
    if (results.length > 0) {
      webResultsSection.style.display = "flex";
      results.forEach(item => {
        const card = createWebResultCard(item);
        if (item.published_date) {
          const datePill = document.createElement("span");
          datePill.className = "dest-stat-pill";
          datePill.style.fontSize = "0.75rem";
          datePill.textContent = item.published_date;
          card.querySelector(".result-meta")?.appendChild(datePill);
        }
        webResultsSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 5. Images Category (Phase 6)
  function renderImagesCategory(data) {
    imagesSection.style.display = "grid";
    imagesSection.innerHTML = "";
    const images = data.images || [];
    if (images.length > 0) {
      images.forEach(img => {
        const item = document.createElement("div");
        item.className = "image-card-box";
        
        let domain = "web";
        try {
          domain = new URL(img.url).hostname.replace("www.", "");
        } catch(e) {}

        item.innerHTML = `
          <div class="image-thumb-wrap">
            <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.title || 'Image')}" loading="lazy" referrerpolicy="no-referrer" onerror="this.closest('.image-card-box').style.display='none'" />
          </div>
          <div class="image-card-meta">
            <div class="image-card-title" title="${escapeHtml(img.title || 'Image')}">${escapeHtml(img.title || 'Image')}</div>
            <div class="image-card-source">${escapeHtml(domain)}</div>
          </div>
        `;

        item.addEventListener("click", () => {
          lightboxImg.src = img.url;
          lightboxTitle.textContent = img.title || "Image Preview";
          lightboxVisitBtn.href = img.url;
          lightboxModal.classList.add("open");
        });
        imagesSection.appendChild(item);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 6. Videos Category (Phase 7)
  function renderVideosCategory(data) {
    videosSection.style.display = "grid";
    videosSection.innerHTML = "";
    const videos = data.videos || [];
    if (videos.length > 0) {
      videos.forEach(v => {
        const card = document.createElement("a");
        card.className = "video-card-box";
        card.href = v.url;
        card.target = "_blank";
        card.rel = "noopener noreferrer";
        card.innerHTML = `
          <div class="video-thumb-container">
            <img src="${escapeHtml(v.thumbnail)}" alt="${escapeHtml(v.title)}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=480&q=80'" />
            <div class="video-play-badge">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            </div>
          </div>
          <div class="video-card-info">
            <div class="video-card-channel">${escapeHtml(v.channel || 'Video')}</div>
            <div class="video-card-title">${escapeHtml(v.title)}</div>
            ${v.snippet ? `<div class="video-card-snippet">${escapeHtml(v.snippet)}</div>` : ''}
          </div>
        `;
        videosSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 7. Documents Category (Phase 8)
  function renderDocsCategory(data) {
    docsSection.style.display = "flex";
    docsSection.innerHTML = "";
    const docs = data.documents || [];
    if (docs.length > 0) {
      docs.forEach(doc => {
        const card = document.createElement("div");
        card.className = "doc-card-box";
        const isPdf = (doc.file_type || '').toUpperCase() === 'PDF' || (doc.url || '').toLowerCase().endsWith('.pdf');
        card.innerHTML = `
          <div class="doc-header-row">
            <span class="${isPdf ? 'doc-badge-pdf' : 'doc-badge-other'}">${isPdf ? 'PDF' : 'DOC'}</span>
            <span class="doc-domain-label">${escapeHtml(doc.domain || 'web')}</span>
          </div>
          <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" class="doc-title-link">${escapeHtml(doc.title)}</a>
          <p class="doc-snippet-text">${escapeHtml(doc.snippet)}</p>
          <div style="margin-top: 10px;">
            <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" style="font-size: 12px; font-weight: 600; color: var(--accent); text-decoration: none;">View Document ↗</a>
          </div>
        `;
        docsSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 8. Developer / Code Category
  function renderCodeCategory(data) {
    codeSection.style.display = "flex";
    codeSection.innerHTML = "";
    const repos = data.repositories || [];
    if (repos.length > 0) {
      repos.forEach(repo => {
        const card = document.createElement("div");
        card.className = "code-card";
        card.innerHTML = `
          <div class="code-header-row">
            <a href="${escapeHtml(repo.url)}" target="_blank" rel="noopener noreferrer" class="code-title-link">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline-block; vertical-align:middle; margin-right:4px;"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              <span>${escapeHtml(repo.name)}</span>
            </a>
            <span class="dest-stat-pill" style="font-size:0.75rem;">GitHub</span>
          </div>
          <p class="code-desc">${escapeHtml(repo.description)}</p>
          <div class="code-meta-row">
            <span class="code-lang-pill">
              <span class="lang-color-dot"></span>
              ${escapeHtml(repo.language)}
            </span>
            <span class="code-stat-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" style="vertical-align:middle; margin-right:3px; opacity:0.8;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
              ${Number(repo.stars).toLocaleString()}
            </span>
            <span class="code-stat-item">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle; margin-right:3px; opacity:0.8;"><circle cx="12" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="18" cy="6" r="3"/><path d="M18 9v2a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9"/><path d="M12 12v3"/></svg>
              ${Number(repo.forks).toLocaleString()}
            </span>
          </div>
        `;
        codeSection.appendChild(card);
      });
    }

    // Append web results for dev discussions
    if (data.web_results && data.web_results.length > 0) {
      data.web_results.forEach(item => {
        codeSection.appendChild(createWebResultCard(item));
      });
    } else if (repos.length === 0) {
      emptyState.style.display = "block";
    }
  }

  // 9. Shopping Category
  function renderShoppingCategory(data) {
    shoppingSection.style.display = "grid";
    shoppingSection.innerHTML = "";
    const products = data.products || [];
    if (products.length > 0) {
      products.forEach(p => {
        const card = document.createElement("div");
        card.className = "shop-card";
        card.innerHTML = `
          <div class="shop-merchant-row">
            <span class="shop-merchant-name">${escapeHtml(p.merchant)}</span>
            <span class="shop-rating-pill">${escapeHtml(p.rating)}</span>
          </div>
          <div class="shop-title" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</div>
          <p style="font-size:0.8rem; color:var(--text-secondary); margin-bottom:10px;">${escapeHtml(p.snippet.slice(0, 90))}...</p>
          <div class="shop-price-row">
            <span class="shop-price-tag">${escapeHtml(p.price)}</span>
            <a href="${escapeHtml(p.url)}" target="_blank" rel="noopener noreferrer" class="shop-buy-btn">View Deal ↗</a>
          </div>
        `;
        shoppingSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 10. Jobs Category
  function renderJobsCategory(data) {
    jobsSection.style.display = "flex";
    jobsSection.innerHTML = "";
    const jobs = data.jobs || [];
    if (jobs.length > 0) {
      jobs.forEach(j => {
        const card = document.createElement("div");
        card.className = "job-card";
        card.innerHTML = `
          <div class="job-info-left">
            <div class="job-company-title">🏢 ${escapeHtml(j.company)}</div>
            <div class="job-role-title">${escapeHtml(j.title)}</div>
            <div class="job-meta-pills">
              <span class="job-pill">📍 ${escapeHtml(j.location)}</span>
              <span class="job-pill">💼 ${escapeHtml(j.type)}</span>
            </div>
          </div>
          <a href="${escapeHtml(j.url)}" target="_blank" rel="noopener noreferrer" class="job-apply-btn">Apply Now ↗</a>
        `;
        jobsSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 11. Places Category
  function renderPlacesCategory(data) {
    if (data.destination) {
      populateDestinationCard(data.destination);
      destinationCard.style.display = "block";
    }
    if (data.results && data.results.length > 0) {
      webResultsSection.style.display = "flex";
      data.results.forEach(item => {
        webResultsSection.appendChild(createWebResultCard(item));
      });
    } else if (!data.destination) {
      emptyState.style.display = "block";
    }
  }

  // Helper: Web Result Card Creator
  function createWebResultCard(item) {
    const card = document.createElement("div");
    card.className = "result-card";

    const favicon = item.favicon || (item.domain ? `https://www.google.com/s2/favicons?domain=${encodeURIComponent(item.domain)}&sz=64` : '');
    const dateBadge = item.published_date ? `<span class="result-date-badge">${escapeHtml(item.published_date)}</span>` : '';

    card.innerHTML = `
      <div class="result-meta">
        <div class="result-meta-left">
          ${favicon ? `<img src="${escapeHtml(favicon)}" class="result-favicon" alt="" onerror="this.style.display='none'" />` : ''}
          <span class="domain-pill">${escapeHtml(item.domain || "web")}</span>
          ${dateBadge}
        </div>
        <div class="result-actions">
          <button class="reader-mode-btn" title="Ad-free Reader View">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
            <span>Reader View</span>
          </button>
          <button class="save-bookmark-btn" title="Save to Collection">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
            <span>Save</span>
          </button>
        </div>
      </div>
      <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" class="result-title">${escapeHtml(item.title)}</a>
      <p class="result-snippet">${escapeHtml(item.snippet)}</p>
    `;

    // Reader Mode Click
    card.querySelector(".reader-mode-btn").addEventListener("click", () => {
      openReaderMode(item.url, item.title, item.domain);
    });

    // Save Bookmark Click
    card.querySelector(".save-bookmark-btn").addEventListener("click", () => {
      openSaveModal(item);
    });

    return card;
  }

  // Helper: Destination Card Population
  function populateDestinationCard(dest) {
    const images = (dest.images && dest.images.length > 0) ? dest.images : (dest.image ? [dest.image] : []);
    const destThumbsRow = document.getElementById("destThumbsRow");

    if (images.length > 0) {
      destHeroImg.src = images[0];
      destHeroImgWrap.style.display = "block";
      destHeroImg.onerror = () => { destHeroImgWrap.style.display = "none"; };

      if (destThumbsRow) {
        destThumbsRow.innerHTML = images.map((img, idx) => `
          <div class="dest-thumb-item ${idx === 0 ? 'active' : ''}" data-src="${escapeHtml(img)}">
            <img src="${escapeHtml(img)}" alt="Photo ${idx + 1}" referrerpolicy="no-referrer" />
          </div>
        `).join("");

        destThumbsRow.querySelectorAll(".dest-thumb-item").forEach(item => {
          item.addEventListener("click", () => {
            destThumbsRow.querySelectorAll(".dest-thumb-item").forEach(t => t.classList.remove("active"));
            item.classList.add("active");
            destHeroImg.src = item.getAttribute("data-src");
          });
        });
      }
    } else {
      destHeroImgWrap.style.display = "none";
      if (destThumbsRow) destThumbsRow.innerHTML = "";
    }

    destTitle.textContent = dest.name || "Destination";
    destCountry.textContent = dest.country || "";
    destWeather.textContent = dest.weather || "Mild";
    destTagline.textContent = dest.tagline || "";
    destBestTime.textContent = `Best time: ${dest.best_time || 'All year'}`;
    destDuration.textContent = `Recommended: ${dest.ideal_duration || '3-4 Days'}`;

    destAttractions.innerHTML = (dest.attractions || []).map(att => `
      <button class="attraction-chip" data-attr="${escapeHtml(att)}">${escapeHtml(att)}</button>
    `).join("");

    destAttractions.querySelectorAll(".attraction-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const attr = chip.getAttribute("data-attr");
        headerInput.value = `${dest.name} ${attr}`;
        executeSearch(`${dest.name} ${attr}`, "all");
      });
    });

    destMapsBtn.href = dest.maps_url || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(dest.name)}`;
    destHotelsBtn.href = dest.hotels_url || `https://www.google.com/travel/hotels?q=hotels+in+${encodeURIComponent(dest.name)}`;
    destFlightsBtn.href = dest.flights_url || `https://www.google.com/travel/flights?q=flights+to+${encodeURIComponent(dest.name)}`;
  }


  // Async AI Overview Fetcher
  async function fetchAiOverview(query, results) {
    try {
      const resp = await apiFetch("/api/overview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, results })
      });
      const data = await resp.json();
      if (data.status === "success" && data.data) {
        aiContent.innerHTML = formatMarkdown(data.data.overview);
        aiSources.innerHTML = (data.data.sources || []).map(s => `
          <a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="source-chip" title="${escapeHtml(s.title)}">
            <span class="source-num">${s.index}</span>
            <span class="source-name">${escapeHtml(s.domain || "Source")}</span>
          </a>
        `).join("");
      } else {
        aiOverviewCard.style.display = "none";
      }
    } catch (e) {
      aiOverviewCard.style.display = "none";
    }
  }

  // Copy Overview Button
  copyOverviewBtn.addEventListener("click", () => {
    const text = aiContent.innerText;
    navigator.clipboard.writeText(text);
    copyOverviewBtn.innerHTML = `✓`;
    setTimeout(() => {
      copyOverviewBtn.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="13" height="13" x="9" y="9" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>`;
    }, 2000);
  });

  // Sidebar Related Queries
  function updateRelatedQueries(query) {
    const suggestions = [
      `${query} guide`,
      `${query} latest news`,
      `best ${query} 2026`,
      `${query} vs alternatives`
    ];
    relatedQueriesList.innerHTML = suggestions.map(q => `
      <div class="related-chip" data-q="${escapeHtml(q)}">${escapeHtml(q)}</div>
    `).join("");

    relatedQueriesList.querySelectorAll(".related-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        const q = chip.getAttribute("data-q");
        headerInput.value = q;
        executeSearch(q, activeTab);
      });
    });
  }

  // --- Reader Mode Logic ---
  async function openReaderMode(url, title, domain) {
    readerTitle.textContent = title || "Loading article...";
    readerDomainBadge.textContent = domain || "web";
    readerTimeBadge.textContent = "Estimating...";
    readerExternalLink.href = url;
    readerBody.innerHTML = `
      <div class="skeleton" style="height: 20px; width: 95%; margin-bottom: 12px;"></div>
      <div class="skeleton" style="height: 16px; width: 90%; margin-bottom: 8px;"></div>
      <div class="skeleton" style="height: 16px; width: 98%; margin-bottom: 8px;"></div>
      <div class="skeleton" style="height: 16px; width: 85%;"></div>
    `;
    readerModal.classList.add("open");

    try {
      const resp = await apiFetch(`/api/reader?url=${encodeURIComponent(url)}`);
      const data = await resp.json();
      readerTitle.textContent = data.title || title;
      readerDomainBadge.textContent = data.domain || domain;
      readerTimeBadge.textContent = data.reading_time || "2 min read";
      readerBody.innerHTML = data.content_html || "<p>Could not extract readable article.</p>";
    } catch (e) {
      readerBody.innerHTML = `<p>Failed to load reader view. Please open the page directly.</p>`;
    }
  }

  closeReaderBtn.addEventListener("click", () => readerModal.classList.remove("open"));
  readerFontInc.addEventListener("click", () => {
    currentReaderFontSize = Math.min(1.6, currentReaderFontSize + 0.1);
    readerBody.style.fontSize = `${currentReaderFontSize}rem`;
  });
  readerFontDec.addEventListener("click", () => {
    currentReaderFontSize = Math.max(0.9, currentReaderFontSize - 0.1);
    readerBody.style.fontSize = `${currentReaderFontSize}rem`;
  });

  // Lightbox Close
  closeLightboxBtn.addEventListener("click", () => lightboxModal.classList.remove("open"));

  // Close modals on overlay click
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("open");
      }
    });
  });

  // --- USER AUTHENTICATION & DASHBOARD ---

  // Check auth state on launch
  async function checkAuth() {
    try {
      const resp = await apiFetch("/api/auth/me");
      const data = await resp.json();
      if (data.authenticated && data.user) {
        currentUser = data.user;
        updateUserUI(true);
        loadCollections();
      } else {
        currentUser = null;
        updateUserUI(false);
      }
    } catch (e) {
      currentUser = null;
      updateUserUI(false);
    }
  }

  function updateUserUI(isLoggedIn) {
    if (isLoggedIn && currentUser) {
      const name = currentUser.name || currentUser.email.split("@")[0];
      userAuthText.textContent = name;
      dashAvatar.textContent = name.charAt(0).toUpperCase();
      dashUserName.textContent = name;
      dashUserEmail.textContent = currentUser.email;
    } else {
      userAuthText.textContent = "Sign In";
      dashUserName.textContent = "Guest User";
      dashUserEmail.textContent = "Sign in to sync your search hub";
    }
  }

  userAuthBtn.addEventListener("click", () => {
    if (currentUser) {
      openDashboard();
    } else {
      authModal.classList.add("open");
    }
  });

  dashboardBtn.addEventListener("click", openDashboard);

  function openDashboard() {
    if (!currentUser) {
      authModal.classList.add("open");
      return;
    }
    dashboardModal.classList.add("open");
    loadCollections();
    loadHistory();
    loadSavedBookmarks();
    loadPreferences();
  }

  closeAuthModal.addEventListener("click", () => authModal.classList.remove("open"));
  closeDashboardModal.addEventListener("click", () => dashboardModal.classList.remove("open"));

  // Tab switching between Sign In & Register
  let isRegisterMode = false;
  tabSignIn.addEventListener("click", () => {
    isRegisterMode = false;
    tabSignIn.classList.add("active");
    tabRegister.classList.remove("active");
    nameGroup.style.display = "none";
    authSubmitBtn.textContent = "Sign In";
    authErrorMsg.style.display = "none";
  });
  tabRegister.addEventListener("click", () => {
    isRegisterMode = true;
    tabRegister.classList.add("active");
    tabSignIn.classList.remove("active");
    nameGroup.style.display = "flex";
    authSubmitBtn.textContent = "Create Account";
    authErrorMsg.style.display = "none";
  });

  authForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    authErrorMsg.style.display = "none";
    const email = authEmail.value.trim();
    const password = authPassword.value.trim();
    const name = authName.value.trim();

    const endpoint = isRegisterMode ? "/api/auth/register" : "/api/auth/login";
    const payload = isRegisterMode ? { email, password, name } : { email, password };

    try {
      const resp = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (resp.ok && data.user) {
        currentUser = data.user;
        updateUserUI(true);
        authModal.classList.remove("open");
        loadCollections();
      } else {
        authErrorMsg.textContent = data.error || "Authentication failed.";
        authErrorMsg.style.display = "block";
      }
    } catch (err) {
      authErrorMsg.textContent = "Network error. Please try again.";
      authErrorMsg.style.display = "block";
    }
  });

  signOutBtn.addEventListener("click", async () => {
    await apiFetch("/api/auth/logout", { method: "POST" });
    currentUser = null;
    updateUserUI(false);
    dashboardModal.classList.remove("open");
  });

  // Dashboard Tab Switching
  dashTabs.forEach(tab => {
    tab.addEventListener("click", () => {
      dashTabs.forEach(t => t.classList.remove("active"));
      dashPanes.forEach(p => p.classList.remove("active"));
      tab.classList.add("active");
      const view = tab.getAttribute("data-view");
      const targetPane = document.getElementById(`pane${view.charAt(0).toUpperCase() + view.slice(1)}`);
      if (targetPane) targetPane.classList.add("active");
    });
  });

  // --- Collections Management ---
  async function loadCollections() {
    if (!currentUser) return;
    try {
      const resp = await apiFetch("/api/collections");
      const data = await resp.json();
      userCollections = data.collections || [];

      // Update collections grid
      collectionsGrid.innerHTML = userCollections.map(c => `
        <div class="coll-item-card" data-name="${escapeHtml(c.name)}">
          <div class="coll-item-title">📁 ${escapeHtml(c.name)}</div>
          <div class="coll-item-desc">${escapeHtml(c.description || 'Collection')}</div>
        </div>
      `).join("");

      // Update save modal dropdown
      saveCollectionSelect.innerHTML = userCollections.map(c => `
        <option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>
      `).join("");

      // Update filter select in Saved Bookmarks
      savedFilterSelect.innerHTML = `<option value="">All Collections</option>` + userCollections.map(c => `
        <option value="${escapeHtml(c.name)}">${escapeHtml(c.name)}</option>
      `).join("");

    } catch (e) {
      console.warn("Could not load collections:", e);
    }
  }

  newCollectionBtn.addEventListener("click", async () => {
    const name = prompt("Enter new collection name (e.g., AI Research, Stays, Physics):");
    if (!name || !name.trim()) return;
    try {
      const resp = await apiFetch("/api/collections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), description: "Personal collection" })
      });
      if (resp.ok) {
        loadCollections();
      }
    } catch (e) {
      alert("Failed to create collection");
    }
  });

  // --- Search History Management ---
  async function loadHistory() {
    if (!currentUser) return;
    try {
      const resp = await apiFetch("/api/history?limit=40");
      const data = await resp.json();
      const items = data.history || [];

      if (items.length === 0) {
        historyList.innerHTML = `<p style="font-size:0.85rem; color:var(--text-secondary); padding: 14px;">No search history recorded.</p>`;
        return;
      }

      historyList.innerHTML = items.map(h => `
        <div class="history-row-item">
          <span class="history-query-text" data-q="${escapeHtml(h.query)}" data-cat="${escapeHtml(h.category)}">
            ${escapeHtml(h.query)}
          </span>
          <div class="history-meta">
            <span class="history-cat-badge">${escapeHtml(h.category)}</span>
            <button class="delete-item-btn" data-id="${h.id}" title="Delete query">✕</button>
          </div>
        </div>
      `).join("");

      historyList.querySelectorAll(".history-query-text").forEach(el => {
        el.addEventListener("click", () => {
          const q = el.getAttribute("data-q");
          const cat = el.getAttribute("data-cat") || "all";
          dashboardModal.classList.remove("open");
          executeSearch(q, cat);
        });
      });

      historyList.querySelectorAll(".delete-item-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-id");
          await apiFetch(`/api/history/${id}`, { method: "DELETE" });
          loadHistory();
        });
      });

    } catch (e) {
      console.warn("Could not load history:", e);
    }
  }

  clearHistoryBtn.addEventListener("click", async () => {
    if (confirm("Are you sure you want to clear your entire search history?")) {
      await apiFetch("/api/history/clear", { method: "POST" });
      loadHistory();
    }
  });

  toggleHistoryBtn.addEventListener("click", async () => {
    const resp = await apiFetch("/api/history/toggle", { method: "POST" });
    const data = await resp.json();
    toggleHistoryBtn.textContent = data.history_enabled ? "Pause History" : "Resume History";
  });

  // --- Saved Bookmarks Management ---
  async function loadSavedBookmarks(collection = "") {
    if (!currentUser) return;
    try {
      const url = collection ? `/api/saved?collection=${encodeURIComponent(collection)}` : "/api/saved";
      const resp = await fetch(url);
      const data = await resp.json();
      const saved = data.saved || [];

      if (saved.length === 0) {
        savedResultsList.innerHTML = `<p style="font-size:0.85rem; color:var(--text-secondary); padding: 14px;">No saved bookmarks in this collection.</p>`;
        return;
      }

      savedResultsList.innerHTML = saved.map(item => `
        <div class="saved-row-item">
          <div>
            <a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer" style="font-weight:600; font-size:0.92rem;">
              ${escapeHtml(item.title)}
            </a>
            <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
              📁 ${escapeHtml(item.collection_name)} • ${escapeHtml(item.domain)}
            </div>
          </div>
          <button class="delete-item-btn" data-id="${item.id}" title="Remove bookmark">✕</button>
        </div>
      `).join("");

      savedResultsList.querySelectorAll(".delete-item-btn").forEach(btn => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-id");
          await apiFetch(`/api/saved/${id}`, { method: "DELETE" });
          loadSavedBookmarks(savedFilterSelect.value);
        });
      });

    } catch (e) {
      console.warn("Could not load saved bookmarks:", e);
    }
  }

  savedFilterSelect.addEventListener("change", () => {
    loadSavedBookmarks(savedFilterSelect.value);
  });

  // Save Modal
  function openSaveModal(item) {
    if (!currentUser) {
      authModal.classList.add("open");
      return;
    }
    pendingSaveItem = item;
    saveItemTitle.textContent = item.title;
    saveResultModal.classList.add("open");
  }

  closeSaveResultModal.addEventListener("click", () => saveResultModal.classList.remove("open"));

  confirmSaveBtn.addEventListener("click", async () => {
    if (!pendingSaveItem) return;
    const selectedCollection = saveCollectionSelect.value || "General";
    try {
      const resp = await apiFetch("/api/saved", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: pendingSaveItem.title,
          url: pendingSaveItem.url,
          domain: pendingSaveItem.domain,
          snippet: pendingSaveItem.snippet,
          category: activeTab,
          collection_name: selectedCollection
        })
      });
      if (resp.ok) {
        saveResultModal.classList.remove("open");
        alert(`Saved to ${selectedCollection}!`);
      }
    } catch (e) {
      alert("Failed to save bookmark.");
    }
  });

  // --- Preferences Management ---
  async function loadPreferences() {
    if (!currentUser) return;
    try {
      const resp = await apiFetch("/api/preferences");
      const data = await resp.json();
      const p = data.preferences || {};
      prefSafeSearch.value = p.safe_search || "moderate";
      prefNewTab.checked = p.open_new_tab !== false;
      prefHistoryEnabled.checked = p.history_enabled !== false;
      prefPersonalized.checked = !!p.personalized;
    } catch (e) {}
  }

  function savePreferences() {
    if (!currentUser) return;
    const payload = {
      safe_search: prefSafeSearch.value,
      open_new_tab: prefNewTab.checked,
      history_enabled: prefHistoryEnabled.checked,
      personalized: prefPersonalized.checked
    };
    apiFetch("/api/preferences", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
  }

  prefSafeSearch.addEventListener("change", savePreferences);
  prefNewTab.addEventListener("change", savePreferences);
  prefHistoryEnabled.addEventListener("change", savePreferences);
  prefPersonalized.addEventListener("change", savePreferences);

  // Export User Data
  exportDataBtn.addEventListener("click", async () => {
    try {
      const resp = await apiFetch("/api/export");
      const data = await resp.json();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vastuda-data-export-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to export data");
    }
  });

  // --- Helper Functions ---
  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let html = escapeHtml(text);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    // Italic
    html = html.replace(/\*(.*?)\*/g, "<em>$1</em>");
    // Lists
    html = html.replace(/^\s*[-•]\s+(.*)$/gm, "<li>$1</li>");
    html = html.replace(/(<li>.*<\/li>)/s, "<ul>$1</ul>");
    // Paragraphs
    html = html.split("\n\n").map(p => p.startsWith("<ul>") ? p : `<p>${p}</p>`).join("");
    return html;
  }

  // --- Initial URL Query Param Check (e.g. ?q=World+Tech+news+today) ---
  function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const q = params.get("q");
    const cat = params.get("category") || "all";
    if (q && q.trim()) {
      homeInput.value = q.trim();
      headerInput.value = q.trim();
      tabBtns.forEach(btn => {
        if (btn.getAttribute("data-tab") === cat) {
          btn.classList.add("active");
        } else {
          btn.classList.remove("active");
        }
      });
      executeSearch(q.trim(), cat);
    }
  }

  window.addEventListener("popstate", () => {
    checkUrlParams();
  });

  // --- BING-STYLE DYNAMIC WALLPAPERS ---
  const WALLPAPERS = [
    {
      url: "https://images.unsplash.com/photo-1533105079780-92b9be482077?auto=format&fit=crop&w=1920&q=80",
      location: "Santorini, Aegean Sea, Greece"
    },
    {
      url: "https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1920&q=80",
      location: "Yosemite Valley, California"
    },
    {
      url: "https://images.unsplash.com/photo-1513584684374-8bab748fbf90?auto=format&fit=crop&w=1920&q=80",
      location: "Kyoto Autumn Lanterns, Japan"
    },
    {
      url: "https://images.unsplash.com/photo-1516483638261-f4dbaf036963?auto=format&fit=crop&w=1920&q=80",
      location: "Cinque Terre Coastline, Italy"
    },
    {
      url: "https://images.unsplash.com/photo-1524492412937-b28074a5d7da?auto=format&fit=crop&w=1920&q=80",
      location: "Taj Mahal Sunrise, Agra, India"
    },
    {
      url: "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1920&q=80",
      location: "Tropical Coastline, Maldives"
    }
  ];

  function initWallpaperManager() {
    const wallpaperBg = document.getElementById("wallpaperBg");
    const wallpaperLocation = document.getElementById("wallpaperLocation");
    const wallpaperToggleBtn = document.getElementById("wallpaperToggleBtn");

    const savedMode = localStorage.getItem("staunt_wallpaper_mode");
    if (savedMode === "disabled") {
      document.body.classList.add("minimalist-mode");
    }

    const dayIndex = (new Date().getDate()) % WALLPAPERS.length;
    const todayWp = WALLPAPERS[dayIndex];
    if (wallpaperBg) wallpaperBg.style.backgroundImage = `url('${todayWp.url}')`;
    if (wallpaperLocation) wallpaperLocation.textContent = todayWp.location;

    if (wallpaperToggleBtn) {
      wallpaperToggleBtn.addEventListener("click", () => {
        document.body.classList.toggle("minimalist-mode");
        const isMin = document.body.classList.contains("minimalist-mode");
        localStorage.setItem("staunt_wallpaper_mode", isMin ? "disabled" : "enabled");
      });
    }
  }

  // --- LIVE WEATHER WIDGET ---
  async function initWeatherWidget() {
    const weatherIcon = document.getElementById("weatherIcon");
    const weatherTemp = document.getElementById("weatherTemp");
    const weatherCity = document.getElementById("weatherCity");
    const headerWeatherPill = document.getElementById("headerWeatherPill");

    try {
      const res = await apiFetch("/api/weather");
      if (res.ok) {
        const data = await res.json();
        if (weatherIcon) weatherIcon.textContent = data.icon || "🌤️";
        if (weatherTemp) weatherTemp.textContent = `${data.temp}°C`;
        if (weatherCity) weatherCity.textContent = data.city || "New Delhi";
      }
    } catch (e) {
      console.warn("Weather fetch note:", e);
    }

    if (headerWeatherPill) {
      headerWeatherPill.addEventListener("click", () => {
        const city = weatherCity ? weatherCity.textContent : "New Delhi";
        headerInput.value = `weather in ${city}`;
        homeInput.value = `weather in ${city}`;
        executeSearch(`weather in ${city}`, "all");
      });
    }
  }

  // --- BING FINANCIAL MARKETS & TRENDING NEWS ---
  async function initTrendingAndMarkets() {
    const marketsRibbon = document.getElementById("marketsRibbon");
    const trendingChipsWrap = document.getElementById("trendingChipsWrap");
    const trendingNewsGrid = document.getElementById("trendingNewsGrid");
    const newsCatFilters = document.querySelectorAll(".news-filter-btn");

    try {
      const res = await apiFetch("/api/trending");
      if (!res.ok) return;
      const data = await res.json();

      // 1. Markets
      if (marketsRibbon && data.markets) {
        marketsRibbon.innerHTML = data.markets.map(m => `
          <div class="market-pill" data-query="${escapeHtml(m.symbol)} stock price today">
            <span class="market-sym">${escapeHtml(m.symbol)}</span>
            <span class="market-val">${escapeHtml(m.value)}</span>
            <span class="market-chg ${m.is_up ? 'up' : 'down'}">${escapeHtml(m.change)}</span>
          </div>
        `).join("");

        marketsRibbon.querySelectorAll(".market-pill").forEach(pill => {
          pill.addEventListener("click", () => {
            const q = pill.getAttribute("data-query");
            homeInput.value = q;
            headerInput.value = q;
            executeSearch(q, "all");
          });
        });
      }

      // 2. Trending Topics
      if (trendingChipsWrap && data.topics) {
        trendingChipsWrap.innerHTML = data.topics.map(t => `
          <button type="button" class="trending-chip" data-query="${escapeHtml(t.query)}">
            <span>${t.icon || '🔥'} ${escapeHtml(t.query)}</span>
          </button>
        `).join("");

        trendingChipsWrap.querySelectorAll(".trending-chip").forEach(chip => {
          chip.addEventListener("click", () => {
            const q = chip.getAttribute("data-query");
            homeInput.value = q;
            headerInput.value = q;
            executeSearch(q, "all");
          });
        });
      }

      // 3. Trending News
      let allNews = data.news || [];
      function renderNews(items) {
        if (!trendingNewsGrid) return;
        if (!items || items.length === 0) {
          trendingNewsGrid.innerHTML = `<div class="news-skeleton">No headlines available right now.</div>`;
          return;
        }
        trendingNewsGrid.innerHTML = items.map(n => `
          <a href="${escapeHtml(n.url || '#')}" target="_blank" rel="noopener noreferrer" class="news-card">
            <div class="news-card-title">${escapeHtml(n.title)}</div>
            <div class="news-card-footer">
              <span class="news-source-tag">${escapeHtml(n.source || 'News')}</span>
              <span class="news-time">${escapeHtml(n.time || 'Trending')}</span>
            </div>
          </a>
        `).join("");
      }

      renderNews(allNews);

      // News filters
      newsCatFilters.forEach(btn => {
        btn.addEventListener("click", async () => {
          newsCatFilters.forEach(b => b.classList.remove("active"));
          btn.classList.add("active");
          const cat = btn.getAttribute("data-cat");
          if (cat === "all") {
            renderNews(allNews);
          } else {
            try {
              trendingNewsGrid.innerHTML = `<div class="news-skeleton">Loading ${cat} stories...</div>`;
              const res = await apiFetch(`/api/search?q=${encodeURIComponent(cat + " news")}&category=news`);
              if (res.ok) {
                const ndata = await res.json();
                renderNews(ndata.news || allNews);
              }
            } catch (e) {
              renderNews(allNews);
            }
          }
        });
      });

    } catch (e) {
      console.warn("Trending fetch note:", e);
    }
  }

  // --- QUICK TOOLS (Calculator, Currency, Travel Hub, Daily Fact) ---
  function initQuickTools() {
    const calcModal = document.getElementById("calcModal");
    const currencyModal = document.getElementById("currencyModal");
    const closeCalcModal = document.getElementById("closeCalcModal");
    const closeCurrencyModal = document.getElementById("closeCurrencyModal");

    const toolCalcBtn = document.getElementById("toolCalcBtn");
    const toolCurrencyBtn = document.getElementById("toolCurrencyBtn");
    const toolTravelBtn = document.getElementById("toolTravelBtn");
    const toolFactBtn = document.getElementById("toolFactBtn");

    if (toolCalcBtn && calcModal) toolCalcBtn.addEventListener("click", () => calcModal.classList.add("open"));
    if (closeCalcModal && calcModal) closeCalcModal.addEventListener("click", () => calcModal.classList.remove("open"));

    if (toolCurrencyBtn && currencyModal) toolCurrencyBtn.addEventListener("click", () => currencyModal.classList.add("open"));
    if (closeCurrencyModal && currencyModal) closeCurrencyModal.addEventListener("click", () => currencyModal.classList.remove("open"));

    if (toolTravelBtn) {
      toolTravelBtn.addEventListener("click", () => {
        const dests = ["Goa India", "Paris France", "Dubai UAE", "Kyoto Japan", "Manali Himachal", "Santorini Greece"];
        const randomDest = dests[Math.floor(Math.random() * dests.length)];
        homeInput.value = randomDest;
        headerInput.value = randomDest;
        executeSearch(randomDest, "all");
      });
    }

    if (toolFactBtn) {
      toolFactBtn.addEventListener("click", () => {
        homeInput.value = "fact of the day";
        headerInput.value = "fact of the day";
        executeSearch("fact of the day", "all");
      });
    }

    // Calculator logic
    const calcDisplay = document.getElementById("calcDisplay");
    let calcExpression = "";
    document.querySelectorAll(".calc-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        const val = btn.getAttribute("data-val");
        if (val === "C") {
          calcExpression = "";
          if (calcDisplay) calcDisplay.textContent = "0";
        } else if (val === "=") {
          try {
            const clean = calcExpression.replace(/×/g, "*").replace(/÷/g, "/");
            const res = Function(`'use strict'; return (${clean})`)();
            if (calcDisplay) calcDisplay.textContent = res;
            calcExpression = String(res);
          } catch (e) {
            if (calcDisplay) calcDisplay.textContent = "Error";
            calcExpression = "";
          }
        } else {
          calcExpression += val;
          if (calcDisplay) calcDisplay.textContent = calcExpression;
        }
      });
    });

    // Currency Converter logic
    const currAmount = document.getElementById("currAmount");
    const currFrom = document.getElementById("currFrom");
    const currTo = document.getElementById("currTo");
    const currResult = document.getElementById("currResult");
    const currencyRateNote = document.getElementById("currencyRateNote");

    const RATES = {
      USD: 1.0,
      INR: 83.82,
      EUR: 0.92,
      GBP: 0.78,
      AED: 3.67
    };

    function updateCurrency() {
      if (!currAmount || !currResult) return;
      const amt = parseFloat(currAmount.value) || 0;
      const f = currFrom ? currFrom.value : "USD";
      const t = currTo ? currTo.value : "INR";
      const inUSD = amt / (RATES[f] || 1.0);
      const out = inUSD * (RATES[t] || 83.82);
      currResult.value = out.toFixed(2);
      if (currencyRateNote) {
        currencyRateNote.textContent = `1 ${f} = ${((RATES[t] || 83.82) / (RATES[f] || 1.0)).toFixed(2)} ${t}`;
      }
    }

    if (currAmount) currAmount.addEventListener("input", updateCurrency);
    if (currFrom) currFrom.addEventListener("change", updateCurrency);
    if (currTo) currTo.addEventListener("change", updateCurrency);
  }

  // --- COPILOT / DEEP AI TOGGLE ---
  let isDeepAiMode = false;
  function initCopilotToggle() {
    const copilotBtn = document.getElementById("copilotToggleBtn");
    const copilotLabel = document.getElementById("copilotLabel");

    if (copilotBtn) {
      copilotBtn.addEventListener("click", () => {
        isDeepAiMode = !isDeepAiMode;
        if (isDeepAiMode) {
          copilotBtn.classList.add("active");
          if (copilotLabel) copilotLabel.textContent = "Copilot";
        } else {
          copilotBtn.classList.remove("active");
          if (copilotLabel) copilotLabel.textContent = "Fast";
        }
      });
    }
  }

  // Initializations
  initWallpaperManager();
  initWeatherWidget();
  initTrendingAndMarkets();
  initQuickTools();
  initCopilotToggle();

  // Initial Auth & URL Check
  checkAuth();
  checkUrlParams();
});

