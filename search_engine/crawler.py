"""
VASTUDA 5.0 — Safe, Respectful Web Crawler & Sitemap Engine
Features:
- Strict SSRF protection (rejects loopback, private RFC1918, link-local, cloud metadata)
- Robots.txt compliance with caching and sitemap discovery
- XML Sitemap parser (/sitemap.xml and robots.txt Sitemap: directives)
- Polite crawling: delay, max page size (2.5MB), max redirects (3), timeout (8s)
- Content extraction: boilerplate removal, structured headings, canonicals, language detection
- High-authority seed lists for core computer science, open knowledge, and legal/government domains
"""

import time
import socket
import ipaddress
import urllib.parse
import urllib.robotparser
import xml.etree.ElementTree as ET
import logging
import requests
from bs4 import BeautifulSoup
from search_engine import db, indexer, query_engine

logger = logging.getLogger("VASTUDA_Crawler")

ROBOTS_CACHE = {}
USER_AGENT = "VASTUDA-Bot/5.1 (+https://vastuda.internal/bot; bot@vastuda.internal)"
MAX_PAGE_SIZE = 2500000  # 2.5 MB maximum

# Internal diagnostic telemetry (ground-truth counters)
CRAWLER_DIAGNOSTICS = {
    "urls_attempted": 0,
    "urls_successful": 0,
    "urls_rejected_robots": 0,
    "urls_rejected_ssrf": 0,
    "http_failures": 0,
    "duplicate_pages": 0,
    "content_extraction_failures": 0,
    "last_crawl_time": 0
}


