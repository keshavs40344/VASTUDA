package com.staunt.browser

import android.content.ContentValues
import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteOpenHelper

class BookmarkDb(context: Context) : SQLiteOpenHelper(context, "bookmarks.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE bookmarks (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, title TEXT, favicon TEXT, folder TEXT, created INTEGER)")
    }

    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        db.execSQL("DROP TABLE IF EXISTS bookmarks")
        onCreate(db)
    }

    fun addBookmark(url: String, title: String) {
        val db = writableDatabase
        val values = ContentValues().apply {
            put("url", url)
            put("title", title)
            put("created", System.currentTimeMillis())
        }
        db.insert("bookmarks", null, values)
    }
}