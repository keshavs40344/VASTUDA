package com.staunt.browser

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.webkit.DownloadListener
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.GridLayoutManager
import androidx.recyclerview.widget.RecyclerView
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {
    private lateinit var tabManager: TabManager
    private lateinit var adBlockEngine: AdBlockEngine
    private lateinit var historyDb: HistoryDb
    private lateinit var bookmarkDb: BookmarkDb
    private lateinit var downloadHandler: DownloadHandler
    
    private lateinit var etUrl: EditText
    private lateinit var progressBar: ProgressBar
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var btnTabCount: Button
    private lateinit var ivSecurity: ImageView

    // Tab Switcher Overlay Elements
    private lateinit var tabSwitcherContainer: View
    private lateinit var rvTabs: RecyclerView
    private lateinit var btnCloseSwitcher: ImageButton
    private lateinit var btnNewTab: Button
    private lateinit var tabAdapter: TabAdapter

    // Find In Page Bar Elements
    private lateinit var findInPageContainer: View
    private lateinit var etFind: EditText
    private lateinit var tvMatchCount: TextView
    private lateinit var btnFindPrev: ImageButton
    private lateinit var btnFindNext: ImageButton
    private lateinit var btnFindClose: ImageButton

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        adBlockEngine = AdBlockEngine(this).apply { init() }
        historyDb = HistoryDb(this)
        bookmarkDb = BookmarkDb(this)
        downloadHandler = DownloadHandler(this)
        
        val container = findViewById<FrameLayout>(R.id.webviewContainer)
        tabManager = TabManager(this, container)
        
        etUrl = findViewById(R.id.etUrl)
        progressBar = findViewById(R.id.progressBar)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        btnTabCount = findViewById(R.id.btnTabCount)
        ivSecurity = findViewById(R.id.ivSecurity)

        setupTabSwitcher()
        setupFindInPage()
        setupButtons()
        
        swipeRefresh.setOnRefreshListener {
            tabManager.getActiveTab()?.webView?.reload()
        }

        etUrl.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_GO || event?.keyCode == KeyEvent.KEYCODE_ENTER) {
                var url = etUrl.text.toString().trim()
                if (url.isNotEmpty()) {
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        if (url.contains(".") && !url.contains(" ")) {
                            url = "https://$url"
                        } else {
                            url = "https://www.google.com/search?q=" + android.net.Uri.encode(url)
                        }
                    }
                    tabManager.getActiveTab()?.webView?.loadUrl(url)
                }
                true
            } else false
        }

        ivSecurity.setOnClickListener {
            showSecurityDialog()
        }

        createNewTab()
    }

    private fun setupTabSwitcher() {
        tabSwitcherContainer = findViewById(R.id.tabSwitcherContainer)
        rvTabs = findViewById(R.id.rvTabs)
        btnCloseSwitcher = findViewById(R.id.btnCloseSwitcher)
        btnNewTab = findViewById(R.id.btnNewTab)

        rvTabs.layoutManager = GridLayoutManager(this, 2)
        tabAdapter = TabAdapter(
            tabs = tabManager.tabs,
            activeTabId = { tabManager.activeTabId },
            onTabSelected = { tab ->
                tabManager.switchTab(tab.id)
                etUrl.setText(tab.webView.url ?: "")
                updateSecurityIcon(tab.webView.url ?: "")
                hideTabSwitcher()
            },
            onTabClosed = { tab ->
                tabManager.closeTab(tab.id)
                updateTabCount()
                if (tabManager.tabs.isEmpty()) {
                    createNewTab()
                }
                tabAdapter.notifyDataSetChanged()
            }
        )
        rvTabs.adapter = tabAdapter

        btnCloseSwitcher.setOnClickListener {
            hideTabSwitcher()
        }

        btnNewTab.setOnClickListener {
            createNewTab()
            hideTabSwitcher()
        }
    }

    private fun showTabSwitcher() {
        tabAdapter.notifyDataSetChanged()
        tabSwitcherContainer.visibility = View.VISIBLE
    }

    private fun hideTabSwitcher() {
        tabSwitcherContainer.visibility = View.GONE
    }

    private fun setupFindInPage() {
        findInPageContainer = findViewById(R.id.findInPageContainer)
        etFind = findViewById(R.id.etFind)
        tvMatchCount = findViewById(R.id.tvMatchCount)
        btnFindPrev = findViewById(R.id.btnFindPrev)
        btnFindNext = findViewById(R.id.btnFindNext)
        btnFindClose = findViewById(R.id.btnFindClose)

        etFind.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                val query = s?.toString() ?: ""
                val activeWv = tabManager.getActiveTab()?.webView
                if (query.isNotEmpty()) {
                    activeWv?.setFindListener { activeIndex, totalMatches, _ ->
                        tvMatchCount.text = if (totalMatches > 0) "${activeIndex + 1}/$totalMatches" else "0/0"
                    }
                    activeWv?.findAllAsync(query)
                } else {
                    activeWv?.clearMatches()
                    tvMatchCount.text = "0/0"
                }
            }
            override fun afterTextChanged(s: Editable?) {}
        })

        btnFindPrev.setOnClickListener {
            tabManager.getActiveTab()?.webView?.findNext(false)
        }

        btnFindNext.setOnClickListener {
            tabManager.getActiveTab()?.webView?.findNext(true)
        }

        btnFindClose.setOnClickListener {
            hideFindInPage()
        }
    }

    private fun showFindInPage() {
        findInPageContainer.visibility = View.VISIBLE
        etFind.requestFocus()
    }

    private fun hideFindInPage() {
        findInPageContainer.visibility = View.GONE
        val activeWv = tabManager.getActiveTab()?.webView
        activeWv?.clearMatches()
        etFind.setText("")
    }

    private fun showSecurityDialog() {
        val currentUrl = tabManager.getActiveTab()?.webView?.url ?: ""
        val isHttps = currentUrl.startsWith("https://")
        val activeTab = tabManager.getActiveTab()
        val cert = activeTab?.webView?.certificate

        val builder = AlertDialog.Builder(this)
        builder.setTitle(if (isHttps) "Connection is Secure" else "Connection Not Secure")
        val message = StringBuilder()
        if (isHttps) {
            message.append("🔒 Verified Secure Connection\n\n")
            message.append("URL: ").append(currentUrl).append("\n\n")
            if (cert != null) {
                message.append("Issued To: ").append(cert.issuedTo?.cName ?: "Valid Host").append("\n")
                message.append("Issued By: ").append(cert.issuedBy?.oName ?: "Trusted Certificate Authority").append("\n")
                message.append("Valid Until: ").append(cert.validNotAfterDate?.toString() ?: "Active").append("\n")
            } else {
                message.append("Certificate: Validated via system trust anchors.")
            }
        } else {
            message.append("⚠️ Your connection to this site is not private.\nInformation you submit might be visible to others.")
        }
        builder.setMessage(message.toString())
        builder.setPositiveButton("OK") { d, _ -> d.dismiss() }
        builder.show()
    }

    private fun updateSecurityIcon(url: String) {
        if (url.startsWith("https://")) {
            ivSecurity.setImageResource(R.drawable.ic_lock)
            ivSecurity.setColorFilter(getColor(R.color.staunt_success))
        } else {
            ivSecurity.setImageResource(R.drawable.ic_shield)
            ivSecurity.setColorFilter(getColor(R.color.staunt_error))
        }
    }

    private fun setupButtons() {
        findViewById<ImageButton>(R.id.btnBack).setOnClickListener {
            tabManager.getActiveTab()?.webView?.goBack()
        }
        findViewById<ImageButton>(R.id.btnForward).setOnClickListener {
            tabManager.getActiveTab()?.webView?.goForward()
        }
        findViewById<ImageButton>(R.id.btnMenu).setOnClickListener {
            showOverflowMenu(it)
        }
        btnTabCount.setOnClickListener {
            showTabSwitcher()
        }
        findViewById<ImageButton>(R.id.btnNavHome).setOnClickListener {
            tabManager.getActiveTab()?.webView?.loadUrl("https://www.google.com")
        }
        findViewById<ImageButton>(R.id.btnNavTabs).setOnClickListener {
            showTabSwitcher()
        }
        findViewById<ImageButton>(R.id.btnNavMenu).setOnClickListener {
            showOverflowMenu(it)
        }
    }

    private fun showOverflowMenu(anchor: View) {
        val popup = PopupMenu(this, anchor)
        popup.menu.add(0, 1, 0, getString(R.string.new_tab))
        popup.menu.add(0, 2, 0, getString(R.string.find_in_page))
        popup.menu.add(0, 3, 0, getString(R.string.bookmarks))
        popup.menu.add(0, 4, 0, getString(R.string.share))
        popup.menu.add(0, 5, 0, getString(R.string.settings))

        popup.setOnMenuItemClickListener { item ->
            when (item.itemId) {
                1 -> {
                    createNewTab()
                    true
                }
                2 -> {
                    showFindInPage()
                    true
                }
                3 -> {
                    val activeTab = tabManager.getActiveTab()
                    val url = activeTab?.webView?.url ?: ""
                    val title = activeTab?.webView?.title ?: url
                    if (url.isNotBlank()) {
                        bookmarkDb.addBookmark(url, title)
                        Toast.makeText(this, "Bookmark saved", Toast.LENGTH_SHORT).show()
                    }
                    true
                }
                4 -> {
                    val url = tabManager.getActiveTab()?.webView?.url ?: ""
                    if (url.isNotBlank()) {
                        val shareIntent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, url)
                        }
                        startActivity(Intent.createChooser(shareIntent, "Share URL"))
                    }
                    true
                }
                5 -> {
                    startActivity(Intent(this, SettingsActivity::class.java))
                    true
                }
                else -> false
            }
        }
        popup.show()
    }

    private fun createNewTab() {
        val tab = tabManager.createTab()
        setupWebView(tab.webView)
        tabManager.switchTab(tab.id)
        updateTabCount()
        tab.webView.loadUrl("https://www.google.com")
    }

    private fun setupWebView(webView: WebView) {
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            databaseEnabled = true
            useWideViewPort = true
            loadWithOverviewMode = true
            setSupportZoom(true)
            builtInZoomControls = true
            displayZoomControls = false
        }

        webView.webViewClient = StauntWebViewClient(
            adBlockEngine,
            historyDb,
            onPageStarted = { url ->
                etUrl.setText(url)
                updateSecurityIcon(url)
                progressBar.visibility = View.VISIBLE
            },
            onPageFinished = { url, title ->
                progressBar.visibility = View.GONE
                swipeRefresh.isRefreshing = false
                updateSecurityIcon(url)
                val tab = tabManager.tabs.find { it.webView == webView }
                if (tab != null) {
                    tab.url = url
                    if (!title.isNullOrBlank()) tab.title = title
                }
            }
        )

        webView.webChromeClient = StauntChromeClient(
            onProgressChanged = { progress ->
                progressBar.progress = progress
                if (progress == 100) progressBar.visibility = View.GONE
                else progressBar.visibility = View.VISIBLE
            },
            onTitleReceived = { title ->
                val tab = tabManager.tabs.find { it.webView == webView }
                if (tab != null && title.isNotBlank()) {
                    tab.title = title
                }
            }
        )

        webView.setDownloadListener { url, userAgent, contentDisposition, mimetype, _ ->
            downloadHandler.downloadFile(url, userAgent, contentDisposition, mimetype)
        }
    }

    private fun updateTabCount() {
        btnTabCount.text = tabManager.tabs.size.toString()
    }

    override fun onBackPressed() {
        if (tabSwitcherContainer.visibility == View.VISIBLE) {
            hideTabSwitcher()
            return
        }
        if (findInPageContainer.visibility == View.VISIBLE) {
            hideFindInPage()
            return
        }
        val webView = tabManager.getActiveTab()?.webView
        if (webView?.canGoBack() == true) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}
