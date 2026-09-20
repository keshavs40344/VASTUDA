"""
VASTUDA 5.0 — Intelligent Indexer & Transparent Multi-Signal Ranking Pipeline
Features:
- FTS5 full-text indexing with SQLite WAL concurrency
- Rich metadata (content_type, source_type, author, canonical_domain, language)
- Multi-signal transparent relevance ranking (BM25 + Title + Heading + Phrase + Language + Freshness + Quality)
- Controlled source diversity (domain clustering control)
- Explainable score breakdown for every retrieved item
"""

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
    # Remove special FTS punctuation and operators
    clean = re.sub(r'[^\w\s]', ' ', text)
    tokens = [t for t in clean.strip().split() if len(t) > 0]
    if not tokens:
        return ""

    # Build token clauses and phrase clause if multi-token
    token_clauses = [f'"{t}"*' for t in tokens if len(t) > 1]
    if not token_clauses:
        token_clauses = [f'"{tokens[0]}"*']

    return " OR ".join(token_clauses)


def index_document(url: str, title: str, body_text: str, headings: str = "",
                   meta_desc: str = "", language: str = "en",
                   canonical_url: str = "", published_date: str = "",
                   quality_score: float = 1.0, content_type: str = "text/html",
                   source_type: str = "web", author: str = "",
                   inbound_links_count: int = 0) -> int:
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

    canon_url = (canonical_url or clean_url).strip()
    try:
        canonical_domain = urllib.parse.urlparse(canon_url).netloc.lower() or domain
    except Exception:
        canonical_domain = domain

    content_hash = hashlib.sha256(body_text.strip().encode("utf-8", errors="ignore")).hexdigest()
    now = int(time.time())

    with db.get_db() as conn:
        cursor = conn.cursor()

        # Check for existing document by URL or canonical URL
        cursor.execute("SELECT id, content_hash FROM documents WHERE url = ? OR canonical_url = ?", (clean_url, clean_url))
        existing = cursor.fetchone()

        if existing:
            doc_id = existing["id"]
            # If content hash unchanged, refresh crawl timestamp
            if existing["content_hash"] == content_hash:
                cursor.execute("UPDATE documents SET crawl_date = ? WHERE id = ?", (now, doc_id))
                conn.commit()
                return doc_id

            # Update document record
            cursor.execute("""
                UPDATE documents SET
                    canonical_url = ?,
                    title = ?,
                    headings = ?,
                    body_text = ?,
                    meta_desc = ?,
                    language = ?,
                    domain = ?,
                    canonical_domain = ?,
                    published_date = ?,
                    crawl_date = ?,
                    content_hash = ?,
                    quality_score = ?,
                    content_type = ?,
                    source_type = ?,
                    author = ?,
                    inbound_links_count = ?
                WHERE id = ?
            """, (canon_url, title, headings, body_text, meta_desc,
                  language, domain, canonical_domain, published_date, now, content_hash,
                  quality_score, content_type, source_type, author, inbound_links_count, doc_id))

            # Sync FTS5 virtual table
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
                    meta_desc, language, domain, canonical_domain, published_date,
                    crawl_date, content_hash, quality_score, content_type,
                    source_type, author, inbound_links_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_url, canon_url, title, headings, body_text,
                  meta_desc, language, domain, canonical_domain, published_date,
                  now, content_hash, quality_score, content_type,
                  source_type, author, inbound_links_count))
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