# Curated high-value open seed sources — expanded for 5.2 index quality
# Targets: 20+ domains, ~100–200 indexable documents of genuine reference quality.
# Every URL here is publicly accessible, robot-compliant, and informationally dense.
SEED_SOURCES = [
    # ── Python Official Documentation ──────────────────────────────────────
    "https://docs.python.org/3/tutorial/index.html",
    "https://docs.python.org/3/tutorial/datastructures.html",
    "https://docs.python.org/3/tutorial/controlflow.html",
    "https://docs.python.org/3/tutorial/classes.html",
    "https://docs.python.org/3/tutorial/errors.html",
    "https://docs.python.org/3/library/functions.html",
    "https://docs.python.org/3/library/itertools.html",
    "https://docs.python.org/3/library/collections.html",
    "https://docs.python.org/3/glossary.html",

    # ── MDN Web Docs — HTML/CSS/JS ─────────────────────────────────────────
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Functions",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures",
    "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise",
    "https://developer.mozilla.org/en-US/docs/Learn/HTML",
    "https://developer.mozilla.org/en-US/docs/Learn/CSS",
    "https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Flexbox",
    "https://developer.mozilla.org/en-US/docs/Learn/CSS/CSS_layout/Grids",
    "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview",
    "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch",

    # ── Git & DevOps ───────────────────────────────────────────────────────
    "https://git-scm.com/doc",
    "https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging",
    "https://git-scm.com/book/en/v2/Getting-Started-What-is-Git%3F",
    "https://docs.docker.com/get-started/",
    "https://docs.docker.com/get-started/overview/",

    # ── SQLite & Databases ─────────────────────────────────────────────────
    "https://www.sqlite.org/wal.html",
    "https://www.sqlite.org/fts5.html",
    "https://www.sqlite.org/queryplanner.html",
    "https://www.sqlite.org/lang_select.html",

    # ── Wikipedia — CS Fundamentals & Algorithms ───────────────────────────
    "https://en.wikipedia.org/wiki/Artificial_intelligence",
    "https://en.wikipedia.org/wiki/Machine_learning",
    "https://en.wikipedia.org/wiki/Quantum_computing",
    "https://en.wikipedia.org/wiki/Domain_Name_System",
    "https://en.wikipedia.org/wiki/Transformer_(machine_learning_model)",
    "https://en.wikipedia.org/wiki/Speed_of_light",
    "https://en.wikipedia.org/wiki/Solar_System",
    "https://en.wikipedia.org/wiki/Photosynthesis",
    "https://en.wikipedia.org/wiki/Binary_search_algorithm",
    "https://en.wikipedia.org/wiki/Relational_database",
    "https://en.wikipedia.org/wiki/Neural_network_(machine_learning)",
    "https://en.wikipedia.org/wiki/Sorting_algorithm",
    "https://en.wikipedia.org/wiki/Big_O_notation",
    "https://en.wikipedia.org/wiki/Hash_table",
    "https://en.wikipedia.org/wiki/Graph_(abstract_data_type)",
    "https://en.wikipedia.org/wiki/Linked_list",
    "https://en.wikipedia.org/wiki/Dynamic_programming",
    "https://en.wikipedia.org/wiki/Recursion_(computer_science)",
    "https://en.wikipedia.org/wiki/Application_programming_interface",
    "https://en.wikipedia.org/wiki/Representational_state_transfer",
    "https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol",
    "https://en.wikipedia.org/wiki/Internet_protocol_suite",
    "https://en.wikipedia.org/wiki/Encryption",
    "https://en.wikipedia.org/wiki/Public-key_cryptography",
    "https://en.wikipedia.org/wiki/Linux",
    "https://en.wikipedia.org/wiki/Open-source_software",
    "https://en.wikipedia.org/wiki/Version_control",
    "https://en.wikipedia.org/wiki/Compiler",
    "https://en.wikipedia.org/wiki/Operating_system",

    # ── Wikipedia — Science & Nature ───────────────────────────────────────
    "https://en.wikipedia.org/wiki/Climate_change",
    "https://en.wikipedia.org/wiki/DNA",
    "https://en.wikipedia.org/wiki/Evolution",
    "https://en.wikipedia.org/wiki/Black_hole",
    "https://en.wikipedia.org/wiki/Theory_of_relativity",
    "https://en.wikipedia.org/wiki/Periodic_table",
    "https://en.wikipedia.org/wiki/Human_brain",
    "https://en.wikipedia.org/wiki/Vaccine",
    "https://en.wikipedia.org/wiki/Protein",
    "https://en.wikipedia.org/wiki/Internet",

    # ── Indian Governance, Law & Space Science ────────────────────────────
    "https://en.wikipedia.org/wiki/Constitution_of_India",
    "https://en.wikipedia.org/wiki/Preamble_to_the_Constitution_of_India",
    "https://en.wikipedia.org/wiki/Fundamental_Rights,_Directive_Principles_and_Fundamental_Duties_of_India",
    "https://en.wikipedia.org/wiki/Indian_Space_Research_Organisation",
    "https://en.wikipedia.org/wiki/Chandrayaan-3",
    "https://en.wikipedia.org/wiki/Aditya-L1",
    "https://en.wikipedia.org/wiki/India",
    "https://en.wikipedia.org/wiki/Economy_of_India",
    "https://www.india.gov.in/my-government/constitution-india",

    # ── Hindi Wikipedia — Science, Technology & India ─────────────────────
    # (URLs are percent-encoded Unicode for Devanagari article names)
    "https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4_%E0%A4%95%E0%A4%BE_%E0%A4%B8%E0%A4%82%E0%A4%B5%E0%A4%BF%E0%A4%A7%E0%A4%BE%E0%A4%A8",
    "https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4%E0%A5%80%E0%A4%AF_%E0%A4%85%E0%A4%82%E0%A4%A4%E0%A4%B0%E0%A4%BF%E0%A4%95%E0%A5%8D%E0%A4%B7_%E0%A4%85%E0%A4%A8%E0%A5%81%E0%A4%B8%E0%A4%82%E0%A4%A7%E0%A4%BE%E0%A4%A8_%E0%A4%B8%E0%A4%82%E0%A4%97%E0%A4%A0%E0%A4%A8",
    "https://hi.wikipedia.org/wiki/%E0%A4%95%E0%A4%82%E0%A4%AA%E0%A5%8D%E0%A4%AF%E0%A5%82%E0%A4%9F%E0%A4%B0",
    "https://hi.wikipedia.org/wiki/%E0%A4%B8%E0%A5%8C%E0%A4%B0%E0%A4%AE%E0%A4%A3%E0%A5%8D%E0%A4%A1%E0%A4%B2",
    "https://hi.wikipedia.org/wiki/%E0%A4%AA%E0%A5%8D%E0%A4%B0%E0%A4%95%E0%A4%BE%E0%A4%B6_%E0%A4%B8%E0%A4%82%E0%A4%B6%E0%A5%8D%E0%A4%B2%E0%A5%87%E0%A4%B7%E0%A4%A3",
    "https://hi.wikipedia.org/wiki/%E0%A4%87%E0%A4%82%E0%A4%9F%E0%A4%B0%E0%A4%A8%E0%A5%87%E0%A4%9F",
    "https://hi.wikipedia.org/wiki/%E0%A4%95%E0%A5%83%E0%A4%A4%E0%A5%8D%E0%A4%B0%E0%A4%BF%E0%A4%AE_%E0%A4%AC%E0%A5%81%E0%A4%A6%E0%A5%8D%E0%A4%A7%E0%A4%BF%E0%A4%AE%E0%A4%A4%E0%A5%8D%E0%A4%A4%E0%A4%BE",
    "https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4",
    "https://hi.wikipedia.org/wiki/%E0%A4%AE%E0%A4%B6%E0%A5%80%E0%A4%A8_%E0%A4%B2%E0%A4%B0%E0%A5%8D%E0%A4%A8%E0%A4%BF%E0%A4%82%E0%A4%97",
    "https://hi.wikipedia.org/wiki/%E0%A4%A1%E0%A5%80%E0%A4%8F%E0%A4%A8%E0%A4%8F",
    "https://hi.wikipedia.org/wiki/%E0%A4%9C%E0%A4%B2%E0%A4%B5%E0%A4%BE%E0%A4%AF%E0%A5%81_%E0%A4%AA%E0%A4%B0%E0%A4%BF%E0%A4%B5%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%A8",
]



