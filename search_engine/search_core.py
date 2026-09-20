import os
import re
import json
import time
import logging
import urllib.parse
import concurrent.futures
import requests
from dotenv import load_dotenv

try:
    from search_engine import indexer
    from search_engine import query_engine
    from search_engine.search_validator import (
        normalize_url, validate_result, deduplicate_results, validate_image, safe_snippet
    )
except ImportError:
    import indexer
    import query_engine
    from search_validator import (
        normalize_url, validate_result, deduplicate_results, validate_image, safe_snippet
    )

load_dotenv()
logger = logging.getLogger("SearchCore")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"

# High-speed connection pool
http_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=0)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# Strict per-request socket timeouts (in seconds, Phase 5.3: connect 1.0s, read 2.5s)
TAVILY_TIMEOUT = (1.0, 2.5)   # (connect 1.0s, read 2.5s) -> total 3.5s
DDG_TIMEOUT = (0.8, 1.2)      # (connect 0.8s, read 1.2s)
WIKI_TIMEOUT = (1.0, 2.0)     # (connect 1.0s, read 2.0s)

# Persistent non-blocking thread pool for concurrent provider execution
ASYNC_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=16)

# Category cache
CATEGORY_CACHE = {}
CACHE_TTL = 900       # 15 mins default
NEWS_CACHE_TTL = 300  # 5 mins for news


def get_cached(key):
    if key in CATEGORY_CACHE:
        ts, data, ttl = CATEGORY_CACHE[key]
        if time.time() - ts < ttl:
            return data
    return None


def set_cached(key, data, ttl=CACHE_TTL):
    CATEGORY_CACHE[key] = (time.time(), data, ttl)


# --- 1. Base Search Providers ---

def search_tavily_raw(query, search_depth="basic", max_results=8, topic="general", include_images=True, time_range=None):
    """Query Tavily Search API with strict per-request timeout and safe failure logging."""
    if not TAVILY_API_KEY:
        return None

    t0 = time.time()
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": search_depth,
            "topic": topic,
            "max_results": max_results,
            "include_images": include_images,
            "include_answer": False
        }
        if time_range in ["day", "week", "month", "year"]:
            payload["time_range"] = time_range

        resp = http_session.post(url, json=payload, timeout=TAVILY_TIMEOUT)
        elapsed_ms = round((time.time() - t0) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("results", []):
                raw_url = item.get("url", "")
                norm_url = normalize_url(raw_url)
                if not norm_url:
                    continue

                domain = urllib.parse.urlsplit(norm_url).netloc
                res_dict = {
                    "title": (item.get("title") or "").strip(),
                    "url": norm_url,
                    "domain": domain,
                    "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
                    "snippet": safe_snippet(item.get("content", "")),
                    "score": item.get("score", 1.0),
                    "published_date": item.get("published_date", "")
                }
                if validate_result(res_dict):
                    results.append(res_dict)

            images = []
            for img in data.get("images", []):
                valid_img = validate_image(img)
                if valid_img:
                    images.append(valid_img)

            return {"results": results, "images": images, "provider": "tavily"}
        else:
            # Safe structured logging: Never log API key or headers with auth tokens
            safe_hdrs = {
                k: v for k, v in resp.headers.items()
                if k.lower() in ("content-type", "server", "cf-ray", "date", "cf-cache-status")
            }
            category = "CLOUDFLARE_530" if resp.status_code == 530 else (
                "RATE_LIMITED_429" if resp.status_code == 429 else f"UPSTREAM_HTTP_{resp.status_code}"
            )
            logger.warning(
                f"[PROVIDER_FAIL] provider=Tavily status={resp.status_code} elapsed={elapsed_ms}ms "
                f"category={category} safe_headers={safe_hdrs}"
            )
            return None
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.time() - t0) * 1000)
        logger.warning(f"[PROVIDER_FAIL] provider=Tavily status=TIMEOUT elapsed={elapsed_ms}ms category=TIMEOUT")
        return None
    except requests.exceptions.RequestException as e:
        elapsed_ms = round((time.time() - t0) * 1000)
        logger.warning(f"[PROVIDER_FAIL] provider=Tavily status=NETWORK_ERROR elapsed={elapsed_ms}ms error={type(e).__name__}")
        return None
    except Exception as e:
        logger.error(f"[PROVIDER_FAIL] provider=Tavily unexpected error: {type(e).__name__}")
        return None


