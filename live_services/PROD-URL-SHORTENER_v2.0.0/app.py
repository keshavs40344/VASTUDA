import sqlite3
import hashlib
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="FastShortener", version="2.0.0")
DB_FILE = "urls.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_url TEXT NOT NULL,
                short_code TEXT UNIQUE NOT NULL
            )
        ''')
        conn.commit()

init_db()

class ShortenRequestV2(BaseModel):
    url: str
    custom_slug: Optional[str] = Field(None, min_length=3, max_length=20)

@app.get("/health")
def health():
    return {"status": "ok", "service": "FastShortener", "version": "2.0.0"}

@app.post("/shorten")
def shorten_url(req: ShortenRequestV2):
    if req.custom_slug:
        code = req.custom_slug.strip().lower()
    else:
        code = hashlib.md5(req.url.encode()).hexdigest()[:6]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT original_url FROM urls WHERE short_code = ?", (code,))
        existing = cursor.fetchone()
        if existing and existing[0] != req.url:
            raise HTTPException(status_code=409, detail="Custom slug already in use")
        if not existing:
            cursor.execute("INSERT INTO urls (original_url, short_code) VALUES (?, ?)", (req.url, code))
            conn.commit()

    return {"short_code": code, "short_url": f"http://short.ly/{code}", "original_url": req.url, "is_custom": bool(req.custom_slug)}

@app.get("/{short_code}")
def resolve_url(short_code: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT original_url FROM urls WHERE short_code = ?", (short_code,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Short URL not found")
        return {"original_url": row[0]}