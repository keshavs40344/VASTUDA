package com.staunt.browser

import android.content.Context
import android.util.Log

class AdBlockEngine(private val context: Context) {
    private val blockedDomains = HashSet<String>()
    var isEnabled = true

    fun init() {
        val prefs = context.getSharedPreferences("staunt_settings", Context.MODE_PRIVATE)
        isEnabled = prefs.getBoolean("ad_block_enabled", true)
        try {
            val inputStream = context.assets.open("adblock/easylist-mini.txt")
            inputStream.bufferedReader().useLines { lines ->
                lines.forEach { line ->
                    if (!line.startsWith("!") && line.startsWith("||") && line.endsWith("^")) {
                        val domain = line.substring(2, line.length - 1)
                        blockedDomains.add(domain)
                    }
                }
            }
        } catch (e: Exception) {
            Log.e("AdBlockEngine", "Failed to load rules", e)
        }
    }

    fun shouldBlock(url: String): Boolean {
        val prefs = context.getSharedPreferences("staunt_settings", Context.MODE_PRIVATE)
        if (!prefs.getBoolean("ad_block_enabled", isEnabled)) return false
        try {
            val uri = android.net.Uri.parse(url)
            val host = uri.host ?: return false
            var currentHost = host
            while (currentHost.contains(".")) {
                if (blockedDomains.contains(currentHost)) {
                    return true
                }
                val firstDot = currentHost.indexOf('.')
                if (firstDot == -1) break
                currentHost = currentHost.substring(firstDot + 1)
            }
        } catch (e: Exception) {}
        return false
    }
}