def search_duckduckgo_raw(query, max_results=10, time_range=None):
    """Fallback search using DuckDuckGo HTML scraping with pooled session and timeout."""
    t0 = time.time()
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"
        }
        url = "https://html.duckduckgo.com/html/"
        post_data = {"q": query}
        df_map = {"day": "d", "week": "w", "month": "m", "year": "y"}
        if time_range in df_map:
            post_data["df"] = df_map[time_range]

        resp = http_session.post(url, data=post_data, headers=headers, timeout=DDG_TIMEOUT)
        elapsed_ms = round((time.time() - t0) * 1000)

        if resp.status_code != 200:
            logger.warning(f"[PROVIDER_FAIL] provider=DuckDuckGo status={resp.status_code} elapsed={elapsed_ms}ms")
            return {"results": [], "images": [], "provider": "failed"}

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        raw_results = soup.select(".result")

        results = []
        for r in raw_results[:max_results]:
            title_elem = r.select_one(".result__title a")
            snippet_elem = r.select_one(".result__snippet")
            if not title_elem:
                continue

            raw_href = title_elem.get("href", "")
            target_url = raw_href
            if "uddg=" in raw_href:
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                if "uddg" in parsed:
                    target_url = parsed["uddg"][0]

            norm_url = normalize_url(target_url)
            if not norm_url:
                continue

            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            domain = urllib.parse.urlsplit(norm_url).netloc

            res_dict = {
                "title": title,
                "url": norm_url,
                "domain": domain,
                "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
                "snippet": safe_snippet(snippet),
                "score": 1.0,
                "published_date": ""
            }
            if validate_result(res_dict):
                results.append(res_dict)

        return {"results": results, "images": [], "provider": "duckduckgo"}
    except requests.exceptions.Timeout:
        elapsed_ms = round((time.time() - t0) * 1000)
        logger.warning(f"[PROVIDER_FAIL] provider=DuckDuckGo status=TIMEOUT elapsed={elapsed_ms}ms")
        return {"results": [], "images": [], "provider": "timeout"}
    except Exception as e:
        elapsed_ms = round((time.time() - t0) * 1000)
        logger.warning(f"[PROVIDER_FAIL] provider=DuckDuckGo error={type(e).__name__} elapsed={elapsed_ms}ms")
        return {"results": [], "images": [], "provider": "failed"}


def search_wikipedia_fallback(query, max_results=6):
    """Zero-auth fallback search using Wikipedia API when commercial providers fail or bot-check."""
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(query)}&format=json&srlimit={max_results}"
        resp = http_session.get(url, headers={"User-Agent": "VASTUDA-SearchEngine/1.0"}, timeout=(2.0, 3.0))
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("query", {}).get("search", []):
                title = (item.get("title") or "").strip()
                page_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                clean_snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
                res_dict = {
                    "title": title,
                    "url": page_url,
                    "domain": "en.wikipedia.org",
                    "favicon": "https://www.google.com/s2/favicons?domain=en.wikipedia.org&sz=64",
                    "snippet": safe_snippet(clean_snippet),
                    "score": 0.9,
                    "published_date": "Wikipedia"
                }
                if validate_result(res_dict):
                    results.append(res_dict)
            return {"results": results, "images": [], "provider": "wikipedia_knowledge"}
    except Exception as e:
        logger.warning(f"Wikipedia fallback error: {type(e).__name__}")
    return {"results": [], "images": [], "provider": "failed"}


