import sqlite3
import os
import hashlib
import binascii
import json
import time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vastuda.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    # High-concurrency performance pragmas
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache in RAM
    return conn



def init_db():
    """Initialize database tables for VASTUDA."""
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                name TEXT DEFAULT '',
                created_at INTEGER NOT NULL,
                preferences TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                query TEXT NOT NULL,
                category TEXT DEFAULT 'all',
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                domain TEXT DEFAULT '',
                snippet TEXT DEFAULT '',
                category TEXT DEFAULT 'web',
                collection_name TEXT DEFAULT 'General',
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at INTEGER NOT NULL,
                UNIQUE(user_id, name)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS search_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                category TEXT DEFAULT 'all',
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ai_overview_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                overview_json TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'pending',
                depth INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                added_at INTEGER NOT NULL,
                crawled_at INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                canonical_url TEXT DEFAULT '',
                title TEXT DEFAULT '',
                headings TEXT DEFAULT '',
                body_text TEXT DEFAULT '',
                meta_desc TEXT DEFAULT '',
                language TEXT DEFAULT 'en',
                domain TEXT DEFAULT '',
                published_date TEXT DEFAULT '',
                crawl_date INTEGER NOT NULL,
                content_hash TEXT DEFAULT '',
                quality_score REAL DEFAULT 1.0
            )
        """)
        # FTS5 full-text virtual table for fast indexing & searching
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                    title,
                    headings,
                    body_text,
                    domain,
                    content='documents',
                    content_rowid='id'
                )
            """)
        except Exception:
            pass
        conn.commit()


def get_cached_ai_overview(query: str, max_age_seconds: int = 43200):
    """Retrieve persistent AI overview if generated within max_age_seconds (Default 12 hours)."""
    q_clean = query.strip().lower()
    q_hash = hashlib.sha256(q_clean.encode("utf-8")).hexdigest()
    min_time = int(time.time()) - max_age_seconds
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT overview_json FROM ai_overview_cache WHERE query_hash = ? AND created_at >= ?", (q_hash, min_time))
            row = cur.fetchone()
            if row:
                return json.loads(row["overview_json"])
    except Exception:
        pass
    return None


def cache_ai_overview(query: str, data: dict):
    """Store synthesized AI overview in SQLite cache with timestamp."""
    if not query or not data:
        return
    q_clean = query.strip().lower()
    q_hash = hashlib.sha256(q_clean.encode("utf-8")).hexdigest()
    now = int(time.time())
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ai_overview_cache (query_hash, query, overview_json, created_at) VALUES (?, ?, ?, ?)",
                (q_hash, q_clean, json.dumps(data), now)
            )
            conn.commit()
    except Exception:
        pass


def get_matching_suggestions(prefix: str, limit: int = 8) -> list:
    """Retrieve matching past search queries from local database as fallback."""
    if not prefix or not prefix.strip():
        return []
    clean = prefix.strip().lower()
    try:
        with get_db() as conn:
            cur = conn.cursor()
            # Match queries starting with or containing prefix
            cur.execute("""
                SELECT query, COUNT(*) as cnt
                FROM search_analytics
                WHERE lower(query) LIKE ?
                GROUP BY lower(query)
                ORDER BY cnt DESC, MAX(created_at) DESC
                LIMIT ?
            """, (f"{clean}%", limit))
            rows = cur.fetchall()
            results = [r["query"] for r in rows if r["query"].lower() != clean]
            if len(results) < limit:
                cur.execute("""
                    SELECT query, COUNT(*) as cnt
                    FROM search_analytics
                    WHERE lower(query) LIKE ? AND lower(query) NOT LIKE ?
                    GROUP BY lower(query)
                    ORDER BY cnt DESC, MAX(created_at) DESC
                    LIMIT ?
                """, (f"%{clean}%", f"{clean}%", limit - len(results)))
                more_rows = cur.fetchall()
                results.extend([r["query"] for r in more_rows if r["query"].lower() != clean])
            return results[:limit]
    except Exception:
        return []


# --- Security: Password Hashing (PBKDF2-HMAC-SHA256) ---

def hash_password(password: str) -> str:
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    pwdhash = binascii.hexlify(pwdhash)
    return (salt + pwdhash).decode('ascii')


def verify_password(stored_password: str, provided_password: str) -> bool:
    salt = stored_password[:64]
    stored_pwdhash = stored_password[64:]
    pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt.encode('ascii'), 100000)
    pwdhash = binascii.hexlify(pwdhash).decode('ascii')
    return pwdhash == stored_pwdhash


# --- User Management ---

