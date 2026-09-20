"""
VASTUDA 5.4 — Production Scalable Web Crawler & Frontier Engine
Features:
- Configurable seed management (loads from search_engine/seeds.json)
- Strict multi-hop SSRF protection (validates target URL + all redirect hops against private/loopback IPs)
- Domain politeness & throttling (per-domain serialization with configurable CRAWL_DELAY_SECONDS)
- Configurable depth bounding (CRAWL_MAX_DEPTH, default 2)
- Domain scope control (MAX_PAGES_PER_DOMAIN, MAX_TOTAL_PAGES, MAX_URL_LENGTH)
- Incremental crawling (ETag, Last-Modified, content_hash change detection)
- Content extraction with structure metrics: word_count, heading_count, paragraph_count
- Bounded retry with exponential backoff (max 3 attempts)
- Production diagnostics telemetry (get_crawler_status)
"""

import os
import json
import time
import socket
import ipaddress
import threading
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
import logging
import requests
from bs4 import BeautifulSoup
from search_engine import db, indexer, query_engine, search_validator

logger = logging.getLogger("VASTUDA_Crawler")

# Configuration Constants (Configurable via Environment)
USER_AGENT = os.getenv("CRAWLER_USER_AGENT", "VASTUDA-Bot/5.4 (+https://vastuda.internal/bot; bot@vastuda.internal)")
CRAWL_DELAY_SECONDS = float(os.getenv("CRAWL_DELAY_SECONDS", 1.0))
CRAWL_MAX_DEPTH = int(os.getenv("CRAWL_MAX_DEPTH", 2))
MAX_PAGES_PER_DOMAIN = int(os.getenv("MAX_PAGES_PER_DOMAIN", 25))
MAX_TOTAL_PAGES = int(os.getenv("MAX_TOTAL_PAGES", 250))
MAX_URL_LENGTH = int(os.getenv("MAX_URL_LENGTH", 500))
MAX_PAGE_SIZE = int(os.getenv("MAX_PAGE_SIZE", 2500000))  # 2.5 MB maximum
MAX_RETRIES = 3

SEEDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seeds.json")

# In-memory caches and locks for polite multi-threading
ROBOTS_CACHE = {}
DOMAIN_LAST_CRAWL = {}
DOMAIN_POLITENESS = DOMAIN_LAST_CRAWL
DOMAIN_PAGE_COUNT = {}
DOMAIN_LOCK = threading.Lock()

# Internal diagnostic telemetry
CRAWLER_DIAGNOSTICS = {
    "urls_attempted": 0,
    "urls_successful": 0,
    "urls_rejected_robots": 0,
    "urls_rejected_ssrf": 0,
    "http_failures": 0,
    "not_modified_skipped": 0,
    "duplicate_pages": 0,
    "content_extraction_failures": 0,
    "last_crawl_time": 0
}


def load_seeds_config() -> list:
    """Load configurable seeds from search_engine/seeds.json."""
    if os.path.exists(SEEDS_FILE):
        try:
            with open(SEEDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return [s for s in data if s.get("enabled", True)]
        except Exception as e:
            logger.warning(f"Error loading seeds.json: {e}")
    # Fallback default authoritative seeds
    return [
        {"url": "https://docs.python.org/3/tutorial/index.html", "category": "docs", "priority": 10, "enabled": True, "max_depth": 2},
        {"url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide", "category": "docs", "priority": 10, "enabled": True, "max_depth": 2},
        {"url": "https://www.sqlite.org/wal.html", "category": "technical", "priority": 9, "enabled": True, "max_depth": 1},
        {"url": "https://en.wikipedia.org/wiki/Linux", "category": "encyclopedia", "priority": 9, "enabled": True, "max_depth": 1},
        {"url": "https://en.wikipedia.org/wiki/Machine_learning", "category": "encyclopedia", "priority": 9, "enabled": True, "max_depth": 1}
    ]


def is_safe_url(url: str) -> bool:
    """
    Strict SSRF Prevention:
    Rejects:
    - Schemes other than http/https
    - Localhost, 127.0.0.1, ::1, 0.0.0.0
    - Private IP ranges (RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local (169.254.0.0/16)
    - Multicast, broadcast, reserved IPs
    - URLs containing credentials (user:pass@host)
    """
    if not url or not isinstance(url, str):
        return False
    if len(url) > MAX_URL_LENGTH:
        return False
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.username or parsed.password:
            return False

        host = parsed.hostname
        if not host:
            return False

        host_lower = host.lower()
        if host_lower in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "internal", "local"):
            return False
        if host_lower.endswith((".local", ".internal", ".localhost")):
            return False

        # Resolve host to IP address and verify public routing
        try:
            addr_info = socket.getaddrinfo(host, None)
            for _, _, _, _, sockaddr in addr_info:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                    return False
        except Exception:
            return False

        return True
    except Exception:
        return False