def execute_web_query(query, max_results=8, topic="general", include_images=True, time_range=None):
    """
    Execute multi-provider search with independent bounded non-blocking execution:
    - Runs Tavily and DuckDuckGo concurrently using persistent thread pool
    - Collects available results within 3.5s deadline
    - Discards incomplete providers without hanging
    - Guarantees partial results if at least one provider succeeds
    - Automatically falls back to Wikipedia knowledge index if commercial providers fail
    """
    q_lower = query.lower()
    if any(k in q_lower for k in ["news", "today", "latest", "breaking", "update", "headline"]):
        topic = "news"

    tav_results = []
    tav_images = []
    ddg_results = []

    tav_future = ASYNC_POOL.submit(
        search_tavily_raw, query, "basic", max_results, topic, include_images, time_range
    )
    ddg_future = ASYNC_POOL.submit(
        search_duckduckgo_raw, query, max_results, time_range
    )

    # High-speed bounded wait: return as soon as first provider completes with results.
    # Primary wait: 1.2s (Tavily typically responds in 800–1100ms; DDG cut to 1.2s max)
    done, not_done = concurrent.futures.wait(
        [tav_future, ddg_future],
        timeout=1.2,
        return_when=concurrent.futures.FIRST_COMPLETED
    )
    for f in done:
        try:
            res = f.result(timeout=0.05)
            if res and res.get("results"):
                if res.get("provider") == "tavily":
                    tav_results = res.get("results", [])
                    tav_images = res.get("images", [])
                elif res.get("provider") == "duckduckgo":
                    ddg_results = res.get("results", [])
        except Exception:
            pass

    # Backup: if primary returned < 4 results and other is pending, wait briefly
    # 0.3s — enough for a fast Tavily response; not enough to allow DDG to drag us
    if (len(tav_results) + len(ddg_results)) < 4 and not_done:
        done_rest, _ = concurrent.futures.wait(not_done, timeout=0.3)
        for f in done_rest:
            try:
                res = f.result(timeout=0.05)
                if res and res.get("results"):
                    if res.get("provider") == "tavily":
                        tav_results = res.get("results", [])
                        tav_images = res.get("images", [])
                    elif res.get("provider") == "duckduckgo":
                        ddg_results = res.get("results", [])
            except Exception:
                pass

    # Combine available results and deduplicate
    combined = tav_results + ddg_results
    deduped = deduplicate_results(combined)[:max_results]

    active_provider = "none"
    if tav_results and ddg_results:
        active_provider = "multi_provider"
    elif tav_results:
        active_provider = "tavily"
    elif ddg_results:
        active_provider = "duckduckgo"
    else:
        # Zero-auth resilient fallback: Wikipedia API
        wiki_fallback = search_wikipedia_fallback(query, max_results=max_results)
        if wiki_fallback.get("results"):
            deduped = wiki_fallback.get("results", [])
            active_provider = "wikipedia_fallback"

    return {
        "results": deduped,
        "images": tav_images,
        "provider": active_provider
    }


# --- 2. Groq AI Synthesis ---

def call_groq(prompt, system_prompt="You are VASTUDA's elite AI engine. Be concise, direct, accurate.", max_tokens=600, json_output=False):
    """Invoke Groq LLM with persistent session."""
    if not GROQ_API_KEY:
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens
        }
        if json_output:
            payload["response_format"] = {"type": "json_object"}

        resp = http_session.post(url, headers=headers, json=payload, timeout=12)
        if resp.status_code == 200:
            return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    except Exception as e:
        logger.error(f"Groq invocation error: {e}")
    return None


# --- 3. Specialized Category Handlers ---

# Helper: Fetch public domain high-res images from Wikipedia / Wikimedia Commons
def fetch_wikimedia_images(query, limit=8):
    images = []
    try:
        # Direct generator search on Wikipedia for related high-res images
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&generator=search&gsrsearch={urllib.parse.quote(query)}&gsrlimit={limit}&prop=pageimages&pithumbsize=800&piprop=thumbnail|original&format=json"
        resp = http_session.get(search_url, headers={"User-Agent": "VASTUDA/1.0"}, timeout=3)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for p in pages.values():
                thumb = p.get("thumbnail", {}).get("source") or p.get("original", {}).get("source")
                if thumb and not thumb.endswith(".svg.png"):
                    images.append({"url": thumb, "title": p.get("title", query), "source": "wikimedia"})
    except Exception as e:
        logger.warning(f"Wikimedia image search error: {e}")
    return images


# CATEGORY: AI Search (Ultra-Concise, Controlled Reasoning)
def search_ai_mode(query):
    cached = get_cached(f"ai:{query.lower()}")
    if cached:
        return cached

    web_data = execute_web_query(query, max_results=5)
    results = web_data.get("results", [])

    context = "\n\n".join([f"[{i+1}] {r['title']} ({r['url']}):\n{r['snippet']}" for i, r in enumerate(results[:4])])
    prompt = f"""Search Query: "{query}"

Web Context:
{context}

Provide an ultra-concise, high-impact synthesis:
1. Direct Answer: A crisp 2-sentence summary answering the query directly.
2. Key Points: At most 3 short bullet points (maximum 1 sentence each).
3. Do NOT write long paragraphs, do NOT over-explain. Be sharp and direct.
4. Cite sources using [1], [2]."""

    ai_text = call_groq(
        prompt,
        system_prompt="You are VASTUDA AI. Give ultra-concise, sharp, and factual answers without fluff.",
        max_tokens=220
    )

    payload = {
        "category": "ai",
        "query": query,
        "overview": ai_text or "AI synthesis temporarily unavailable.",
        "sources": [{"index": i + 1, "title": r["title"], "url": r["url"], "domain": r["domain"]} for i, r in enumerate(results[:4])],
        "results": results,
        "provider": web_data.get("provider", "groq")
    }
    set_cached(f"ai:{query.lower()}", payload)
    return payload