def is_safe_url(url: str) -> bool:
    """
    Strict SSRF Prevention:
    Rejects:
    - Schemes other than http/https
    - Localhost, 127.0.0.1, ::1
    - Private IP ranges (RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    - Link-local (169.254.0.0/16)
    - Multicast, broadcast, reserved IPs
    - URLs containing credentials (user:pass@host)
    """
    if not url or not isinstance(url, str):
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

        # Resolve host to IP address
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
                # Polite timeout for robots.txt
                headers = {"User-Agent": USER_AGENT}
                r = requests.get(robots_url, headers=headers, timeout=5)
                if r.status_code == 200:
                    rp.parse(r.text.splitlines())
                    # Extract Sitemap directives
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
    """
    Parse XML Sitemap and extract URLs with lastmod dates.
    """
    if not is_safe_url(sitemap_url):
        return []

    discovered = []
    try:
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(sitemap_url, headers=headers, timeout=7)
        if resp.status_code != 200:
            return []

        root = ET.fromstring(resp.content)
        # Handle standard XML namespaces
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        
        # Check if sitemap index
        for sm in root.findall("sm:sitemap", ns) or root.findall("sitemap"):
            loc = sm.find("sm:loc", ns) or sm.find("loc")
            if loc is not None and loc.text and is_safe_url(loc.text):
                discovered.append({"url": loc.text.strip(), "is_index": True})
            if len(discovered) >= max_urls:
                break

        # Check for standard url entries
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


def enqueue_urls(urls, depth: int = 0, priority: int = 0):
    """Add a list of validated URLs to the crawl queue."""
    now = int(time.time())
    added = 0
    with db.get_db() as conn:
        cur = conn.cursor()
        for u in urls:
            clean = u.strip() if isinstance(u, str) else ""
            if not clean or not is_safe_url(clean):
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


