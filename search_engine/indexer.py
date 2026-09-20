"""
VASTUDA 5.3 — Production-Grade Indexer & Transparent Multi-Signal Ranking Pipeline

Features:
- FTS5 full-text indexing with SQLite WAL concurrency
- Configurable ranking weights & candidate limits via environment variables
- Transparent Multi-Signal Ranking Engine:
  * text_relevance_score (BM25 from FTS5)
  * title_score (exact phrase, quoted phrase, token overlap)
  * phrase_score (quoted exact phrase in body, contiguous term ordering)
  * url_score (domain match, term in URL path/slug, site restriction)
  * freshness_score (reliable timestamp, neutral for evergreen)
  * quality_score (substantive length, structured headings, boilerplate control)
  * authority_score (documentation, encyclopedic, academic source types)
  * query_intent_score (query-document intent alignment)
  * duplicate & spam penalties (thin content, keyword stuffing)
- Adaptive domain diversity (score-proportional damping)
- Machine-readable debug breakdown in developer debug mode
- Passage snippet generation using search_validator
"""

import os
import re
import time
import hashlib
import logging
import urllib.parse
from search_engine import db
from search_engine import search_validator
try:
    from search_engine import query_engine
except ImportError:
    import query_engine

logger = logging.getLogger("VASTUDA_Indexer")

# Configurable Limits (Phase 5.3)
RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", 50))
RANKING_TOP_K = int(os.getenv("RANKING_TOP_K", 30))
FINAL_RESULTS = int(os.getenv("FINAL_RESULTS", os.getenv("SEARCH_TOP_K", 10)))

# Configurable Ranking Weights (Phase 5.3)
W_TEXT = float(os.getenv("RANK_TEXT_WEIGHT", 1.0))
W_TITLE = float(os.getenv("RANK_TITLE_WEIGHT", 1.0))
W_PHRASE = float(os.getenv("RANK_PHRASE_WEIGHT", 1.0))
W_URL = float(os.getenv("RANK_URL_WEIGHT", 1.0))
W_FRESHNESS = float(os.getenv("RANK_FRESHNESS_WEIGHT", 1.0))
W_QUALITY = float(os.getenv("RANK_QUALITY_WEIGHT", 1.0))
W_AUTHORITY = float(os.getenv("RANK_AUTHORITY_WEIGHT", 1.0))
W_INTENT = float(os.getenv("RANK_INTENT_WEIGHT", 1.0))
DIVERSITY_PENALTY_STEP = float(os.getenv("RANK_DIVERSITY_PENALTY", 4.0))


def clean_text_for_fts(text: str) -> str:
    """Sanitize query string for safe SQLite FTS5 query."""
    if not text:
        return ""
    # Remove special FTS punctuation and operators
    clean = re.sub(r'[^\w\s\u0900-\u097F]', ' ', text)
    tokens = [t for t in clean.strip().split() if len(t) > 0]
    if not tokens:
        return ""

    # Build token clauses and phrase clause if multi-token
    token_clauses = [f'"{t}"*' for t in tokens if len(t) > 1]
    if not token_clauses:
        token_clauses = [f'"{tokens[0]}"*']

    return " OR ".join(token_clauses)