# CATEGORY: Research Search (Academic Consensus, Controlled & Focused)
def search_research_mode(query):
    cached = get_cached(f"research:{query.lower()}")
    if cached:
        return cached

    academic_query = f"{query} research"
    web_data = execute_web_query(academic_query, max_results=6)
    results = web_data.get("results", [])
    if not results:
        wiki_res = search_wikipedia_fallback(query, max_results=5)
        results = wiki_res.get("results", [])

    context = "\n\n".join([f"[{i+1}] {r['title']} ({r['domain']}):\n{r['snippet']}" for i, r in enumerate(results[:5])])
    prompt = f"""Analyze research literature for: "{query}"

Sources:
{context}

Output strictly valid JSON (be concise, no long essays):
{{
  "summary": "Crisp 1-paragraph synthesis of scientific consensus (max 3 sentences)",
  "key_findings": ["Key finding 1 (1 sentence)", "Key finding 2 (1 sentence)", "Key finding 3 (1 sentence)"],
  "methodology_and_evidence": "1-sentence summary of analytical models or datasets used",
  "counter_arguments_limitations": "1-sentence summary of key limitations or open debates",
  "recommended_topics": ["Topic 1", "Topic 2", "Topic 3"]
}}"""

    json_str = call_groq(
        prompt,
        system_prompt="You are VASTUDA Academic Research Engine. Provide sharp, concise scholarly summaries formatted strictly as JSON.",
        max_tokens=420,
        json_output=True
    )

    research_data = {}
    try:
        if json_str:
            research_data = json.loads(json_str)
    except Exception as e:
        logger.warning(f"Error parsing research json: {e}")

    payload = {
        "category": "research",
        "query": query,
        "research": research_data,
        "results": results,
        "provider": web_data.get("provider", "research")
    }
    set_cached(f"research:{query.lower()}", payload)
    return payload


# CATEGORY: News Search
def search_news_mode(query, time_range=None):
    q_clean = query.strip().lower()
    is_breaking = any(k in q_clean for k in ["latest", "today", "breaking", "current", "now", "update"])
    cache_key = f"news:{q_clean}:{time_range or 'any'}"
    
    if not is_breaking:
        cached = get_cached(cache_key)
        if cached:
            return cached

    news_data = search_tavily_raw(query, max_results=10, topic="news", time_range=time_range)
    if not news_data or not news_data.get("results"):
        news_data = execute_web_query(f"{query} latest news headlines", max_results=8, time_range=time_range)

    results = []
    for r in news_data.get("results", []):
        raw_url = r.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url:
            continue
        domain = urllib.parse.urlsplit(norm_url).netloc
        res_dict = {
            "title": (r.get("title") or "").strip(),
            "url": norm_url,
            "domain": domain,
            "snippet": safe_snippet(r.get("snippet", "")),
            "published_date": r.get("published_date") or "Recent News",
            "score": r.get("score", 1.0)
        }
        if validate_result(res_dict):
            results.append(res_dict)

    deduped = deduplicate_results(results)
    payload = {
        "category": "news",
        "query": query,
        "results": deduped,
        "provider": news_data.get("provider", "news")
    }
    set_cached(cache_key, payload, ttl=NEWS_CACHE_TTL)
    return payload


# CATEGORY: Images Search (Multi-source: Wikimedia + Tavily)
def search_images_mode(query):
    cached = get_cached(f"images:{query.lower()}")
    if cached:
        return cached

    # 1. Fetch Wikimedia public domain high-res images
    wiki_images = fetch_wikimedia_images(query, limit=8)

    # 2. Fetch Tavily web images
    tav_data = search_tavily_raw(query, max_results=12, include_images=True)
    tav_images = tav_data.get("images", []) if tav_data else []

    all_images = []
    seen = set()
    for img in (wiki_images + tav_images):
        valid_img = validate_image(img)
        if valid_img:
            img_url = valid_img["url"]
            if img_url not in seen:
                seen.add(img_url)
                all_images.append(valid_img)

    payload = {
        "category": "images",
        "query": query,
        "images": all_images,
        "provider": "multisource"
    }
    set_cached(f"images:{query.lower()}", payload)
    return payload