def create_user(email, password, name=""):
    pwd_hash = hash_password(password)
    now = int(time.time())
    default_prefs = json.dumps({
        "theme": "dark",
        "safe_search": "moderate",
        "results_per_page": 10,
        "open_new_tab": True,
        "history_enabled": True,
        "personalized": False,
        "region": "global"
    })
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash, name, created_at, preferences) VALUES (?, ?, ?, ?, ?)",
                (email.lower().strip(), pwd_hash, name.strip(), now, default_prefs)
            )
            user_id = cur.lastrowid
            # Default collections
            conn.execute("INSERT INTO collections (user_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                         (user_id, "Study", "Academic and research materials", now))
            conn.execute("INSERT INTO collections (user_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                         (user_id, "Projects", "Development and code links", now))
            conn.commit()
            return {"id": user_id, "email": email.lower().strip(), "name": name.strip()}
    except sqlite3.IntegrityError:
        return None


def authenticate_user(email, password):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),)).fetchone()
        if not row:
            return None
        if verify_password(row["password_hash"], password):
            prefs = json.loads(row["preferences"] or "{}")
            return {
                "id": row["id"],
                "email": row["email"],
                "name": row["name"],
                "preferences": prefs
            }
    return None


def get_user_by_id(user_id):
    with get_db() as conn:
        row = conn.execute("SELECT id, email, name, preferences, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "preferences": json.loads(row["preferences"] or "{}"),
            "created_at": row["created_at"]
        }


def update_user_preferences(user_id, prefs_dict):
    with get_db() as conn:
        current = conn.execute("SELECT preferences FROM users WHERE id = ?", (user_id,)).fetchone()
        if not current:
            return False
        existing = json.loads(current["preferences"] or "{}")
        existing.update(prefs_dict)
        conn.execute("UPDATE users SET preferences = ? WHERE id = ?", (json.dumps(existing), user_id))
        conn.commit()
        return existing


# --- History Management ---

def record_search_history(user_id, query, category="all"):
    now = int(time.time())
    with get_db() as conn:
        # Check if history is paused/disabled
        if user_id:
            user = conn.execute("SELECT preferences FROM users WHERE id = ?", (user_id,)).fetchone()
            if user:
                prefs = json.loads(user["preferences"] or "{}")
                if not prefs.get("history_enabled", True):
                    return
        conn.execute(
            "INSERT INTO search_history (user_id, query, category, created_at) VALUES (?, ?, ?, ?)",
            (user_id, query, category, now)
        )
        conn.execute(
            "INSERT INTO search_analytics (query, category, created_at) VALUES (?, ?, ?)",
            (query, category, now)
        )
        conn.commit()


def get_search_history(user_id, limit=50):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, query, category, created_at FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def delete_history_item(user_id, history_id):
    with get_db() as conn:
        conn.execute("DELETE FROM search_history WHERE id = ? AND user_id = ?", (history_id, user_id))
        conn.commit()
        return True


def clear_search_history(user_id):
    with get_db() as conn:
        conn.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
        conn.commit()
        return True


# --- Collections & Saved Results ---

def get_user_collections(user_id):
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM collections WHERE user_id = ? ORDER BY created_at ASC", (user_id,)).fetchall()
        return [dict(r) for r in rows]


def create_collection(user_id, name, description=""):
    now = int(time.time())
    try:
        with get_db() as conn:
            cur = conn.execute(
                "INSERT INTO collections (user_id, name, description, created_at) VALUES (?, ?, ?, ?)",
                (user_id, name.strip(), description.strip(), now)
            )
            conn.commit()
            return {"id": cur.lastrowid, "name": name.strip(), "description": description.strip()}
    except sqlite3.IntegrityError:
        return None


def save_result(user_id, title, url, domain="", snippet="", category="web", collection_name="General"):
    now = int(time.time())
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO saved_results (user_id, title, url, domain, snippet, category, collection_name, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, title, url, domain, snippet, category, collection_name, now)
        )
        conn.commit()
        return cur.lastrowid


def get_saved_results(user_id, collection_name=None):
    with get_db() as conn:
        if collection_name:
            rows = conn.execute(
                "SELECT * FROM saved_results WHERE user_id = ? AND collection_name = ? ORDER BY created_at DESC",
                (user_id, collection_name)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM saved_results WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]


def remove_saved_result(user_id, item_id):
    with get_db() as conn:
        conn.execute("DELETE FROM saved_results WHERE id = ? AND user_id = ?", (item_id, user_id))
        conn.commit()
        return True


def delete_collection(user_id, collection_name):
    with get_db() as conn:
        conn.execute("DELETE FROM collections WHERE user_id = ? AND name = ?", (user_id, collection_name))
        # Keep items but move to General
        conn.execute("UPDATE saved_results SET collection_name = 'General' WHERE user_id = ? AND collection_name = ?", (user_id, collection_name))
        conn.commit()
        return True


def export_user_data(user_id):
    """Generate complete export of user profile, history, collections, and saved links."""
    user = get_user_by_id(user_id)
    if not user:
        return None
    history = get_search_history(user_id, limit=500)
    collections = get_user_collections(user_id)
    saved = get_saved_results(user_id)
    return {
        "user": user,
        "search_history": history,
        "collections": collections,
        "saved_results": saved,
        "exported_at": int(time.time())
    }


# Initialize database automatically on import
init_db()

