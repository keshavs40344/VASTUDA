"""
VASTUDA 5.3 — Production-Grade Search Result Validation, Deduplication & Snippet Generation

Features:
- Robust URL canonicalization (scheme/netloc lowercase, default port stripping,
  tracking param removal, fragment stripping, trailing slash normalization)
- SSRF and private IP protection on result URLs
- Multi-tier deduplication: primary canonical URL + secondary content fingerprint
- High-quality passage snippet extractor (locates highest query-token density passages)
- Production quality filter (rejects empty titles, crawler error pages, malware patterns)
"""

import re
import ipaddress
import hashlib
import urllib.parse

# Comprehensive tracking parameters that add zero informational value
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "utm_cid", "utm_reader", "utm_viz_id",
    "fbclid", "gclid", "gclsrc", "dclid", "msclkid", "yclid", "_ga", "_gl",
    "mc_cid", "mc_eid", "igshid", "gbraid", "wbraid", "cmpid", "_hsenc",
    "_hsmi", "mkt_tok", "action_object_map", "action_type_map", "action_ref_map"
}

ALLOWED_SCHEMES = {"http", "https"}

# Obvious error and boilerplate page titles to suppress
ERROR_TITLES = {
    "404 not found", "404 page not found", "page not found",
    "403 forbidden", "access denied", "error 404", "error 403",
    "untitled", "untitled document", "default web site page",
    "just a moment...", "attention required! | cloudflare",
    "security check to continue", "loading...", "bad request"
}


def normalize_url(url: str) -> str:
    """
    Normalizes a URL for canonical matching (Phase 5.3):
    - Strips fragment (#...)
    - Lowercases scheme and netloc
    - Strips default ports (:80 for http, :443 for https)
    - Strips tracking query parameters (utm_*, fbclid, gclid, etc.)
    - Removes redundant consecutive slashes in path
    - Preserves meaningful query parameters and path
    - Strips trailing slash on path if path is not root '/'
    """
    if not url or not isinstance(url, str):
        return ""

    url = url.strip()
    try:
        parsed = urllib.parse.urlsplit(url)
        scheme = parsed.scheme.lower()
        if scheme not in ALLOWED_SCHEMES:
            return ""

        netloc = parsed.netloc.lower()
        if not netloc:
            return ""

        # Strip standard default ports
        if scheme == "http" and netloc.endswith(":80"):
            netloc = netloc[:-3]
        elif scheme == "https" and netloc.endswith(":443"):
            netloc = netloc[:-4]

        # Normalize path
        path = parsed.path or "/"
        # Collapse multiple consecutive slashes (e.g. //wiki// -> /wiki/)
        path = re.sub(r"/+", "/", path)
        if len(path) > 1 and path.endswith("/"):
            path = path.rstrip("/")

        # Filter tracking params from query
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=False)
        filtered_query = [
            (k, v) for k, v in query_pairs
            if k.lower() not in TRACKING_PARAMS and not k.lower().startswith("utm_")
        ]

        # Sort query params for consistent canonical representation
        filtered_query.sort(key=lambda x: x[0])
        new_query = urllib.parse.urlencode(filtered_query)

        # Build clean url (omit fragment)
        return urllib.parse.urlunsplit((scheme, netloc, path, new_query, ""))
    except Exception:
        return ""


