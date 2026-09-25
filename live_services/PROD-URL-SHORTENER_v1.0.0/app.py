import sqlite3
import hashlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl

app = FastAPI(title="FastShortener", version="1.0.0")
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

class ShortenRequest(BaseModel):
    url: str

@app.get("/health")
def health():
    return {"status": "ok", "service": "FastShortener", "version": "1.0.0"}

@app.post("/shorten")
def shorten_url(req: ShortenRequest):
    code = hashlib.md5(req.url.encode()).hexdigest()[:6]
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT short_code FROM urls WHERE short_code = ?", (code,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO urls (original_url, short_code) VALUES (?, ?)", (req.url, code))
            conn.commit()
    return {"short_code": code, "short_url": f"http://short.ly/{code}", "original_url": req.url}

@app.get("/{short_code}")
def resolve_url(short_code: str):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT original_url FROM urls WHERE short_code = ?", (short_code,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Short URL not found")
        return {"original_url": row[0]}