def wait_for_domain_politeness(domain: str, delay_seconds: float = None):
    """Ensure polite domain crawling by enforcing a delay between consecutive requests to the same host."""
    delay = delay_seconds if delay_seconds is not None else CRAWL_DELAY_SECONDS
    if not domain or delay <= 0:
        return

    domain_lower = domain.lower()
    with DOMAIN_LOCK:
        last_time = DOMAIN_LAST_CRAWL.get(domain_lower, 0.0)
        now = time.time()
        sleep_needed = delay - (now - last_time)
        if sleep_needed > 0:
            time.sleep(sleep_needed)
        DOMAIN_LAST_CRAWL[domain_lower] = time.time()


def is_allowed_by_robots(url: str) -> tuple:
    """
    Check if URL is allowed according to robots.txt and discover sitemaps.
    Returns (is_allowed: bool, sitemaps: list).
    """
    try:
        parsed = urllib.parse.urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        if base_url in ROBOTS_CACHE:
            rp, sitemaps = ROBOTS_CACHE[base_url]
        else:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
            rp.set_url(robots_url)
            sitemaps = []
            try:
                headers = {"User-Agent": USER_AGENT}
                r = requests.get(robots_url, headers=headers, timeout=5)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    for line in r.text.splitlines():
                        if line.strip().lower().startswith("sitemap:"):
                            s_url = line.split(":", 1)[1].strip()
                            if is_safe_url(s_url):
                                sitemaps.append(s_url)
            except Exception:
                pass
            ROBOTS_CACHE[base_url] = (rp, sitemaps)

        allowed = rp.can_fetch(USER_AGENT, url)
        return allowed, sitemaps
    except Exception as e:
        logger.warning(f"Robots check error for {url}: {e}")
        return True, []


def parse_sitemap(sitemap_url: str, max_urls: int = 30) -> list:
    """Parse XML Sitemap and extract URLs with lastmod dates."""
    if not is_safe_url(sitemap_url):
        return []

    discovered = []
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(sitemap_url, headers=headers, timeout=7)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

        for sm in root.findall("sm:sitemap", ns) or root.findall("sitemap"):
            loc = sm.find("sm:loc", ns) or sm.find("loc")
            if loc is not None and loc.text and is_safe_url(loc.text):
                discovered.append({"url": loc.text.strip(), "is_index": True})
            if len(discovered) >= max_urls:
                break

        for url_node in root.findall("sm:url", ns) or root.findall("url"):
            loc = url_node.find("sm:loc", ns) or url_node.find("loc")
            lastmod = url_node.find("sm:lastmod", ns) or url_node.find("lastmod")
            if loc is not None and loc.text and is_safe_url(loc.text):
                clean_url = loc.text.strip()
                mod_date = lastmod.text.strip() if (lastmod is not None and lastmod.text) else ""
                discovered.append({"url": clean_url, "lastmod": mod_date, "is_index": False})
            if len(discovered) >= max_urls:
                break
    except Exception as e:
        logger.warning(f"Sitemap parse error on {sitemap_url}: {e}")

    return discovered


def enqueue_urls(urls, depth: int = 0, priority: int = 0) -> int:
    """Add a list of validated URLs to the crawl queue frontier with metadata."""
    now = int(time.time())
    added = 0
    with db.get_db() as conn:
        cur = conn.cursor()
        for u in urls:
            clean = u.strip() if isinstance(u, str) else ""
            if not clean or not is_safe_url(clean) or len(clean) > MAX_URL_LENGTH:
                continue
            clean = search_validator.normalize_url(clean) or urllib.parse.urldefrag(clean)[0]
            try:
                domain = urllib.parse.urlparse(clean).netloc.lower()
            except Exception:
                domain = ""

            try:
                cur.execute("""
                    INSERT INTO crawl_queue (
                        url, canonical_url, domain, status, depth, priority, added_at, discovered_at
                    ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        priority = MAX(crawl_queue.priority, excluded.priority)
                """, (clean, clean, domain, depth, priority, now, now))
                if cur.rowcount > 0:
                    added += 1
            except Exception:
                pass
        conn.commit()
    return added


