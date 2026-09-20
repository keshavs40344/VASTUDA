// VASTUDA — Independent AI Discovery & Neural Web Engine Client Logic

document.addEventListener("DOMContentLoaded", () => {
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
    resultsView.classList.remove("active");
    homeView.style.display = "flex";
    headerSearchWrap.style.display = "none";
    homeInput.value = "";
    headerInput.value = "";
    currentQuery = "";
  });

  // Quick Discovery Pills
  document.querySelectorAll(".pill").forEach(btn => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-query");
      homeInput.value = q;
      headerInput.value = q;
      executeSearch(q, "all");
    });
  });

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
      executeSearch(transcript, activeTab);
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

  // --- Search Suggestions ---
  function setupSuggestions(input, box) {
    let timeout = null;
    input.addEventListener("input", () => {
      const val = input.value.trim();
      clearTimeout(timeout);
      if (val.length < 2) {
        box.classList.remove("active");
        box.innerHTML = "";
        return;
      }
      timeout = setTimeout(async () => {
        try {
          const resp = await fetch(`/api/suggest?q=${encodeURIComponent(val)}`);
          const items = await resp.json();
          if (items && items.length > 0) {
            box.innerHTML = items.map(s => `
              <div class="suggest-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <span>${escapeHtml(s)}</span>
              </div>
            `).join("");
            box.classList.add("active");

            box.querySelectorAll(".suggest-item").forEach((item, idx) => {
              item.addEventListener("click", () => {
                const text = items[idx];
                input.value = text;
                box.classList.remove("active");
                executeSearch(text, activeTab);
              });
            });
          } else {
            box.classList.remove("active");
          }
        } catch (e) {
          box.classList.remove("active");
        }
      }, 200);
    });

    document.addEventListener("click", (e) => {
      if (!input.contains(e.target) && !box.contains(e.target)) {
        box.classList.remove("active");
      }
    });
  }
  setupSuggestions(homeInput, suggestBoxHome);
  setupSuggestions(headerInput, suggestBoxHeader);

  // --- Category Tabs Switching ---
  tabBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      activeTab = btn.getAttribute("data-tab");
      if (currentQuery) {
        executeSearch(currentQuery, activeTab);
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
  async function executeSearch(query, category = "all") {
    currentQuery = query;
    activeTab = category;

    // Switch view to results
    homeView.style.display = "none";
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
      window.history.replaceState({ query, category }, "", url);
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
      const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}&category=${encodeURIComponent(category)}`);
      const data = await resp.json();

      webResultsSection.innerHTML = "";

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
          datePill.textContent = `🕒 ${item.published_date}`;
          card.querySelector(".result-meta")?.appendChild(datePill);
        }
        webResultsSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 5. Images Category
  function renderImagesCategory(data) {
    imagesSection.style.display = "grid";
    imagesSection.innerHTML = "";
    const images = data.images || [];
    if (images.length > 0) {
      images.forEach(img => {
        const item = document.createElement("div");
        item.className = "image-card";
        item.innerHTML = `
          <img src="${escapeHtml(img.url)}" alt="${escapeHtml(img.title || 'Image')}" loading="lazy" referrerpolicy="no-referrer" onerror="this.parentElement.style.display='none'" />
          <div class="image-overlay">
            <span class="image-title">${escapeHtml(img.title || 'Image')}</span>
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

  // 6. Videos Category
  function renderVideosCategory(data) {
    videosSection.style.display = "grid";
    videosSection.innerHTML = "";
    const videos = data.videos || [];
    if (videos.length > 0) {
      videos.forEach(v => {
        const card = document.createElement("div");
        card.className = "video-card";
        card.innerHTML = `
          <div class="video-thumb-wrap">
            <img class="video-thumb-img" src="${escapeHtml(v.thumbnail)}" alt="${escapeHtml(v.title)}" />
            <span class="video-duration-tag">${escapeHtml(v.duration)}</span>
          </div>
          <div class="video-body">
            <a href="${escapeHtml(v.url)}" target="_blank" rel="noopener noreferrer" class="video-title">${escapeHtml(v.title)}</a>
            <span class="video-channel">▶️ ${escapeHtml(v.channel)}</span>
          </div>
        `;
        videosSection.appendChild(card);
      });
    } else {
      emptyState.style.display = "block";
    }
  }

  // 7. Documents Category
  function renderDocsCategory(data) {
    docsSection.style.display = "flex";
    docsSection.innerHTML = "";
    const docs = data.documents || [];
    if (docs.length > 0) {
      docs.forEach(doc => {
        const card = document.createElement("div");
        card.className = "doc-card";
        card.innerHTML = `
          <div class="doc-icon-badge">
            <span>📄</span>
            <span>${escapeHtml(doc.file_type)}</span>
          </div>
          <div class="doc-body">
            <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" class="doc-title">${escapeHtml(doc.title)}</a>
            <p class="doc-snippet">${escapeHtml(doc.snippet)}</p>
            <div class="doc-footer-row">
              <span>${escapeHtml(doc.domain)}</span>
              <span>•</span>
              <a href="${escapeHtml(doc.url)}" target="_blank" rel="noopener noreferrer" class="doc-download-btn">Direct View / Download ↗</a>
            </div>
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
              📦 ${escapeHtml(repo.name)}
            </a>
            <span class="dest-stat-pill" style="font-size:0.75rem;">GitHub</span>
          </div>
          <p class="code-desc">${escapeHtml(repo.description)}</p>
          <div class="code-meta-row">
            <span class="code-lang-pill">
              <span class="lang-color-dot"></span>
              ${escapeHtml(repo.language)}
            </span>
            <span class="code-stat-item">⭐ ${Number(repo.stars).toLocaleString()}</span>
            <span class="code-stat-item">🍴 ${Number(repo.forks).toLocaleString()}</span>
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
    const dateBadge = item.published_date ? `<span class="result-date-badge">🕒 ${escapeHtml(item.published_date)}</span>` : '';

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
    if (dest.image) {
      destHeroImg.src = dest.image;
      destHeroImgWrap.style.display = "block";
      destHeroImg.onerror = () => { destHeroImgWrap.style.display = "none"; };
    } else {
      destHeroImgWrap.style.display = "none";
    }

    destTitle.textContent = dest.name || "Destination";
    destCountry.textContent = dest.country || "";
    destWeather.textContent = dest.weather || "☀️ Mild";
    destTagline.textContent = dest.tagline || "";
    destBestTime.textContent = `🗓️ Best time: ${dest.best_time || 'All year'}`;
    destDuration.textContent = `⏱️ Ideal: ${dest.ideal_duration || '3-4 Days'}`;


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
      const resp = await fetch("/api/overview", {
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
      const resp = await fetch(`/api/reader?url=${encodeURIComponent(url)}`);
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
      const resp = await fetch("/api/auth/me");
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
    await fetch("/api/auth/logout", { method: "POST" });
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
      const resp = await fetch("/api/collections");
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
      const resp = await fetch("/api/collections", {
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
      const resp = await fetch("/api/history?limit=40");
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
          await fetch(`/api/history/${id}`, { method: "DELETE" });
          loadHistory();
        });
      });

    } catch (e) {
      console.warn("Could not load history:", e);
    }
  }

  clearHistoryBtn.addEventListener("click", async () => {
    if (confirm("Are you sure you want to clear your entire search history?")) {
      await fetch("/api/history/clear", { method: "POST" });
      loadHistory();
    }
  });

  toggleHistoryBtn.addEventListener("click", async () => {
    const resp = await fetch("/api/history/toggle", { method: "POST" });
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
          await fetch(`/api/saved/${id}`, { method: "DELETE" });
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
      const resp = await fetch("/api/saved", {
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
      const resp = await fetch("/api/preferences");
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
    fetch("/api/preferences", {
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
      const resp = await fetch("/api/export");
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

  // Initial Auth & URL Check
  checkAuth();
  checkUrlParams();
});
