import re
import time
import hashlib
import logging
import urllib.parse
from search_engine import db

logger = logging.getLogger("VASTUDA_Indexer")


def clean_text_for_fts(text: str) -> str:
    """Sanitize query string for safe SQLite FTS5 query."""
    if not text:
        return ""
    # Remove special FTS punctuation and characters
    clean = re.sub(r'[^\w\s]', ' ', text)
    tokens = clean.strip().split()
    if not tokens:
        return ""
    # Join tokens with NEAR or OR for flexible token matching
    return " OR ".join([f'"{t}"*' for t in tokens if len(t) > 1]) or f'"{tokens[0]}"*'


def index_document(url: str, title: str, body_text: str, headings: str = "",
                   meta_desc: str = "", language: str = "en",
                   canonical_url: str = "", published_date: str = "",
                   quality_score: float = 1.0) -> int:
    """
    Insert or update a crawled document into the SQLite database and sync FTS5 index.
    """
    if not url or not body_text:
        return 0

    clean_url = url.strip()
    try:
        domain = urllib.parse.urlparse(clean_url).netloc.lower()
    except Exception:
        domain = ""

    content_hash = hashlib.sha256(body_text.strip().encode("utf-8", errors="ignore")).hexdigest()
    now = int(time.time())

    with db.get_db() as conn:
        cursor = conn.cursor()

        # Check for existing document by URL
        cursor.execute("SELECT id, content_hash FROM documents WHERE url = ?", (clean_url,))
        existing = cursor.fetchone()

        if existing:
            doc_id = existing["id"]
            # If content hash unchanged, skip re-indexing
            if existing["content_hash"] == content_hash:
                cursor.execute("UPDATE documents SET crawl_date = ? WHERE id = ?", (now, doc_id))
                conn.commit()
                return doc_id

            # Update documents
            cursor.execute("""
                UPDATE documents SET
                    canonical_url = ?,
                    title = ?,
                    headings = ?,
                    body_text = ?,
                    meta_desc = ?,
                    language = ?,
                    domain = ?,
                    published_date = ?,
                    crawl_date = ?,
                    content_hash = ?,
                    quality_score = ?
                WHERE id = ?
            """, (canonical_url or clean_url, title, headings, body_text, meta_desc,
                  language, domain, published_date, now, content_hash, quality_score, doc_id))

            # Update FTS5 index
            try:
                cursor.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc_id,))
                cursor.execute("""
                    INSERT INTO documents_fts (rowid, title, headings, body_text, domain)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc_id, title, headings, body_text, domain))
            except Exception as e:
                logger.warning(f"FTS5 update note: {e}")

            conn.commit()
            return doc_id
        else:
            # Insert new document
            cursor.execute("""
                INSERT INTO documents (
                    url, canonical_url, title, headings, body_text,
                    meta_desc, language, domain, published_date, crawl_date,
                    content_hash, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_url, canonical_url or clean_url, title, headings, body_text,
                  meta_desc, language, domain, published_date, now, content_hash, quality_score))
            doc_id = cursor.lastrowid

            try:
                cursor.execute("""
                    INSERT INTO documents_fts (rowid, title, headings, body_text, domain)
                    VALUES (?, ?, ?, ?, ?)
                """, (doc_id, title, headings, body_text, domain))
            except Exception as e:
                logger.warning(f"FTS5 insert note: {e}")

            conn.commit()
            return doc_id


def search_local_index(query: str, limit: int = 8):
    """
    Query local FTS5 index with BM25 rank scoring and snippet generation.
    Returns list of matching result dictionaries.
    """
    clean_q = clean_text_for_fts(query)
    if not clean_q:
        return []

    results = []
    try:
        with db.get_db() as conn:
            cursor = conn.cursor()
            # Query documents_fts using bm25() ranking
            sql = """
                SELECT 
                    d.id,
                    d.url,
                    d.title,
                    d.domain,
                    d.meta_desc,
                    d.quality_score,
                    d.published_date,
                    snippet(documents_fts, 2, '<b>', '</b>', '...', 28) AS matched_snippet,
                    bm25(documents_fts, 5.0, 3.0, 1.0, 2.0) AS bm25_rank
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ?
                ORDER BY (bm25_rank * d.quality_score) ASC
                LIMIT ?
            """
            cursor.execute(sql, (clean_q, limit))
            rows = cursor.fetchall()
            for r in rows:
                domain = r["domain"] or ""
                snippet = r["matched_snippet"] or r["meta_desc"] or "Relevant page from VASTUDA index."
                results.append({
                    "title": r["title"] or domain,
                    "url": r["url"],
                    "domain": domain,
                    "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
                    "snippet": snippet,
                    "score": round(abs(float(r["bm25_rank"] or 1.0)), 2),
                    "published_date": r["published_date"] or "Indexed",
                    "source": "VASTUDA Local Index"
                })
    except Exception as e:
        logger.warning(f"Local index search error: {e}")

    return results


def get_index_stats():
    """Return total number of indexed documents and crawled URLs."""
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM documents")
            doc_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM crawl_queue")
            queue_count = cur.fetchone()["total"]
            return {"indexed_documents": doc_count, "queued_urls": queue_count}
    except Exception:
        return {"indexed_documents": 0, "queued_urls": 0}