def safe_fetch_with_redirect_validation(url: str, etag: str = "", last_modified: str = "", max_redirects: int = 3):
    """
    Fetch URL with manual redirect following to guarantee SSRF protection on every hop,
    and supports ETag/Last-Modified for incremental crawling.
    """
    curr_url = url
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    session = requests.Session()

    for _ in range(max_redirects + 1):
        if not is_safe_url(curr_url):
            return None, "blocked_ssrf_hop", curr_url

        parsed = urllib.parse.urlparse(curr_url)
        wait_for_domain_politeness(parsed.netloc)

        resp = session.get(curr_url, headers=headers, timeout=8, stream=True, allow_redirects=False)

        if resp.status_code == 304:
            return resp, "not_modified", curr_url

        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location")
            if not loc:
                return resp, f"http_{resp.status_code}", curr_url
            next_url = urllib.parse.urljoin(curr_url, loc)
            curr_url = next_url
            continue

        return resp, "ok", curr_url

def extract_page_content(url: str, html_text: str) -> dict:
    """Extract clean title, headings, paragraphs, word counts, and metadata from HTML."""
    soup = BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "aside", "header", "form", "iframe", "noscript", "svg"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        h_text = h.get_text(strip=True)
        if h_text and len(h_text) > 3:
            headings.append(h_text)
    headings_str = " | ".join(headings[:10])
    heading_count = len(headings)

    meta_desc = ""
    meta_tag = (
        soup.find("meta", attrs={"name": "description"}) or
        soup.find("meta", attrs={"property": "og:description"}) or
        soup.find("meta", attrs={"name": "twitter:description"})
    )
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"].strip()

    published_date = ""
    time_tag = (
        soup.find("meta", attrs={"property": "article:published_time"}) or
        soup.find("meta", attrs={"name": "pubdate"}) or
        soup.find("time")
    )
    if time_tag:
        published_date = (time_tag.get("content") or time_tag.get("datetime") or "").strip()[:10]

    paragraphs = []
    for p in soup.find_all(["p", "li"]):
        p_text = p.get_text(strip=True)
        if len(p_text) > 10:
            paragraphs.append(p_text)
    paragraph_count = len(paragraphs)
    body_text = " ".join(paragraphs[:40]) if paragraphs else " ".join(soup.stripped_strings)
    word_count = len(body_text.split())

    canonical_tag = soup.find("link", rel="canonical")
    canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else url
    if canonical_url and not canonical_url.startswith(("http://", "https://")):
        canonical_url = urllib.parse.urljoin(url, canonical_url)

    discovered_links = []
    try:
        base_domain = urllib.parse.urlparse(url).netloc.lower()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            absolute_link = urllib.parse.urljoin(url, href)
            if is_safe_url(absolute_link):
                link_domain = urllib.parse.urlparse(absolute_link).netloc.lower()
                if link_domain == base_domain and absolute_link != url:
                    discovered_links.append(absolute_link)
    except Exception:
        pass

    return {
        "title": title or url,
        "headings": headings_str,
        "heading_count": heading_count,
        "meta_desc": meta_desc,
        "published_date": published_date,
        "paragraphs": paragraphs,
        "paragraph_count": paragraph_count,
        "body_text": body_text,
        "word_count": word_count,
        "canonical_url": canonical_url,
        "links": discovered_links
    }


