package com.staunt.browser

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class HistoryDb(context: Context) : SQLiteOpenHelper(context, "history.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE history (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, title TEXT, favicon TEXT, timestamp INTEGER)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS history")
        onCreate(db)
    }

    fun addEntry(url: String, title: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("url", url)
            put("title", title)
            put("timestamp", System.currentTimeMillis())
        }
        db.insert("history", null, values)
    }

    fun clear() {
        writableDatabase.delete("history", null, null)
    }
}