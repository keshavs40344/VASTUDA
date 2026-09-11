package com.staunt.browser

import android.graphics.Bitmap
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import android.webkit.WebView
import android.webkit.WebViewClient
import java.io.ByteArrayInputStream

class StauntWebViewClient(
    private val adBlockEngine: AdBlockEngine,
    private val historyDb: HistoryDb,
    private val onPageStarted: (String) -> Unit,
    private val onPageFinished: (String, String?) -> Unit
) : WebViewClient() {

    override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
        view.loadUrl(request.url.toString())
        return true
    }

    override fun shouldInterceptRequest(view: WebView, request: WebResourceRequest): WebResourceResponse? {
        if (adBlockEngine.shouldBlock(request.url.toString())) {
            return WebResourceResponse("text/plain", "UTF-8", ByteArrayInputStream("".toByteArray()))
        }
        return super.shouldInterceptRequest(view, request)
    }

    override fun onPageStarted(view: WebView, url: String, favicon: Bitmap?) {
        super.onPageStarted(view, url, favicon)
        onPageStarted(url)
    }

    override fun onPageFinished(view: WebView, url: String) {
        super.onPageFinished(view, url)
        onPageFinished(url, view.title)
    }

    override fun doUpdateVisitedHistory(view: WebView, url: String, isReload: Boolean) {
        super.doUpdateVisitedHistory(view, url, isReload)
        if (!isReload) {
            historyDb.addEntry(url, view.title ?: "")
        }
    }

    override fun onReceivedError(
        view: WebView,
        request: WebResourceRequest,
        error: android.webkit.WebResourceError
    ) {
        super.onReceivedError(view, request, error)
        if (request.isForMainFrame) {
            val errorHtml = """
                <!DOCTYPE html>
                <html>
                <head>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { margin: 0; background: #12141a; color: #f1f5f9; font-family: -apple-system, Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; text-align: center; }
                        .box { padding: 24px; }
                        h2 { font-size: 18px; margin: 12px 0 6px; font-weight: 700; }
                        p { font-size: 13px; color: #94a3b8; line-height: 1.5; margin: 0 0 20px; }
                        button { background: #3b82f6; color: #fff; border: none; padding: 10px 24px; border-radius: 8px; font-weight: 600; font-size: 14px; }
                    </style>
                </head>
                <body>
                    <div class="box">
                        <div style="font-size: 40px;">🌐</div>
                        <h2>Site Cannot Be Reached</h2>
                        <p>Connection timed out or network offline.</p>
                        <button onclick="location.reload()">Retry</button>
                    </div>
                </body>
                </html>
            """.trimIndent()
            view.loadDataWithBaseURL(null, errorHtml, "text/html", "UTF-8", null)
        }
    }
}