# CATEGORY: Video Search
def search_videos_mode(query):
    cached = get_cached(f"videos:{query.lower()}")
    if cached:
        return cached

    video_query = f"{query} site:youtube.com OR site:vimeo.com video"
    web_data = execute_web_query(video_query, max_results=10)

    videos = []
    for r in web_data.get("results", []):
        raw_url = r.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url:
            continue

        title = (r.get("title") or "").strip()
        snippet = safe_snippet(r.get("snippet", ""))
        domain = urllib.parse.urlsplit(norm_url).netloc

        # Extract YouTube ID if available
        yt_match = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", norm_url)
        video_id = yt_match.group(1) if yt_match else None

        # Real thumbnail only; never fabricate with unrelated stock photography
        thumbnail = ""
        if video_id:
            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        elif domain:
            thumbnail = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"

        channel = "YouTube" if "youtube.com" in domain or "youtu.be" in domain else domain
        clean_title = re.sub(r" - YouTube$", "", title, flags=re.I)

        video_dict = {
            "title": clean_title,
            "url": norm_url,
            "thumbnail": thumbnail,
            "channel": channel,
            "domain": domain,
            "duration": "HD Video",
            "snippet": snippet
        }
        if validate_result(video_dict):
            videos.append(video_dict)

    deduped_videos = deduplicate_results(videos)
    payload = {
        "category": "videos",
        "query": query,
        "videos": deduped_videos,
        "provider": web_data.get("provider", "videos")
    }
    set_cached(f"videos:{query.lower()}", payload)
    return payload


# CATEGORY: Document/PDF Search
def search_documents_mode(query):
    cached = get_cached(f"docs:{query.lower()}")
    if cached:
        return cached

    doc_query = f"{query} filetype:pdf OR whitepaper OR manual OR documentation"
    web_data = execute_web_query(doc_query, max_results=10)

    documents = []
    for r in web_data.get("results", []):
        raw_url = r.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url:
            continue

        domain = urllib.parse.urlsplit(norm_url).netloc
        is_pdf = norm_url.lower().endswith(".pdf") or "pdf" in (r.get("title") or "").lower()
        file_type = "PDF" if is_pdf else "DOC"
        doc_dict = {
            "title": (r.get("title") or "").strip(),
            "url": norm_url,
            "domain": domain,
            "snippet": safe_snippet(r.get("snippet", "")),
            "file_type": file_type,
            "file_size": "Direct Document" if is_pdf else "Document Guide"
        }
        if validate_result(doc_dict):
            documents.append(doc_dict)

    deduped_docs = deduplicate_results(documents)
    
    # 2. Local Index Integration (Official Documentation & Knowledgebase)
    local_docs = indexer.search_local_index(query, limit=8)
    if local_docs:
        local_formatted = []
        for ld in local_docs:
            norm_u = normalize_url(ld.get("url", ""))
            if not norm_u:
                continue
            d_domain = ld.get("domain", "")
            local_formatted.append({
                "title": ld.get("title", ""),
                "url": norm_u,
                "domain": d_domain,
                "snippet": safe_snippet(ld.get("snippet", "")),
                "file_type": "DOC",
                "file_size": "Official Documentation",
                "source": "VASTUDA Local Index"
            })
        # Local docs get high precedence for documentation queries
        deduped_docs = deduplicate_results(local_formatted + deduped_docs)

    prov = "hybrid_vastuda" if (local_docs and web_data.get("results")) else ("local_index" if local_docs else web_data.get("provider", "docs"))
    payload = {
        "category": "docs",
        "query": query,
        "documents": deduped_docs,
        "provider": prov
    }
    set_cached(f"docs:{query.lower()}", payload)
    return payload


