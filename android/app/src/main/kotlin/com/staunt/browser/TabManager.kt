package com.staunt.browser

import android.content.Context
import android.view.ViewGroup
import android.webkit.WebView

class TabManager(private val context: Context, private val container: ViewGroup) {
    val tabs = ArrayList<TabData>()
    var activeTabId: String? = null

    fun createTab(isIncognito: Boolean = false): TabData {
        val webView = WebView(context).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
        }
        val tab = TabData(
            id = System.currentTimeMillis().toString(),
            webView = webView,
            isIncognito = isIncognito
        )
        tabs.add(tab)
        return tab
    }

    fun switchTab(id: String) {
        val tab = tabs.find { it.id == id } ?: return
        container.removeAllViews()
        if (tab.webView.parent != null) {
            (tab.webView.parent as ViewGroup).removeView(tab.webView)
        }
        container.addView(tab.webView)
        activeTabId = id
    }

    fun closeTab(id: String) {
        val index = tabs.indexOfFirst { it.id == id }
        if (index == -1) return
        val tab = tabs[index]
        tab.webView.destroy()
        tabs.removeAt(index)
        if (activeTabId == id) {
            if (tabs.isNotEmpty()) {
                val newIndex = if (index > 0) index - 1 else 0
                switchTab(tabs[newIndex].id)
            } else {
                activeTabId = null
                container.removeAllViews()
            }
        }
    }

    fun getActiveTab(): TabData? {
        return tabs.find { it.id == activeTabId }
    }
}