def upsert_document(url=None, title: str = "", body_text: str = "", headings: str = "",
                    meta_desc: str = "", language: str = "en",
                    canonical_url: str = "", published_date: str = "",
                    quality_score: float = 1.0, content_type: str = "text/html",
                    source_type: str = "web", author: str = "",
                    inbound_links_count: int = 0, word_count: int = 0,
                    heading_count: int = 0, paragraph_count: int = 0) -> int:
    """
    Insert or update a crawled document into SQLite database and sync FTS5 index.
    Supports either dictionary object or individual arguments.
    """
    if isinstance(url, dict):
        doc = url
        url = doc.get("url", "")
        title = doc.get("title", "")
        body_text = doc.get("body_text", "")
        headings = doc.get("headings", "")
        meta_desc = doc.get("meta_desc", "")
        language = doc.get("language", "en")
        canonical_url = doc.get("canonical_url", "")
        published_date = doc.get("published_date", "")
        quality_score = doc.get("quality_score", 1.0)
        content_type = doc.get("content_type", "text/html")
        source_type = doc.get("source_type", "web")
        author = doc.get("author", "")
        inbound_links_count = doc.get("inbound_links_count", 0)
        word_count = doc.get("word_count", 0)
        heading_count = doc.get("heading_count", 0)
        paragraph_count = doc.get("paragraph_count", 0)

    if not url or not body_text:
        return 0

    clean_url = search_validator.normalize_url(url.strip()) or url.strip()
    try:
        domain = urllib.parse.urlparse(clean_url).netloc.lower()
    except Exception:
        domain = ""

    canon_url = search_validator.normalize_url((canonical_url or clean_url).strip()) or clean_url
    try:
        canonical_domain = urllib.parse.urlparse(canon_url).netloc.lower() or domain
    except Exception:
        canonical_domain = domain

    content_hash = hashlib.sha256(body_text.strip().encode("utf-8", errors="ignore")).hexdigest()
    now = int(time.time())

    w_count = word_count or len(body_text.split())
    h_count = heading_count or len([h for h in headings.split("|") if h.strip()])
    p_count = paragraph_count or max(1, len(body_text.split(". ")))

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
                    inbound_links_count = ?,
                    word_count = ?,
                    heading_count = ?,
                    paragraph_count = ?
                WHERE id = ?
            """, (canon_url, title, headings, body_text, meta_desc,
                  language, domain, canonical_domain, published_date, now, content_hash,
                  quality_score, content_type, source_type, author, inbound_links_count,
                  w_count, h_count, p_count, doc_id))

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
                    source_type, author, inbound_links_count,
                    word_count, heading_count, paragraph_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (clean_url, canon_url, title, headings, body_text,
                  meta_desc, language, domain, canonical_domain, published_date,
                  now, content_hash, quality_score, content_type,
                  source_type, author, inbound_links_count,
                  w_count, h_count, p_count))
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


def index_document(url: str, title: str, body_text: str, headings: str = "",
                   meta_desc: str = "", language: str = "en",
                   canonical_url: str = "", published_date: str = "",
                   quality_score: float = 1.0, content_type: str = "text/html",
                   source_type: str = "web", author: str = "",
                   inbound_links_count: int = 0) -> int:
    """Backward-compatible wrapper around upsert_document."""
    return upsert_document(
        url=url, title=title, body_text=body_text, headings=headings,
        meta_desc=meta_desc, language=language, canonical_url=canonical_url,
        published_date=published_date, quality_score=quality_score,
        content_type=content_type, source_type=source_type, author=author,
        inbound_links_count=inbound_links_count
    )


def delete_document(identifier) -> bool:
    """Safely delete a document by ID or URL from documents and documents_fts."""
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
                doc_id = int(identifier)
            else:
                cur.execute("SELECT id FROM documents WHERE url = ? OR canonical_url = ?", (identifier, identifier))
                row = cur.fetchone()
                if not row:
                    return False
                doc_id = row["id"]

            cur.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            try:
                cur.execute("DELETE FROM documents_fts WHERE rowid = ?", (doc_id,))
            except Exception:
                pass
            conn.commit()
            return True
    except Exception as e:
        logger.warning(f"Delete document error: {e}")
        return False


def reindex_all() -> int:
    """Full atomic rebuild of the FTS5 virtual table from the documents table."""
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM documents_fts")
            cur.execute("""
                INSERT INTO documents_fts (rowid, title, headings, body_text, domain)
                SELECT id, title, headings, body_text, domain FROM documents
            """)
            count = cur.rowcount
            conn.commit()
            return count
    except Exception as e:
        logger.warning(f"Reindex all error: {e}")
        return 0


def get_index_vocabulary(min_freq: int = 1) -> dict:
    """Extract real document tokens and frequencies from SQLite documents for spell-checker and suggestions."""
    vocab = {}
    try:
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT title, headings FROM documents")
            for row in cur.fetchall():
                text = f"{row['title']} {row['headings']}"
                words = re.findall(r'[a-zA-Z0-9_\-\.\+]{2,}', text.lower())
                for w in words:
                    vocab[w] = vocab.get(w, 0) + 1
    except Exception as e:
        logger.warning(f"Vocabulary build error: {e}")
    return {k: v for k, v in vocab.items() if v >= min_freq}


def compute_relevance_score(doc: dict, query: str, query_info: dict = None) -> tuple:
    """
    Transparent Multi-Signal Relevance Scorer (Phase 5.3):
    Evaluates:
    - Base BM25 text match (from FTS5) * W_TEXT
    - Title matches (exact query, quoted phrases, token overlap) * W_TITLE
    - Heading matches
    - Phrase matches (quoted phrases in body, contiguous word ordering) * W_PHRASE
    - URL and domain matches (query terms in path, domain match, site: restriction) * W_URL
    - Language congruence
    - Source quality & Content structure * W_QUALITY
    - Authority signal * W_AUTHORITY
    - Query intent congruence * W_INTENT
    - Freshness signal (query-dependent) * W_FRESHNESS
    - Low-quality / spam penalties
    Returns (composite_score, score_breakdown).
    """
    q_info = query_info or {}
    q_lower = (q_info.get("normalized_query") or query).strip().lower()
    tokens = q_info.get("tokens") or [t for t in re.sub(r'[^\w\s\u0900-\u097F]', ' ', q_lower).split() if len(t) > 1]
    phrases = q_info.get("phrases") or []

    title = (doc.get("title") or "").lower()
    headings = (doc.get("headings") or "").lower()
    body = (doc.get("body_text") or doc.get("snippet") or "").lower()
    doc_url = (doc.get("canonical_url") or doc.get("url") or "").lower()
    doc_domain = (doc.get("canonical_domain") or doc.get("domain") or "").lower()
    doc_lang = (doc.get("language") or "en").lower()

    raw_bm25 = abs(float(doc.get("bm25_rank") or 1.0))
    bm25_score = min(raw_bm25 * 8.0, 50.0)

    # 1. Title Signals (Step 6)
    title_boost = 0.0
    if q_lower and q_lower in title:
        title_boost += 35.0  # Full exact query phrase in title
    else:
        # Check quoted phrases in title
        for p in phrases:
            if p.lower() in title:
                title_boost += 20.0
                break
        if tokens:
            matched_tokens = sum(1 for t in tokens if t in title)
            ratio = matched_tokens / len(tokens)
            title_boost += ratio * 22.0

    # 2. Heading Signals
    heading_boost = 0.0
    if q_lower and q_lower in headings:
        heading_boost += 16.0
    elif tokens:
        matched_h = sum(1 for t in tokens if t in headings)
        heading_boost += (matched_h / max(len(tokens), 1)) * 10.0

    # 3. Phrase Signals (Step 7)
    phrase_boost = 0.0
    # Strong boost for user's explicit quoted phrases appearing in body
    for p in phrases:
        if p.lower() in body:
            phrase_boost += 16.0
            break

    # Natural word-order bonus for normal queries
    if len(tokens) > 1:
        if q_lower in body:
            phrase_boost += 12.0
        else:
            # Check 2-token contiguous bigrams in body
            bigram_matches = 0
            for i in range(len(tokens) - 1):
                bigram = f"{tokens[i]} {tokens[i+1]}"
                if bigram in body:
                    bigram_matches += 1
            if bigram_matches > 0:
                phrase_boost += min(8.0, bigram_matches * 3.0)

    # 4. URL and Domain Signals (Step 8)
    url_boost = 0.0
    site_restr = q_info.get("site_restriction")
    if site_restr and (site_restr in doc_domain or doc_domain in site_restr):
        url_boost += 30.0  # Explicit site: restriction satisfied

    # Check query terms in URL path / slug
    if tokens:
        tokens_in_url = sum(1 for t in tokens if t in doc_url)
        if tokens_in_url > 0:
            url_boost += min(8.0, (tokens_in_url / len(tokens)) * 8.0)

    # Navigational root domain match
    if q_info.get("intent") in ("navigational", "domain") and any(t in doc_domain for t in tokens):
        url_boost += 10.0

    # 5. Language Match Signal
    lang_boost = 0.0
    query_lang = q_info.get("language", "en")
    if query_lang == doc_lang:
        lang_boost += 10.0
    elif query_lang == "hinglish" and (doc_lang in ("en", "hi") or any(t in body for t in ["sikhe", "kare", "kaise", "hindi"])):
        lang_boost += 8.0

    # 6. Measurable Content Structure Quality (Step 9)
    quality_boost = 0.0
    body_word_count = len(body.split())
    if 250 <= body_word_count <= 10000:
        quality_boost += 4.0  # Substantive content length
    if headings and len(headings.strip()) > 15:
        quality_boost += 3.0  # Structured document with headings
    if doc.get("meta_desc") and len(str(doc.get("meta_desc")).strip()) > 25:
        quality_boost += 2.0  # Quality metadata description present

    # 7. Authority Signal (Documentation, Encyclopedic, Academic)
    authority_boost = 0.0
    s_type = (doc.get("source_type") or "web").lower()
    c_type = (doc.get("content_type") or "web").lower()
    if s_type in ("academic", "encyclopedic", "curated_seed") or "wiki" in doc_domain:
        authority_boost += 5.0
    elif "doc" in s_type or "doc" in c_type or any(d in doc_domain for d in ["python.org", "mozilla.org", "docker.com", "sqlite.org", "git-scm.com"]):
        authority_boost += 5.0

    # 8. Intent-Aligned Content Congruence (Step 3 & 5)
    intent_boost = 0.0
    q_intent = q_info.get("intent", "informational")
    if q_intent in ("tutorial", "code", "technical") and ("doc" in c_type or "doc" in s_type or any(d in doc_domain for d in ["python.org", "mozilla.org", "docker.com", "sqlite.org"])):
        intent_boost += 6.0
    elif q_intent in ("academic", "definition") and (s_type in ("academic", "encyclopedic") or "wiki" in doc_domain):
        intent_boost += 6.0
    elif q_intent == "navigational" and doc.get("canonical_url", "").rstrip("/") == f"https://{doc_domain}":
        intent_boost += 8.0

    # 9. Freshness Signal (Step 13)
    fresh_boost = 0.0
    fresh_required = q_info.get("freshness_required", False)

    def _parse_ts(val):
        if not val:
            return 0
        if isinstance(val, (int, float)):
            return int(val)
        try:
            return int(float(str(val).strip()))
        except (ValueError, TypeError):
            return 0

    pub_at = _parse_ts(doc.get("published_at"))
    upd_at = _parse_ts(doc.get("updated_at"))
    crw_at = _parse_ts(doc.get("crawled_at") or doc.get("crawl_date")) or int(time.time())
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
        # Evergreen query: minimal freshness impact, preserve authoritative content
        fresh_boost = max(0.0, 2.0 - (age_days * 0.01))

    # 10. Spam / Thin Page Penalties (Step 9 & 14)
    spam_penalty = 0.0
    is_external_snippet = (doc.get("source") != "VASTUDA Local Index" and not doc.get("body_text"))
    body_len = len(body.strip())
    if not is_external_snippet:
        if body_len < 60:
            spam_penalty += 40.0
        elif body_len < 120:
            spam_penalty += 20.0

    if tokens and body_len > 0:
        # Keyword stuffing check
        first_token = tokens[0]
        token_count = body.count(first_token)
        density = (token_count * len(first_token)) / body_len
        if density > 0.12:
            spam_penalty += 25.0

    # Composite weighted score calculation
    weighted_text = bm25_score * W_TEXT
    weighted_title = title_boost * W_TITLE
    weighted_phrase = phrase_boost * W_PHRASE
    weighted_url = url_boost * W_URL
    weighted_freshness = fresh_boost * W_FRESHNESS
    weighted_quality = quality_boost * W_QUALITY
    weighted_authority = authority_boost * W_AUTHORITY
    weighted_intent = intent_boost * W_INTENT

    composite_score = round(
        weighted_text + weighted_title + heading_boost + weighted_phrase +
        weighted_url + lang_boost + weighted_quality + weighted_authority +
        weighted_intent + weighted_freshness - spam_penalty,
        2
    )

    breakdown = {
        "bm25": round(weighted_text, 2),
        "title_boost": round(weighted_title, 2),
        "heading_boost": round(heading_boost, 2),
        "phrase_boost": round(weighted_phrase, 2),
        "url_boost": round(weighted_url, 2),
        "lang_boost": round(lang_boost, 2),
        "quality_boost": round(weighted_quality, 2),
        "authority_boost": round(weighted_authority, 2),
        "intent_boost": round(weighted_intent, 2),
        "freshness_boost": round(weighted_freshness, 2),
        "spam_penalty": round(spam_penalty, 2),
        "final_score": composite_score,
        "signals": {
            "text": round(weighted_text, 2),
            "title": round(weighted_title, 2),
            "phrase": round(weighted_phrase, 2),
            "url": round(weighted_url, 2),
            "freshness": round(weighted_freshness, 2),
            "quality": round(weighted_quality, 2),
            "authority": round(weighted_authority, 2),
            "intent": round(weighted_intent, 2),
            "spam_penalty": round(spam_penalty, 2)
        }
    }

    return composite_score, breakdown


def search_local_index(query: str, limit: int = None, query_info: dict = None, debug: bool = False):
    """
    Execute VASTUDA 5.3 Production Local Index Retrieval:
    1. Query FTS5 index for top candidate pool (up to RETRIEVAL_TOP_K items)
    2. Respect site: restriction if present
    3. Score candidates using transparent multi-signal relevance pipeline
    4. Apply adaptive domain diversity damping
    5. Generate query-relevant passage snippets
    6. Return ranked results (top FINAL_RESULTS or requested limit)
    """
    if limit is None:
        limit = FINAL_RESULTS

    clean_q = clean_text_for_fts(query)
    if not clean_q:
        return []

    q_info = query_info or {}
    site_restr = q_info.get("site_restriction")

    candidates = []
    try:
        with db.get_db() as conn:
            cursor = conn.cursor()
            if site_restr:
                sql = f"""
                    SELECT 
                        d.id, d.url, d.canonical_url, d.title, d.headings,
                        d.body_text, d.domain, d.canonical_domain, d.meta_desc,
                        d.language, d.quality_score, d.source_type, d.content_type,
                        d.published_date, d.crawl_date,
                        bm25(documents_fts, 5.0, 3.0, 1.0, 2.0) AS bm25_rank
                    FROM documents_fts
                    JOIN documents d ON d.id = documents_fts.rowid
                    WHERE documents_fts MATCH ? AND (d.domain LIKE ? OR d.canonical_domain LIKE ?)
                    LIMIT {RETRIEVAL_TOP_K}
                """
                cursor.execute(sql, (clean_q, f"%{site_restr}%", f"%{site_restr}%"))
            else:
                sql = f"""
                    SELECT 
                        d.id, d.url, d.canonical_url, d.title, d.headings,
                        d.body_text, d.domain, d.canonical_domain, d.meta_desc,
                        d.language, d.quality_score, d.source_type, d.content_type,
                        d.published_date, d.crawl_date,
                        bm25(documents_fts, 5.0, 3.0, 1.0, 2.0) AS bm25_rank
                    FROM documents_fts
                    JOIN documents d ON d.id = documents_fts.rowid
                    WHERE documents_fts MATCH ?
                    LIMIT {RETRIEVAL_TOP_K}
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
        score, breakdown = compute_relevance_score(doc, query, query_info=q_info)
        scored.append({
            "doc": doc,
            "score": score,
            "breakdown": breakdown
        })

    # Sort descending by composite score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Adaptive Domain Diversity (Step 11)
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

        other_best = max([s for d, s in domain_best_scores.items() if d != domain] or [0.0])
        score_gap = curr_score - other_best

        diversity_penalty = 0.0
        if curr_count == 1:
            if score_gap < 15.0:
                diversity_penalty = DIVERSITY_PENALTY_STEP
        elif curr_count == 2:
            if score_gap < 30.0:
                diversity_penalty = DIVERSITY_PENALTY_STEP * 2.5
            else:
                diversity_penalty = DIVERSITY_PENALTY_STEP
        elif curr_count >= 3:
            diversity_penalty = DIVERSITY_PENALTY_STEP * 5.5

        item["score"] = round(item["score"] - diversity_penalty, 2)
        item["breakdown"]["diversity_penalty"] = diversity_penalty
        item["breakdown"]["signals"]["diversity_penalty"] = diversity_penalty
        domain_counts[domain] = curr_count + 1

    # Re-sort after adaptive diversity adjustments
    scored.sort(key=lambda x: x["score"], reverse=True)

    ranked_results = []
    final_domain_counts = {}
    for item in scored:
        doc = item["doc"]
        domain = doc.get("domain") or ""

        cnt = final_domain_counts.get(domain, 0)
        # Prevent monopoly if alternatives exist
        if cnt >= 3 and len(ranked_results) < limit and len(domain_best_scores) > 1:
            continue

        final_domain_counts[domain] = cnt + 1

        # High-quality passage snippet generation (Step 12)
        raw_snippet = search_validator.generate_best_snippet(
            doc.get("body_text") or doc.get("meta_desc") or "",
            query=query,
            max_len=240
        )

        result_dict = {
            "title": doc.get("title") or domain,
            "url": doc.get("canonical_url") or doc.get("url"),
            "domain": domain,
            "display_url": (doc.get("canonical_url") or doc.get("url", "")).replace("https://", "").replace("http://", "").rstrip("/"),
            "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
            "snippet": raw_snippet,
            "score": item["score"],
            "language": doc.get("language", "en"),
            "published_at": doc.get("published_date") or "Indexed",
            "published_date": doc.get("published_date") or "Indexed",
            "source": "VASTUDA Local Index"
        }

        # Expose internal ranking breakdown only in debug mode
        if debug:
            result_dict["score_breakdown"] = item["breakdown"]

        ranked_results.append(result_dict)

        if len(ranked_results) >= limit:
            break

    return ranked_results