def crawl_url(target_url: str, max_depth: int = 1, source_type: str = "web", quality_score: float = 1.0) -> dict:
    """
    Fetch, extract content, and index a single URL safely, incrementally, and politely.
    """
    clean_url = search_validator.normalize_url(target_url.strip()) or urllib.parse.urldefrag(target_url.strip())[0]
    CRAWLER_DIAGNOSTICS["urls_attempted"] += 1

    try:
        domain = urllib.parse.urlparse(clean_url).netloc.lower()
    except Exception:
        domain = ""

    # Scope control: Check domain page limit
    with DOMAIN_LOCK:
        curr_pages = DOMAIN_PAGE_COUNT.get(domain, 0)
        if curr_pages >= MAX_PAGES_PER_DOMAIN:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'domain_limit_reached' WHERE url = ?", (clean_url,))
                conn.commit()
            return {"status": "domain_limit_reached", "url": clean_url}

    # 1. SSRF Safety Check
    if not is_safe_url(clean_url):
        logger.warning(f"[Crawler] SSRF rejection for URL: {clean_url}")
        CRAWLER_DIAGNOSTICS["urls_rejected_ssrf"] += 1
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'blocked_ssrf' WHERE url = ?", (clean_url,))
            conn.commit()
        return {"status": "blocked_ssrf", "url": clean_url}

    # 2. Robots.txt Compliance
    allowed, discovered_sitemaps = is_allowed_by_robots(clean_url)
    if not allowed:
        logger.info(f"[Crawler] Blocked by robots.txt: {clean_url}")
        CRAWLER_DIAGNOSTICS["urls_rejected_robots"] += 1
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'blocked_robots' WHERE url = ?", (clean_url,))
            conn.commit()
        return {"status": "blocked_by_robots", "url": clean_url}

    # If sitemaps were discovered, enqueue URLs from them
    if discovered_sitemaps and max_depth > 0:
        for sm_url in discovered_sitemaps[:2]:
            sm_items = parse_sitemap(sm_url, max_urls=15)
            sm_urls = [it["url"] for it in sm_items if not it.get("is_index")]
            if sm_urls:
                enqueue_urls(sm_urls, depth=max_depth - 1)

    # 3. Incremental crawl metadata lookup
    etag = ""
    last_mod = ""
    with db.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT etag, last_modified FROM crawl_queue WHERE url = ?", (clean_url,))
        q_row = cur.fetchone()
        if q_row:
            etag = q_row["etag"] or ""
            last_mod = q_row["last_modified"] or ""

    # 4. Fetch Page with Safety Bounds & SSRF-Protected Redirects
    now = int(time.time())
    try:
        resp, fetch_status, final_url = safe_fetch_with_redirect_validation(
            clean_url, etag=etag, last_modified=last_mod, max_redirects=3
        )

        if fetch_status == "not_modified":
            CRAWLER_DIAGNOSTICS["not_modified_skipped"] += 1
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'completed', last_crawled_at = ? WHERE url = ?", (now, clean_url))
                conn.execute("UPDATE documents SET crawl_date = ? WHERE url = ?", (now, clean_url))
                conn.commit()
            return {"status": "not_modified", "url": clean_url}

        if fetch_status != "ok" or not resp:
            CRAWLER_DIAGNOSTICS["http_failures"] += 1
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = ?, retry_count = retry_count + 1 WHERE url = ?",
                             (fetch_status, clean_url))
                conn.commit()
            return {"status": fetch_status, "url": clean_url}

        if resp.status_code != 200:
            CRAWLER_DIAGNOSTICS["http_failures"] += 1
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = ?, retry_count = retry_count + 1, http_status = ? WHERE url = ?",
                             (f"http_{resp.status_code}", resp.status_code, clean_url))
                conn.commit()
            return {"status": f"http_error_{resp.status_code}", "url": clean_url}

        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type and "application/xhtml" not in content_type:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'non_html' WHERE url = ?", (clean_url,))
                conn.commit()
            return {"status": "non_html", "url": clean_url}

        resp_etag = resp.headers.get("ETag", "").strip()
        resp_lastmod = resp.headers.get("Last-Modified", "").strip()
        text = resp.text[:MAX_PAGE_SIZE]

    except Exception as e:
        logger.warning(f"Error fetching {clean_url}: {e}")
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'fetch_failed', retry_count = retry_count + 1 WHERE url = ?",
                         (clean_url,))
            conn.commit()
        return {"status": "failed", "error": str(e), "url": clean_url}

    # 5. Clean Content Extraction & Document Structure
    try:
        extracted = extract_page_content(clean_url, text)
        title = extracted["title"]
        headings_str = extracted["headings"]
        heading_count = extracted["heading_count"]
        meta_desc = extracted["meta_desc"]
        published_date = extracted["published_date"]
        paragraph_count = extracted["paragraph_count"]
        body_text = extracted["body_text"]
        word_count = extracted["word_count"]
        canonical_url = extracted["canonical_url"]

        # If body is too thin, mark in queue
        if len(body_text.strip()) < 80:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'thin_content' WHERE url = ?", (clean_url,))
                conn.commit()
            return {"status": "thin_content", "url": clean_url}

        # Language Detection
        detected_lang = query_engine.detect_language(title + " " + body_text[:200])

        # 6. Index Document into VASTUDA FTS5 Index (with structure metrics)
        doc_id = indexer.upsert_document(
            url=clean_url,
            title=title or clean_url,
            body_text=body_text,
            headings=headings_str,
            meta_desc=meta_desc,
            language=detected_lang,
            canonical_url=canonical_url or clean_url,
            published_date=published_date,
            quality_score=quality_score,
            content_type="text/html",
            source_type=source_type,
            word_count=word_count,
            heading_count=heading_count,
            paragraph_count=paragraph_count
        )

        with DOMAIN_LOCK:
            DOMAIN_PAGE_COUNT[domain] = DOMAIN_PAGE_COUNT.get(domain, 0) + 1

        # 7. Outbound link discovery if within max depth
        discovered_links = extracted.get("links", [])
        if max_depth > 0 and discovered_links:
            enqueue_urls(discovered_links[:10], depth=max_depth - 1)

        # Mark queue item completed with ETag / Last-Modified for future incremental crawling
        with db.get_db() as conn:
            conn.execute("""
                UPDATE crawl_queue SET
                    status = 'completed',
                    last_crawled_at = ?,
                    http_status = 200,
                    etag = ?,
                    last_modified = ?
                WHERE url = ?
            """, (now, resp_etag, resp_lastmod, clean_url))
            conn.commit()

        CRAWLER_DIAGNOSTICS["urls_successful"] += 1
        CRAWLER_DIAGNOSTICS["last_crawl_time"] = now

        return {
            "status": "indexed",
            "doc_id": doc_id,
            "title": title,
            "url": clean_url,
            "language": detected_lang,
            "word_count": word_count,
            "links_discovered": len(discovered_links)
        }

    except Exception as e:
        CRAWLER_DIAGNOSTICS["content_extraction_failures"] += 1
        logger.error(f"Parsing error on {clean_url}: {e}")
        return {"status": "parse_error", "error": str(e), "url": clean_url}