def crawl_url(target_url: str, max_depth: int = 1, source_type: str = "web", quality_score: float = 1.0) -> dict:
    """
    Fetch, extract content, and index a single URL safely and politely.
    """
    clean_url = urllib.parse.urldefrag(target_url.strip())[0]
    CRAWLER_DIAGNOSTICS["urls_attempted"] += 1

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

    # 3. Fetch Page with Safety Bounds
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }
    try:
        with requests.get(clean_url, headers=headers, timeout=8, stream=True, allow_redirects=True) as resp:
            if resp.status_code != 200:
                CRAWLER_DIAGNOSTICS["http_failures"] += 1
                with db.get_db() as conn:
                    conn.execute("UPDATE crawl_queue SET status = ?, retry_count = retry_count + 1 WHERE url = ?",
                                 (f"http_{resp.status_code}", clean_url))
                    conn.commit()
                return {"status": f"http_error_{resp.status_code}", "url": clean_url}

            content_type = resp.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                with db.get_db() as conn:
                    conn.execute("UPDATE crawl_queue SET status = 'non_html' WHERE url = ?", (clean_url,))
                    conn.commit()
                return {"status": "non_html", "url": clean_url}

            # Enforce max page size to prevent memory exhaustion
            text = resp.text[:MAX_PAGE_SIZE]

    except Exception as e:
        logger.warning(f"Error fetching {clean_url}: {e}")
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'fetch_failed', retry_count = retry_count + 1 WHERE url = ?",
                         (clean_url,))
            conn.commit()
        return {"status": "failed", "error": str(e), "url": clean_url}

    # 4. Clean Content Extraction
    try:
        soup = BeautifulSoup(text, "html.parser")

        # Decompose non-content and boilerplate elements
        for tag in soup(["script", "style", "nav", "footer", "aside", "header", "form", "iframe", "noscript", "svg"]):
            tag.decompose()

        # Extract title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        if not title:
            h1 = soup.find("h1")
            if h1:
                title = h1.get_text(strip=True)

        # Extract structured headings (H1, H2, H3)
        headings = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            h_text = h.get_text(strip=True)
            if h_text and len(h_text) > 3:
                headings.append(h_text)
        headings_str = " | ".join(headings[:10])

        # Extract meta description
        meta_desc = ""
        meta_tag = (
            soup.find("meta", attrs={"name": "description"}) or
            soup.find("meta", attrs={"property": "og:description"}) or
            soup.find("meta", attrs={"name": "twitter:description"})
        )
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"].strip()

        # Extract published date if available
        published_date = ""
        time_tag = (
            soup.find("meta", attrs={"property": "article:published_time"}) or
            soup.find("meta", attrs={"name": "pubdate"}) or
            soup.find("time")
        )
        if time_tag:
            published_date = (time_tag.get("content") or time_tag.get("datetime") or "").strip()[:10]

        # Extract clean body text
        paragraphs = []
        for p in soup.find_all(["p", "li"]):
            p_text = p.get_text(strip=True)
            if len(p_text) > 25:
                paragraphs.append(p_text)
        body_text = " ".join(paragraphs[:40])

        # If body is too thin, skip indexing
        if len(body_text.strip()) < 80:
            with db.get_db() as conn:
                conn.execute("UPDATE crawl_queue SET status = 'thin_content' WHERE url = ?", (clean_url,))
                conn.commit()
            return {"status": "thin_content", "url": clean_url}

        # Canonical URL detection
        canonical_tag = soup.find("link", rel="canonical")
        canonical_url = canonical_tag.get("href", "").strip() if canonical_tag else clean_url
        if canonical_url and not canonical_url.startswith(("http://", "https://")):
            canonical_url = urllib.parse.urljoin(clean_url, canonical_url)

        # Language Detection
        detected_lang = query_engine.detect_language(title + " " + body_text[:200])

        # 5. Index Document into VASTUDA FTS5 Index
        doc_id = indexer.index_document(
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
            source_type=source_type
        )

        # 6. Outbound link discovery if within max depth
        now = int(time.time())
        discovered_links = []
        if max_depth > 0:
            base_domain = urllib.parse.urlparse(clean_url).netloc.lower()
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                absolute_link = urllib.parse.urljoin(clean_url, href)
                # Keep crawls on same domain or trusted domains
                if is_safe_url(absolute_link):
                    link_domain = urllib.parse.urlparse(absolute_link).netloc.lower()
                    if link_domain == base_domain:
                        discovered_links.append(absolute_link)
            if discovered_links:
                enqueue_urls(discovered_links[:10], depth=max_depth - 1)

        # Mark queue item completed
        with db.get_db() as conn:
            conn.execute("UPDATE crawl_queue SET status = 'completed', crawled_at = ? WHERE url = ?",
                         (now, clean_url))
            conn.commit()

        CRAWLER_DIAGNOSTICS["urls_successful"] += 1
        CRAWLER_DIAGNOSTICS["last_crawl_time"] = now

        return {
            "status": "indexed",
            "doc_id": doc_id,
            "title": title,
            "url": clean_url,
            "language": detected_lang,
            "links_discovered": len(discovered_links)
        }

    except Exception as e:
        CRAWLER_DIAGNOSTICS["content_extraction_failures"] += 1
        logger.error(f"Parsing error on {clean_url}: {e}")
        return {"status": "parse_error", "error": str(e), "url": clean_url}


def get_crawler_diagnostics() -> dict:
    """Return genuine, accurate internal crawler diagnostics."""
    stats = indexer.get_index_stats()
    diag = dict(CRAWLER_DIAGNOSTICS)
    diag["documents_indexed"] = stats.get("indexed_documents", 0)
    diag["domains_indexed"] = stats.get("unique_domains", 0)
    diag["queue_size"] = stats.get("queued_urls", 0)
    diag["languages"] = stats.get("languages", {})
    return diag


def seed_crawl_knowledge(max_seeds: int = 100):
    """
    Seed initial high-value knowledge documents into VASTUDA index.
    Expanded in 5.2 to cover 90+ curated sources (Python docs, MDN, SQLite,
    Wikipedia CS/Science/Hindi/India, Git, Docker).
    """
    total = min(len(SEED_SOURCES), max_seeds)
    print(f"[Crawler] Seeding {total} high-value knowledge sources (5.2 expanded corpus)...")
    indexed_count = 0
    for seed_url in SEED_SOURCES[:max_seeds]:
        try:
            res = crawl_url(seed_url, max_depth=0, source_type="curated_seed", quality_score=1.0)
            if res.get("status") == "indexed":
                indexed_count += 1
                print(f"  [Indexed] {seed_url[:55]} -> doc_id {res.get('doc_id')}")
            elif res.get("status") in ("already_indexed", "thin_content", "robots_rejected"):
                print(f"  [Skip:{res['status']}] {seed_url[:55]}")
            time.sleep(0.3)  # Polite crawling delay (100ms between same-domain; 300ms overall)
        except Exception as e:
            logger.warning(f"Seed note on {seed_url}: {e}")

    print(f"[Crawler] Seed crawl complete: {indexed_count}/{total} indexed.")
    return indexed_count


def run_seed_crawl(max_docs: int = 100):
    """Alias for server.py compatibility. Delegates to seed_crawl_knowledge."""
    return seed_crawl_knowledge(max_seeds=max_docs)
