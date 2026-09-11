package com.staunt.browser

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebStorage
import android.webkit.WebView
import android.widget.Button
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.Toolbar

class SettingsActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)

        val toolbar = findViewById<Toolbar>(R.id.settingsToolbar)
        setSupportActionBar(toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        toolbar.setNavigationOnClickListener { finish() }

        val prefs = getSharedPreferences("staunt_settings", Context.MODE_PRIVATE)
        val swAdBlocker = findViewById<Switch>(R.id.swAdBlocker)
        val btnClearData = findViewById<Button>(R.id.btnClearData)
        val tvVersion = findViewById<TextView>(R.id.tvVersion)

        // Dynamically query real Android WebView engine package and version
        try {
            val webViewPackage = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                WebView.getCurrentWebViewPackage()
            } else null
            
            val engineVersion = webViewPackage?.versionName ?: "System Default"
            val appVersion = try {
                packageManager.getPackageInfo(packageName, 0).versionName
            } catch (e: Exception) {
                "2.0.0"
            }
            
            tvVersion.text = "Staunt Version: $appVersion\nWebView Engine: $engineVersion\nChromium Provider: ${webViewPackage?.packageName ?: "Android System WebView"}"
        } catch (e: Exception) {
            tvVersion.text = "Staunt Version 2.0.0\nEngine version unavailable."
        }

        // Ad blocker switch state
        val adBlockEnabled = prefs.getBoolean("ad_block_enabled", true)
        swAdBlocker.isChecked = adBlockEnabled

        swAdBlocker.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("ad_block_enabled", isChecked).apply()
            Toast.makeText(this, if (isChecked) "Ad Blocker Enabled" else "Ad Blocker Disabled", Toast.LENGTH_SHORT).show()
        }

        // Clear Browsing Data
        btnClearData.setOnClickListener {
            val historyDb = HistoryDb(this)
            historyDb.clear()

            CookieManager.getInstance().removeAllCookies(null)
            CookieManager.getInstance().flush()

            WebStorage.getInstance().deleteAllData()

            Toast.makeText(this, "Browsing history, cookies, and cache cleared", Toast.LENGTH_LONG).show()
        }
    }
}