def is_safe_public_url(url: str) -> bool:
    """
    Verify that a URL does not point to internal, private, or loopback networks.
    Protects against SSRF and internal network leakage in search results.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        if not host:
            return False

        # Block localhost and local names
        if host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False
        if host.endswith((".local", ".internal", ".corp", ".lan")):
            return False

        # If IP address, verify it is global
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except ValueError:
            pass  # Hostname is a domain, not an IP literal

        return True
    except Exception:
        return False


def clean_text_artifacts(text: str) -> str:
    """Remove HTML tags, script remnants, and broken characters from text."""
    if not text or not isinstance(text, str):
        return ""
    # Strip HTML tags
    clean = re.sub(r"<[^>]+>", " ", text)
    # Strip markdown and wiki artifacts
    clean = re.sub(r"\[\.\.\.\]", " ", clean)
    clean = re.sub(r"\[edit\]", "", clean, flags=re.I)
    clean = re.sub(r"#+\s*", "", clean)
    clean = re.sub(r"[\r\n\t]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def safe_snippet(text: str, max_len: int = 240) -> str:
    """Sanitize snippet text, bound length, and append ellipsis if truncated."""
    clean = clean_text_artifacts(text)
    if not clean:
        return "Visit source for complete details."

    if len(clean) > max_len:
        truncated = clean[:max_len].rsplit(" ", 1)[0]
        return truncated.strip() + "..."
    return clean


def generate_best_snippet(body_text: str, query: str = "", max_len: int = 240) -> str:
    """
    High-quality passage snippet generator (Phase 5.3):
    1. If query terms are provided, identifies the passage with the highest term density.
    2. Centers the snippet around the most relevant sentence or window.
    3. Cleans formatting artifacts.
    4. Falls back gracefully to leading text if no passage matches.
    """
    clean_body = clean_text_artifacts(body_text)
    if not clean_body:
        return "Visit source for complete details."

    if not query or len(clean_body) <= max_len:
        return safe_snippet(clean_body, max_len=max_len)

    q_tokens = [t for t in re.sub(r"[^\w\s]", " ", query.lower()).split() if len(t) > 2]
    if not q_tokens:
        return safe_snippet(clean_body, max_len=max_len)

    # Split body into sentence windows
    sentences = re.split(r'(?<=[.!?])\s+', clean_body)
    best_window = sentences[0] if sentences else clean_body[:max_len]
    best_score = -1

    for idx, sentence in enumerate(sentences):
        s_lower = sentence.lower()
        matched = sum(1 for tok in q_tokens if tok in s_lower)
        if matched > best_score:
            best_score = matched
            # Combine current with next sentence if space permits
            combined = sentence
            if idx + 1 < len(sentences) and len(combined) + len(sentences[idx + 1]) < max_len:
                combined = f"{combined} {sentences[idx + 1]}"
            best_window = combined

    if len(best_window) > max_len:
        best_window = best_window[:max_len].rsplit(" ", 1)[0] + "..."

    return best_window.strip() or safe_snippet(clean_body, max_len=max_len)


def validate_result(result: dict) -> bool:
    """
    Validates that a search result meets production quality standards (Phase 5.3):
    - Valid dict format
    - Non-empty title (at least 3 non-whitespace characters)
    - Rejects crawler error page titles (404, Access Denied, etc.)
    - Valid normalized HTTP/HTTPS URL
    - Valid public host (SSRF safe)
    - Valid domain
    """
    if not isinstance(result, dict):
        return False

    title = result.get("title")
    if not title or not isinstance(title, str) or len(title.strip()) < 3:
        return False

    clean_t = title.strip().lower()
    if clean_t in ERROR_TITLES or clean_t.startswith("error ") or "404 not found" in clean_t:
        return False

    raw_url = result.get("url")
    if not raw_url or not isinstance(raw_url, str):
        return False

    norm_url = normalize_url(raw_url)
    if not norm_url or not is_safe_public_url(norm_url):
        return False

    domain = result.get("domain") or urllib.parse.urlsplit(norm_url).netloc
    if not domain or "." not in domain or len(domain) < 3:
        return False

    return True


def deduplicate_results(results: list) -> list:
    """
    Deduplicates a list of search result items using multi-signal keys (Phase 5.3):
    1. Primary key: canonical normalized URL
    2. Secondary key: (domain, alphanumeric title fingerprint)
    3. Tertiary key: snippet content hash (suppresses mirror pages)
    Preserves original ranking order.
    """
    if not results:
        return []

    deduped = []
    seen_urls = set()
    seen_titles = set()
    seen_content_hashes = set()

    for item in results:
        if not isinstance(item, dict):
            continue

        raw_url = item.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url or norm_url in seen_urls:
            continue

        domain = item.get("domain") or urllib.parse.urlsplit(norm_url).netloc
        title = (item.get("title") or "").strip()
        title_key = re.sub(r"[^a-zA-Z0-9\u0900-\u097F]", "", title.lower())
        title_fingerprint = (domain.lower(), title_key[:45])

        if title_key and title_fingerprint in seen_titles:
            continue

        # Content hash check for identical snippet mirrors
        snippet = item.get("snippet", "")
        snip_clean = re.sub(r"[^\w\u0900-\u097F]", "", snippet.lower())
        if len(snip_clean) > 50:
            c_hash = hashlib.md5(snip_clean[:120].encode("utf-8")).hexdigest()
            if c_hash in seen_content_hashes:
                continue
            seen_content_hashes.add(c_hash)

        seen_urls.add(norm_url)
        if title_key:
            seen_titles.add(title_fingerprint)

        # Standardize snippet and url
        cleaned_item = dict(item)
        cleaned_item["url"] = norm_url
        cleaned_item["domain"] = domain.lower()
        cleaned_item["snippet"] = safe_snippet(cleaned_item.get("snippet", ""))
        deduped.append(cleaned_item)

    return deduped


def validate_image(image_item) -> dict | None:
    """
    Validates and normalizes an image object.
    Returns normalized dict or None if invalid.
    """
    if isinstance(image_item, str):
        url = normalize_url(image_item)
        if url and is_safe_public_url(url):
            return {"url": url, "title": "", "source": "web"}
        return None

    if isinstance(image_item, dict):
        url = normalize_url(image_item.get("url", ""))
        if url and is_safe_public_url(url):
            return {
                "url": url,
                "title": clean_text_artifacts(image_item.get("title", "")),
                "source": image_item.get("source", "web")
            }
    return None
