import re
import urllib.parse

# Recognized tracking parameters that provide zero user/content value
TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "fbclid", "gclid", "gclsrc", "dclid",
    "msclkid", "yclid", "_ga", "_gl", "mc_cid", "mc_eid"
}

ALLOWED_SCHEMES = {"http", "https"}


def normalize_url(url: str) -> str:
    """
    Normalizes a URL for canonical matching:
    - Strips fragment (#...)
    - Lowercases scheme and netloc
    - Strips tracking query parameters (utm_*, fbclid, gclid, etc.)
    - Preserves meaningful query parameters and path
    - Strips trailing slash on path if path is not empty
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

        # Normalize path
        path = parsed.path
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


def safe_snippet(text: str, max_len: int = 240) -> str:
    """Sanitize snippet text, remove markdown headers/artifacts, and bound length."""
    if not text or not isinstance(text, str):
        return "Visit source for complete details."
    
    clean = re.sub(r"\[\.\.\.\]", " ", text)
    clean = re.sub(r"\[edit\]", "", clean, flags=re.I)
    clean = re.sub(r"#+\s*", "", clean)
    clean = re.sub(r"[\r\n\t]+", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    
    if len(clean) > max_len:
        truncated = clean[:max_len].rsplit(" ", 1)[0]
        return truncated.strip() + "..."
    return clean or "Visit source for complete details."


def validate_result(result: dict) -> bool:
    """
    Validates that a result dictionary meets production quality standards:
    - Has valid dict format
    - Non-empty title (at least 2 non-whitespace characters)
    - Valid, normalized URL using http or https
    - Valid domain
    """
    if not isinstance(result, dict):
        return False

    title = result.get("title")
    if not title or not isinstance(title, str) or len(title.strip()) < 2:
        return False

    raw_url = result.get("url")
    if not raw_url or not isinstance(raw_url, str):
        return False

    norm_url = normalize_url(raw_url)
    if not norm_url:
        return False

    domain = result.get("domain") or urllib.parse.urlsplit(norm_url).netloc
    if not domain or "." not in domain or len(domain) < 3:
        return False

    return True


def deduplicate_results(results: list) -> list:
    """
    Deduplicates a list of search result items using:
    1. Primary key: canonical normalized URL
    2. Secondary key: (normalized domain, normalized alphanumeric title)
    Preserves original ranking order.
    """
    if not results:
        return []

    deduped = []
    seen_urls = set()
    seen_content = set()

    for item in results:
        if not isinstance(item, dict):
            continue

        raw_url = item.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url or norm_url in seen_urls:
            continue

        # Secondary dedup key: domain + simplified title
        domain = item.get("domain") or urllib.parse.urlsplit(norm_url).netloc
        title = item.get("title", "")
        title_key = re.sub(r"[^a-zA-Z0-9]", "", title.lower())
        content_key = (domain.lower(), title_key[:50])

        if title_key and content_key in seen_content:
            continue

        seen_urls.add(norm_url)
        if title_key:
            seen_content.add(content_key)

        # Standardize snippet and url
        cleaned_item = dict(item)
        cleaned_item["url"] = norm_url
        cleaned_item["domain"] = domain.lower()
        cleaned_item["snippet"] = safe_snippet(cleaned_item.get("snippet", ""))
        deduped.append(cleaned_item)

    return deduped


def validate_image(image_item) -> dict:
    """
    Validates and normalizes an image object.
    Returns normalized dict or None if invalid.
    """
    if isinstance(image_item, str):
        url = normalize_url(image_item)
        if url:
            return {"url": url, "title": "", "source": "web"}
        return None

    if isinstance(image_item, dict):
        raw_url = image_item.get("url")
        url = normalize_url(raw_url)
        if not url:
            return None
        title = str(image_item.get("title") or "").strip()
        source = str(image_item.get("source") or "web").strip()
        return {"url": url, "title": title, "source": source}

    return None