def compute_relevance_score(doc: dict, query: str, query_info: dict = None) -> tuple:
    """
    Transparent Multi-Signal Relevance Scorer:
    Evaluates:
    - Base BM25 text match (from FTS5)
    - Exact query match in title
    - Term coverage in title
    - Heading matches
    - Exact phrase match in body
    - Language congruence
    - Source quality / authority
    - Freshness signal (query-dependent)
    - Low-quality / spam penalties
    Returns (composite_score, score_breakdown).
    """
    q_lower = query.strip().lower()
    q_tokens = [t for t in re.sub(r'[^\w\s]', ' ', q_lower).split() if len(t) > 1]
    
    title = (doc.get("title") or "").lower()
    headings = (doc.get("headings") or "").lower()
    body = (doc.get("body_text") or "").lower()
    doc_lang = (doc.get("language") or "en").lower()
    raw_bm25 = abs(float(doc.get("bm25_rank") or 1.0))
    # Normalized BM25 component (higher = better)
    bm25_score = min(raw_bm25 * 8.0, 50.0)

    # 1. Title Signals
    title_boost = 0.0
    if q_lower and q_lower in title:
        title_boost += 35.0  # Full exact query phrase in title
    elif q_tokens:
        matched_tokens = sum(1 for t in q_tokens if t in title)
        ratio = matched_tokens / len(q_tokens)
        title_boost += ratio * 25.0

    # 2. Heading Signals
    heading_boost = 0.0
    if q_lower and q_lower in headings:
        heading_boost += 18.0
    elif q_tokens:
        matched_h = sum(1 for t in q_tokens if t in headings)
        heading_boost += (matched_h / max(len(q_tokens), 1)) * 10.0

    # 3. Exact Phrase in Body
    phrase_boost = 0.0
    if len(q_tokens) > 1 and q_lower in body:
        phrase_boost += 12.0

    # 4. Language Match Signal
    lang_boost = 0.0
    query_lang = query_info.get("language", "en") if query_info else "en"
    if query_lang == doc_lang:
        lang_boost += 10.0
    elif query_lang == "hinglish" and (doc_lang in ("en", "hi") or any(t in body for t in ["sikhe", "kare", "kaise", "hindi"])):
        lang_boost += 8.0

    # 5. Measurable Content Structure Quality (no arbitrary authority bonuses)
    quality_boost = 0.0
    body_word_count = len(body.split())
    if 250 <= body_word_count <= 10000:
        quality_boost += 4.0  # Substantive content length
    if headings and len(headings.strip()) > 15:
        quality_boost += 3.0  # Structured document with headings
    if doc.get("meta_desc") and len(str(doc.get("meta_desc")).strip()) > 25:
        quality_boost += 2.0  # Quality metadata description present

    # 6. Intent-Aligned Content Congruence (Query-document intent match)
    intent_boost = 0.0
    q_intent = query_info.get("intent", "informational") if query_info else "informational"
    c_type = (doc.get("content_type") or "web").lower()
    s_type = (doc.get("source_type") or "web").lower()

    if q_intent in ("tutorial", "code") and ("doc" in c_type or "doc" in s_type):
        intent_boost += 6.0
    elif q_intent in ("academic", "definition") and (s_type in ("academic", "encyclopedic") or "wiki" in doc.get("domain", "")):
        intent_boost += 6.0
    elif q_intent == "navigational" and doc.get("canonical_url", "").rstrip("/") == f"https://{doc.get('domain', '')}":
        intent_boost += 8.0  # Root domain page matches navigational queries

    # 7. Freshness Signal (Query-dependent: strong for temporal, minimal for evergreen)
    fresh_boost = 0.0
    fresh_required = query_info.get("freshness_required", False) if query_info else False
    pub_at = int(doc.get("published_at") or 0)
    upd_at = int(doc.get("updated_at") or 0)
    crw_at = int(doc.get("crawled_at") or doc.get("crawl_date") or time.time())
    best_ts = upd_at or pub_at or crw_at
    age_days = max(0, (time.time() - best_ts) / 86400.0)

    if fresh_required:
        if age_days <= 2:
            fresh_boost += 25.0
        elif age_days <= 7:
            fresh_boost += 16.0
        elif age_days <= 30:
            fresh_boost += 8.0
        elif age_days <= 180:
            fresh_boost += 2.0
        else:
            fresh_boost -= 6.0
    else:
        # Evergreen query: minimal freshness impact, preserve authoritative long-standing content
        fresh_boost = max(0.0, 2.0 - (age_days * 0.01))

    # 8. Spam / Thin Page Penalties
    spam_penalty = 0.0
    body_len = len(body.strip())
    if body_len < 120:
        spam_penalty += 20.0
    if q_tokens and body_len > 0:
        # Keyword stuffing check
        first_token = q_tokens[0]
        token_count = body.count(first_token)
        density = (token_count * len(first_token)) / body_len
        if density > 0.12:
            spam_penalty += 25.0

    composite_score = round(
        bm25_score + title_boost + heading_boost + phrase_boost +
        lang_boost + quality_boost + intent_boost + fresh_boost - spam_penalty,
        2
    )

    breakdown = {
        "bm25": round(bm25_score, 2),
        "title_boost": round(title_boost, 2),
        "heading_boost": round(heading_boost, 2),
        "phrase_boost": round(phrase_boost, 2),
        "lang_boost": round(lang_boost, 2),
        "quality_boost": round(quality_boost, 2),
        "intent_boost": round(intent_boost, 2),
        "freshness_boost": round(fresh_boost, 2),
        "spam_penalty": round(spam_penalty, 2),
        "final_score": composite_score
    }

    return composite_score, breakdown


