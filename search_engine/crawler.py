import time
import urllib.parse
import urllib.robotparser
import logging
import requests
from bs4 import BeautifulSoup
from search_engine import db, indexer

logger = logging.getLogger("VASTUDA_Crawler")

ROBOTS_CACHE = {}
USER_AGENT = "VASTUDA-Bot/1.0 (+https://vastuda.internal/bot; bot@vastuda.internal)"


def is_allowed_by_robots(url: str) -> bool:
    """Check if the URL is allowed to be crawled according to robots.txt."""
    try:
        parsed = urllib.parse.urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        if base_url in ROBOTS_CACHE:
            rp = ROBOTS_CACHE[base_url]
        else:
            rp = urllib.robotparser.RobotFileParser()
            robots_url = urllib.parse.urljoin(base_url, "/robots.txt")
            rp.set_url(robots_url)
            try:
                rp.read()
            except Exception:
                # If robots.txt cannot be read or 404s, allow crawling politely
                pass
            ROBOTS_CACHE[base_url] = rp

        return rp.can_fetch(USER_AGENT, url)
    except Exception as e:
        logger.warning(f"Robots.txt check error for {url}: {e}")
        return True


def enqueue_urls(urls, depth: int = 0):
    """Add a list of URLs to the crawl queue."""
    now = int(time.time())
    added = 0
    with db.get_db() as conn:
        cur = conn.cursor()
        for u in urls:
            clean = u.strip()
            if not clean.startswith(("http://", "https://")):
                continue
            # Strip fragments
            clean = urllib.parse.urldefrag(clean)[0]
            try:
                cur.execute("""
                    INSERT OR IGNORE INTO crawl_queue (url, status, depth, added_at)
                    VALUES (?, 'pending', ?, ?)
                """, (clean, depth, now))
                if cur.rowcount > 0:
                    added += 1
            except Exception:
                pass
        conn.commit()
    return added


def crawl_url(target_url: str, max_depth: int = 2) -> dict:
    """
    Fetch, parse, index a single URL and enqueue its outbound links.
    Returns status summary.
    """
    clean_url = urllib.parse.urldefrag(target_url.strip())[0]

    # 1. Robots.txt check
    if not is_allowed_by_robots(clean_url):
        logger.info(f"[Crawler] Blocked by robots.txt: {clean_url}")
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'blocked_robots' WHERE url = ?", (clean_url,))
            conn.commit()
        return {"status": "blocked_by_robots", "url": clean_url}

    # 2. Fetch page
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        resp = requests.get(clean_url, headers=headers, timeout=8, allow_redirects=True)
        if resp.status_code != 200:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = ?, retry_count = retry_count + 1 WHERE url = ?",
                             (f"http_{resp.status_code}", clean_url))
                conn.commit()
            return {"status": f"http_error_{resp.status_code}", "url": clean_url}

        content_type = resp.headers.get("Content-Type", "").lower()
        if "text/html" not in content_type:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'non_html' WHERE url = ?", (clean_url,))
                conn.commit()
            return {"status": "non_html", "url": clean_url}

    except Exception as e:
        logger.warning(f"Error fetching {clean_url}: {e}")
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'fetch_failed', retry_count = retry_count + 1 WHERE url = ?",
                         (clean_url,))
            conn.commit()
        return {"status": "failed", "error": str(e), "url": clean_url}

    # 3. Parse HTML
    try:
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip uninformative elements
        for tag in soup(["script", "style", "nav", "footer", "aside", "noscript", "svg", "iframe"]):
            tag.decompose()

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Extract headings
        headings = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            text = h.get_text(strip=True)
            if text and len(text) > 3:
                headings.append(text)
        headings_str = " | ".join(headings[:10])

        # Extract meta description
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Extract clean body text
        paragraphs = []
        for p in soup.find_all(["p", "li"]):
            p_text = p.get_text(strip=True)
            if len(p_text) > 30:
                paragraphs.append(p_text)
        body_text = " ".join(paragraphs[:30])

        # Canonical URL if specified
        canonical_tag = soup.find("link", rel="canonical")
        canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else clean_url

        # Language
        html_tag = soup.find("html")
        language = (html_tag.get("lang", "en") if html_tag else "en").split("-")[0].lower()

        # 4. Index in FTS5 Search Index
        doc_id = indexer.index_document(
            url=clean_url,
            title=title or clean_url,
            body_text=body_text,
            headings=headings_str,
            meta_desc=meta_desc,
            language=language,
            canonical_url=canonical_url,
            quality_score=1.0
        )

        # 5. Extract links for queue
        now = int(time.time())
        discovered_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            absolute_link = urllib.parse.urljoin(clean_url, href)
            if absolute_link.startswith(("http://", "https://")):
                discovered_links.append(absolute_link)

        # Enqueue discovered links if within depth
        if max_depth > 0 and discovered_links:
            enqueue_urls(discovered_links[:15], depth=max_depth - 1)

        # Mark queue item as completed
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'completed', crawled_at = ? WHERE url = ?",
                         (now, clean_url))
            conn.commit()

        return {
            "status": "indexed",
            "doc_id": doc_id,
            "title": title,
            "url": clean_url,
            "links_discovered": len(discovered_links)
        }

    except Exception as e:
        logger.error(f"Parsing error on {clean_url}: {e}")
        return {"status": "parse_error", "error": str(e), "url": clean_url}


def run_crawl_batch(batch_size: int = 5):
    """Process up to batch_size pending URLs from crawl queue."""
    pending_urls = []
    with db.get_db() as conn:
        cur = conn.cursor()
        cur.execute("SELECT url, depth FROM crawl_queue WHERE status = 'pending' LIMIT ?", (batch_size,))
        rows = cur.fetchall()
        for r in rows:
            pending_urls.append((r["url"], r["depth"]))

    results = []
    for url, depth in pending_urls:
        res = crawl_url(url, max_depth=depth)
        results.append(res)
        time.sleep(0.5)  # Polite crawling delay

    return results
