package com.staunt.browser

import android.content.Intent
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.webkit.DownloadListener
import android.webkit.WebSettings
import android.webkit.WebView
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

class MainActivity : AppCompatActivity() {
    private lateinit var tabManager: TabManager
    private lateinit var adBlockEngine: AdBlockEngine
    private lateinit var historyDb: HistoryDb
    private lateinit var downloadHandler: DownloadHandler
    
    private lateinit var etUrl: EditText
    private lateinit var progressBar: ProgressBar
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var btnTabCount: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        adBlockEngine = AdBlockEngine(this).apply { init() }
        historyDb = HistoryDb(this)
        downloadHandler = DownloadHandler(this)
        
        val container = findViewById<FrameLayout>(R.id.webviewContainer)
        tabManager = TabManager(this, container)
        
        etUrl = findViewById(R.id.etUrl)
        progressBar = findViewById(R.id.progressBar)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        btnTabCount = findViewById(R.id.btnTabCount)

        setupButtons()
        
        swipeRefresh.setOnRefreshListener {
            tabManager.getActiveTab()?.webView?.reload()
        }

        etUrl.setOnEditorActionListener { _, actionId, event ->
            if (actionId == EditorInfo.IME_ACTION_GO || event?.keyCode == KeyEvent.KEYCODE_ENTER) {
                var url = etUrl.text.toString()
                if (!url.startsWith("http://") && !url.startsWith("https://")) {
                    url = "https://www.google.com/search?q=$url"
                }
                tabManager.getActiveTab()?.webView?.loadUrl(url)
                true
            } else false
        }

        createNewTab()
    }

    private fun setupButtons() {
        findViewById<ImageButton>(R.id.btnBack).setOnClickListener {
            tabManager.getActiveTab()?.webView?.goBack()
        }
        findViewById<ImageButton>(R.id.btnForward).setOnClickListener {
            tabManager.getActiveTab()?.webView?.goForward()
        }
        findViewById<ImageButton>(R.id.btnMenu).setOnClickListener {
            startActivity(Intent(this, SettingsActivity::class))
        }
        findViewById<ImageButton>(R.id.btnNavHome).setOnClickListener {
            tabManager.getActiveTab()?.webView?.loadUrl("https://www.google.com")
        }
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
                progressBar.visibility = View.VISIBLE
            },
            onPageFinished = { _, _ ->
                progressBar.visibility = View.GONE
                swipeRefresh.isRefreshing = false
            }
        )

        webView.webChromeClient = StauntChromeClient(
            onProgressChanged = { progress ->
                progressBar.progress = progress
                if (progress == 100) progressBar.visibility = View.GONE
                else progressBar.visibility = View.VISIBLE
            },
            onTitleReceived = { title ->
                tabManager.getActiveTab()?.title = title
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
        val webView = tabManager.getActiveTab()?.webView
        if (webView?.canGoBack() == true) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }
}