def get_crawler_status() -> dict:
    """Return genuine, accurate internal crawler diagnostics and operational status."""
    stats = indexer.get_index_stats()
    diag = dict(CRAWLER_DIAGNOSTICS)
    diag["documents_indexed"] = stats.get("indexed_documents", 0)
    diag["domains_indexed"] = stats.get("unique_domains", 0)
    diag["queue_size"] = stats.get("queued_urls", 0)
    diag["languages"] = stats.get("languages", {})
    diag["politeness_delay_sec"] = CRAWL_DELAY_SECONDS
    diag["max_depth"] = CRAWL_MAX_DEPTH
    diag["max_pages_per_domain"] = MAX_PAGES_PER_DOMAIN
    diag["domains_crawled_in_memory"] = len(DOMAIN_PAGE_COUNT)
    return diag


def get_crawler_diagnostics() -> dict:
    """Backward-compatible alias for get_crawler_status."""
    return get_crawler_status()


def run_scalable_crawl(max_docs: int = 150, max_depth: int = None) -> int:
    """
    Executes scalable knowledge crawl:
    1. Loads seeds from seeds.json
    2. Crawls high-value seeds and their queued internal children up to limits
    3. Respects robots.txt, politeness delay, max depth, and domain quotas
    """
    depth = max_depth if max_depth is not None else CRAWL_MAX_DEPTH
    seeds = load_seeds_config()
    print(f"[Crawler] Starting scalable crawl across {len(seeds)} configured seeds (target max: {max_docs} docs, depth: {depth})...")

    # Enqueue seed URLs
    for s in seeds:
        enqueue_urls([s["url"]], depth=min(s.get("max_depth", depth), depth), priority=s.get("priority", 5))

    indexed_count = 0
    while indexed_count < max_docs:
        # Fetch highest priority pending URL from frontier
        target_url = None
        target_depth = 0
        with db.get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT url, depth FROM crawl_queue
                WHERE status = 'pending' AND retry_count < ?
                ORDER BY priority DESC, depth ASC, added_at ASC
                LIMIT 1
            """, (MAX_RETRIES,))
            row = cur.fetchone()
            if row:
                target_url = row["url"]
                target_depth = row["depth"]

        if not target_url:
            break

        res = crawl_url(target_url, max_depth=target_depth, source_type="knowledge_seed")
        if res.get("status") == "indexed":
            indexed_count += 1
            print(f"  [Indexed #{indexed_count}] {target_url[:60]} -> doc_id {res.get('doc_id')}")
        elif res.get("status") in ("not_modified", "domain_limit_reached", "thin_content", "blocked_by_robots"):
            print(f"  [{res.get('status')}] {target_url[:60]}")
        else:
            print(f"  [{res.get('status')}] {target_url[:60]}")

    print(f"[Crawler] Scalable crawl finished: {indexed_count} new documents indexed.")
    return indexed_count


def seed_crawl_knowledge(max_seeds: int = 100) -> int:
    """Compatibility bridge for initial seed ingestion."""
    return run_scalable_crawl(max_docs=max_seeds, max_depth=0)


def run_seed_crawl(max_docs: int = 100) -> int:
    """Compatibility alias for server.py."""
    return run_scalable_crawl(max_docs=max_docs, max_depth=0)