def apply_domain_diversity(ranked_items: list, max_per_domain: int = 2, max_results: int = 10, penalty_step: float = None) -> list:
    """
    Apply adaptive domain diversity damping:
    - Decreases scores of repeated domains adaptively
    - Prevents any single domain from monopolizing top results
    - Preserves high-quality results from multiple domains
    """
    p_step = penalty_step or DIVERSITY_PENALTY_STEP
    domain_counts = {}
    domain_best_scores = {}
    for item in ranked_items:
        d = item.get("domain") or ""
        s = item.get("score", 0.0)
        if d not in domain_best_scores or s > domain_best_scores[d]:
            domain_best_scores[d] = s

    adjusted = []
    for item in ranked_items:
        domain = item.get("domain") or ""
        curr_count = domain_counts.get(domain, 0)
        curr_score = item.get("score", 0.0)

        other_best = max([s for d, s in domain_best_scores.items() if d != domain] or [0.0])
        score_gap = curr_score - other_best

        diversity_penalty = 0.0
        if curr_count == 1:
            if score_gap < 15.0:
                diversity_penalty = p_step
        elif curr_count == 2:
            if score_gap < 30.0:
                diversity_penalty = p_step * 2.5
            else:
                diversity_penalty = p_step
        elif curr_count >= 3:
            diversity_penalty = p_step * 5.5

        new_item = dict(item)
        new_item["score"] = round(curr_score - diversity_penalty, 2)
        if "score_breakdown" in new_item and isinstance(new_item["score_breakdown"], dict):
            new_item["score_breakdown"]["diversity_penalty"] = diversity_penalty
            if "signals" in new_item["score_breakdown"]:
                new_item["score_breakdown"]["signals"]["diversity_penalty"] = diversity_penalty
        domain_counts[domain] = curr_count + 1
        adjusted.append(new_item)

    adjusted.sort(key=lambda x: x.get("score", 0), reverse=True)

    final_results = []
    final_counts = {}
    for item in adjusted:
        d = item.get("domain") or ""
        cnt = final_counts.get(d, 0)
        if cnt >= max_per_domain and len(final_results) < max_results and len(domain_best_scores) > 1:
            continue
        final_counts[d] = cnt + 1
        final_results.append(item)
        if len(final_results) >= max_results:
            break

    # If limit not met due to diversity filters, append remaining items
    if len(final_results) < max_results:
        for item in adjusted:
            if item not in final_results:
                final_results.append(item)
                if len(final_results) >= max_results:
                    break

    return final_results


def score_candidates(candidates: list, query: str, query_info: dict = None, debug: bool = False, max_results: int = 10) -> list:
    """
    Score and rank a candidate pool (from local index, web providers, or combined)
    using the transparent multi-signal ranking formula and adaptive domain diversity.
    """
    if not candidates:
        return []

    q_info = query_info or query_engine.understand_query(query)
    scored = []
    for cand in candidates:
        score, breakdown = compute_relevance_score(cand, query, query_info=q_info)
        item = dict(cand)
        item["score"] = score
        if debug:
            item["score_breakdown"] = breakdown
        scored.append(item)

    scored.sort(key=lambda x: x.get("score", 0), reverse=True)
    return apply_domain_diversity(scored, max_per_domain=2, max_results=max_results)


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