def search_local_index(query: str, limit: int = 8, query_info: dict = None):
    """
    Execute VASTUDA 5.0 Local Index Retrieval:
    1. Query FTS5 index for top candidate pool (up to 30 items)
    2. Score candidates using multi-signal relevance pipeline
    3. Apply source diversity limit (max 2 per domain in top results)
    4. Return ranked results with explainable score breakdowns
    """
    clean_q = clean_text_for_fts(query)
    if not clean_q:
        return []

    candidates = []
    try:
        with db.get_db() as conn:
            cursor = conn.cursor()
            sql = """
                SELECT 
                    d.id,
                    d.url,
                    d.canonical_url,
                    d.title,
                    d.headings,
                    d.body_text,
                    d.domain,
                    d.canonical_domain,
                    d.meta_desc,
                    d.language,
                    d.quality_score,
                    d.source_type,
                    d.published_date,
                    d.crawl_date,
                    snippet(documents_fts, 2, '<b>', '</b>', '...', 28) AS matched_snippet,
                    bm25(documents_fts, 5.0, 3.0, 1.0, 2.0) AS bm25_rank
                FROM documents_fts
                JOIN documents d ON d.id = documents_fts.rowid
                WHERE documents_fts MATCH ?
                LIMIT 40
            """
            cursor.execute(sql, (clean_q,))
            rows = cursor.fetchall()
            for r in rows:
                candidates.append(dict(r))
    except Exception as e:
        logger.warning(f"Local FTS5 query note: {e}")
        return []

    if not candidates:
        return []

    # Score each candidate
    scored = []
    for doc in candidates:
        score, breakdown = compute_relevance_score(doc, query, query_info=query_info)
        scored.append({
            "doc": doc,
            "score": score,
            "breakdown": breakdown
        })

    # Sort descending by composite score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Adaptive Domain Diversity (score-proportional damping instead of rigid hard cutoff):
    domain_counts = {}
    domain_best_scores = {}
    for item in scored:
        d = item["doc"].get("domain") or ""
        if d not in domain_best_scores:
            domain_best_scores[d] = item["score"]

    for item in scored:
        doc = item["doc"]
        domain = doc.get("domain") or ""
        curr_count = domain_counts.get(domain, 0)
        curr_score = item["score"]

        # Highest score from other domains
        other_best = max([s for d, s in domain_best_scores.items() if d != domain] or [0.0])
        score_gap = curr_score - other_best

        diversity_penalty = 0.0
        if curr_count == 1:
            # 2nd result from this domain: gentle damping if alternatives are competitive
            if score_gap < 15.0:
                diversity_penalty = 4.0
        elif curr_count == 2:
            # 3rd result from this domain: moderate damping unless vastly superior
            if score_gap < 30.0:
                diversity_penalty = 10.0
            else:
                diversity_penalty = 4.0
        elif curr_count >= 3:
            # 4th+ result: strong damping to prevent monopoly
            diversity_penalty = 22.0

        item["score"] = round(item["score"] - diversity_penalty, 2)
        item["breakdown"]["diversity_penalty"] = diversity_penalty
        domain_counts[domain] = curr_count + 1

    # Re-sort after adaptive diversity adjustments
    scored.sort(key=lambda x: x["score"], reverse=True)

    ranked_results = []
    final_domain_counts = {}
    for item in scored:
        doc = item["doc"]
        domain = doc.get("domain") or ""

        cnt = final_domain_counts.get(domain, 0)
        # Avoid total saturation if multiple domains are available
        if cnt >= 3 and len(ranked_results) < limit and len(domain_best_scores) > 1:
            continue

        final_domain_counts[domain] = cnt + 1
        snippet = doc.get("matched_snippet") or doc.get("meta_desc") or "Relevant page from VASTUDA index."

        ranked_results.append({
            "title": doc.get("title") or domain,
            "url": doc.get("canonical_url") or doc.get("url"),
            "domain": domain,
            "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
            "snippet": snippet,
            "score": item["score"],
            "score_breakdown": item["breakdown"],
            "language": doc.get("language", "en"),
            "published_date": doc.get("published_date") or "Indexed",
            "source": "VASTUDA Local Index"
        })

        if len(ranked_results) >= limit:
            break

    return ranked_results


def get_index_stats():
    """Return genuine, accurate index statistics from SQLite database."""
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) AS total FROM documents")
            doc_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(*) AS total FROM crawl_queue")
            queue_count = cur.fetchone()["total"]
            cur.execute("SELECT COUNT(DISTINCT domain) AS domains FROM documents")
            domain_count = cur.fetchone()["domains"]
            cur.execute("SELECT language, COUNT(*) AS count FROM documents GROUP BY language")
            lang_counts = {r["language"]: r["count"] for r in cur.fetchall()}
            return {
                "indexed_documents": doc_count,
                "queued_urls": queue_count,
                "unique_domains": domain_count,
                "languages": lang_counts
            }
    except Exception as e:
        logger.warning(f"Stats error: {e}")
        return {"indexed_documents": 0, "queued_urls": 0, "unique_domains": 0, "languages": {}}