# CATEGORY: Developer/Code Search (GitHub Public API + Web)
def search_code_mode(query):
    cached = get_cached(f"code:{query.lower()}")
    if cached:
        return cached

    repos = []
    # 1. Query GitHub Search API (Free public endpoint)
    try:
        gh_url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(query)}&sort=stars&order=desc&per_page=6"
        gh_resp = http_session.get(gh_url, headers={"User-Agent": "VASTUDA-Search-Engine"}, timeout=(3.05, 4.0))
        if gh_resp.status_code == 200:
            gh_data = gh_resp.json()
            for repo in gh_data.get("items", []):
                repo_url = normalize_url(repo.get("html_url", ""))
                if not repo_url:
                    continue
                repos.append({
                    "name": (repo.get("full_name") or "").strip(),
                    "url": repo_url,
                    "description": safe_snippet(repo.get("description") or "No description provided"),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language") or "Code",
                    "owner": repo.get("owner", {}).get("login", ""),
                    "avatar": repo.get("owner", {}).get("avatar_url", "")
                })
    except Exception as e:
        logger.warning(f"GitHub API search error: {type(e).__name__}")

    # 2. Query web for developer discussions and documentation
    dev_query = f"{query} programming documentation github stackoverflow example"
    web_data = execute_web_query(dev_query, max_results=6)
    valid_web_results = deduplicate_results([
        r for r in web_data.get("results", []) if validate_result(r)
    ])

    payload = {
        "category": "code",
        "query": query,
        "repositories": repos,
        "web_results": valid_web_results,
        "provider": "github+web"
    }
    set_cached(f"code:{query.lower()}", payload)
    return payload


# CATEGORY: Shopping Discovery (Internal Clean Implementation)
def search_shopping_mode(query):
    cached = get_cached(f"shopping:{query.lower()}")
    if cached:
        return cached

    shop_query = f"{query} buy online price store specifications"
    web_data = execute_web_query(shop_query, max_results=10)

    products = []
    for r in web_data.get("results", []):
        raw_url = r.get("url", "")
        norm_url = normalize_url(raw_url)
        if not norm_url:
            continue

        domain = urllib.parse.urlsplit(norm_url).netloc
        title = (r.get("title") or "").strip()
        snippet = safe_snippet(r.get("snippet", ""))

        # Extract price if present
        price_match = re.search(r"(\$|₹|£|€)\s?([\d,]+(?:\.\d{2})?)", snippet + " " + title)
        price_str = price_match.group(0) if price_match else "View Source"
        merchant = domain.replace("www.", "").split(".")[0].capitalize()

        prod_dict = {
            "title": title,
            "url": norm_url,
            "domain": domain,
            "merchant": merchant,
            "price": price_str,
            "snippet": snippet
        }
        if validate_result(prod_dict):
            products.append(prod_dict)

    deduped_products = deduplicate_results(products)
    payload = {
        "category": "shopping",
        "query": query,
        "products": deduped_products,
        "provider": web_data.get("provider", "shopping")
    }
    set_cached(f"shopping:{query.lower()}", payload)
    return payload

    payload = {
        "category": "shopping",
        "query": query,
        "products": products,
        "provider": web_data.get("provider", "shopping")
    }
    set_cached(f"shopping:{query.lower()}", payload)
    return payload


# CATEGORY: Jobs Search
def search_jobs_mode(query):
    cached = get_cached(f"jobs:{query.lower()}")
    if cached:
        return cached

    jobs_query = f"{query} jobs careers hiring openings apply"
    web_data = execute_web_query(jobs_query, max_results=10)

    jobs = []
    for r in web_data.get("results", []):
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        domain = r.get("domain", "")
        url = r.get("url", "")

        is_remote = "remote" in snippet.lower() or "remote" in title.lower()
        location = "Remote / Worldwide" if is_remote else "Global / Multiple Locations"

        company = domain.replace("www.", "").split(".")[0].capitalize()
        if "linkedin.com" in domain:
            company = "LinkedIn Jobs"
        elif "indeed.com" in domain:
            company = "Indeed"
        elif "glassdoor.com" in domain:
            company = "Glassdoor"

        jobs.append({
            "title": title,
            "company": company,
            "location": location,
            "type": "Full-Time",
            "snippet": snippet,
            "url": url,
            "domain": domain
        })

    payload = {
        "category": "jobs",
        "query": query,
        "jobs": jobs,
        "provider": web_data.get("provider", "jobs")
    }
    set_cached(f"jobs:{query.lower()}", payload)
    return payload


# Query Intent Classifier
def classify_query_intent(query: str) -> dict:
    """Classify queries using structured deterministic Query Engine."""
    u = query_engine.understand_query(query)
    return {
        "intent": u["intent"],
        "confidence": 0.95,
        "target_category": u["vertical"],
        "language": u["language"],
        "freshness_required": u["freshness_required"],
        "entities": u["entities"],
        "normalized_query": u["normalized_query"]
    }


