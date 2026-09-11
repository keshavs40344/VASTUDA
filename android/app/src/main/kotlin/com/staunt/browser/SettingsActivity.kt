package com.staunt.browser

import android.content.Context
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebStorage
import android.widget.Button
import android.widget.Switch
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
