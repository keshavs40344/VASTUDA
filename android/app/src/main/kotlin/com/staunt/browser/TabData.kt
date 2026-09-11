package com.staunt.browser

import android.graphics.Bitmap
import android.webkit.WebView

data class TabData(
    val id: String,
    var webView: WebView,
    var url: String = "",
    var title: String = "New Tab",
    var favicon: Bitmap? = null,
    val isIncognito: Boolean = false,
    val timestamp: Long = System.currentTimeMillis()
)