def search_with_hybrid_ranking(query: str, max_results: int = 8, time_range=None, debug: bool = False):
    """
    Execute VASTUDA 5.3 Production Multi-Layer Hybrid Search:
    1. Query Understanding (safe normalization, tokenization, phrase extraction, intent, language, freshness).
    2. Query VASTUDA Local FTS5 Index (with site: restriction and term expansion).
    3. Query Web Retriever (Tavily + DuckDuckGo + Wikipedia bounded non-blocking).
    4. Merge candidates, validate schema, normalize canonical URLs.
    5. Deduplicate and score using transparent multi-signal relevance ranker.
    6. Enforce adaptive domain diversity damping.
    7. Determine transparent provider provenance.
    """
    q_info = query_engine.understand_query(query)
    q_lang = q_info.get("language", "en")

    # 1. Local VASTUDA Index Retrieval
    local_candidates = []
    try:
        raw_local = indexer.search_local_index(query, limit=indexer.RANKING_TOP_K, query_info=q_info, debug=debug)
        # If Hinglish and few local matches, also try normalized/expanded terms
        if len(raw_local) < 2 and q_info.get("expanded_terms"):
            expanded_q = " ".join(q_info["expanded_terms"][:4])
            if expanded_q != query:
                extra_local = indexer.search_local_index(expanded_q, limit=6, query_info=q_info, debug=debug)
                raw_local.extend(extra_local)

        for item in raw_local:
            norm = normalize_url(item.get("url", ""))
            if norm:
                item["url"] = norm
                if validate_result(item):
                    local_candidates.append(item)
    except Exception as e:
        logger.warning(f"Local index fetch note: {e}")

    # 2. Web Retriever (External Fallback / Augmentation)
    web_data = execute_web_query(query, max_results=max(max_results, 8), time_range=time_range)
    web_candidates = web_data.get("results", [])

    # If web query returned 0 and query is Hinglish or multi-term, try expanded query fallback
    if not web_candidates and q_lang == "hinglish" and q_info.get("expanded_terms"):
        fallback_q = " ".join(q_info["expanded_terms"][:4])
        logger.info(f"Hinglish fallback query to web: {fallback_q}")
        web_data = execute_web_query(fallback_q, max_results=max(max_results, 8), time_range=time_range)
        web_candidates = web_data.get("results", [])

    # 3. Merge & Deduplicate
    combined = local_candidates + web_candidates
    deduped = deduplicate_results(combined)

    # 4. Multi-Signal Ranking over merged candidates using indexer.score_candidates
    final_ranked = indexer.score_candidates(
        deduped, query, query_info=q_info, debug=debug, max_results=max_results
    )

    # 5. Provider Provenance Labeling
    has_local = any(r.get("source") == "VASTUDA Local Index" for r in final_ranked)
    has_web = any(r.get("source") != "VASTUDA Local Index" for r in final_ranked)

    provider = "none"
    if final_ranked:
        if has_local and has_web:
            provider = "hybrid_vastuda"
        elif has_local:
            provider = "local_index"
        else:
            provider = web_data.get("provider", "web")

    return {
        "results": final_ranked,
        "images": web_data.get("images", []),
        "provider": provider,
        "query_understanding": q_info,
        "message": "Insufficient information from available sources." if not final_ranked else None
    }


# Master router
def route_search_category(query, category="all", time_range=None):
    """Route query to the specific category search engine."""
    cat = (category or "all").lower().strip()
    if cat in ["all", "web"]:
        return None
    elif cat in ["ai", "assistant"]:
        return search_ai_mode(query)
    elif cat in ["research", "academic"]:
        return search_research_mode(query)
    elif cat in ["news"]:
        return search_news_mode(query, time_range=time_range)
    elif cat in ["images", "image"]:
        return search_images_mode(query)
    elif cat in ["videos", "video"]:
        return search_videos_mode(query)
    elif cat in ["docs", "pdf", "documents"]:
        return search_documents_mode(query)
    elif cat in ["code", "developer", "dev"]:
        return search_code_mode(query)
    elif cat in ["shopping", "products"]:
        return search_shopping_mode(query)
    elif cat in ["jobs", "careers"]:
        return search_jobs_mode(query)
    else:
        return None
