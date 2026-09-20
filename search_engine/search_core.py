import os
import re
import json
import time
import logging
import urllib.parse
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("SearchCore")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"

# High-speed connection pool
http_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=1)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# Category cache
CATEGORY_CACHE = {}
CACHE_TTL = 900  # 15 mins


def get_cached(key):
    if key in CATEGORY_CACHE:
        ts, data = CATEGORY_CACHE[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def set_cached(key, data):
    CATEGORY_CACHE[key] = (time.time(), data)


# --- 1. Base Search Providers ---

def sanitize_snippet(text, max_len=200):
    """Sanitize and limit snippet text to prevent huge walls of text."""
    if not text:
        return "Visit website for complete article and details."
    # Strip markdown headers, tags, citations, edit markers
    clean = re.sub(r"\[\.\.\.\]", " ", text)
    clean = re.sub(r"\[edit\]", "", clean, flags=re.I)
    clean = re.sub(r"#+\s*", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) > max_len:
        truncated = clean[:max_len].rsplit(" ", 1)[0]
        return truncated.strip() + "..."
    return clean


def search_tavily_raw(query, search_depth="basic", max_results=8, topic="general", include_images=True):
    """Query Tavily Search API with image and snippet control."""
    if not TAVILY_API_KEY:
        return None
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
        resp = http_session.post(url, json=payload, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            results = []
            for item in data.get("results", []):
                domain = ""
                try:
                    domain = urllib.parse.urlparse(item.get("url", "")).netloc
                except Exception:
                    pass
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "domain": domain,
                    "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
                    "snippet": sanitize_snippet(item.get("content", "")),
                    "score": item.get("score", 1.0),
                    "published_date": item.get("published_date", "")
                })
            images = []
            for img in data.get("images", []):
                if isinstance(img, str):
                    images.append({"url": img, "title": query, "source": "web"})
                elif isinstance(img, dict):
                    images.append({
                        "url": img.get("url", ""),
                        "title": img.get("description", query),
                        "source": "web"
                    })
            return {"results": results, "images": images, "provider": "tavily"}
        else:
            logger.warning(f"Tavily returned {resp.status_code}")
            return None
    except Exception as e:
        logger.error(f"Tavily error: {e}")
        return None


def search_duckduckgo_raw(query, max_results=10):
    """Fallback search using DuckDuckGo HTML scraping."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        url = "https://html.duckduckgo.com/html/"
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=8)
        if resp.status_code != 200:
            return {"results": [], "images": [], "provider": "error"}

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

            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
            domain = ""
            try:
                domain = urllib.parse.urlparse(target_url).netloc
            except Exception:
                pass

            if target_url and title:
                results.append({
                    "title": title,
                    "url": target_url,
                    "domain": domain,
                    "favicon": f"https://www.google.com/s2/favicons?domain={domain}&sz=64" if domain else "",
                    "snippet": sanitize_snippet(snippet),
                    "score": 1.0,
                    "published_date": ""
                })

        return {"results": results, "images": [], "provider": "duckduckgo"}
    except Exception as e:
        logger.error(f"DuckDuckGo error: {e}")
        return {"results": [], "images": [], "provider": "failed"}


def execute_web_query(query, max_results=8, topic="general", include_images=True):
    """Execute search query with Tavily and fallback to DuckDuckGo."""
    # Detect news intent automatically
    q_lower = query.lower()
    if any(k in q_lower for k in ["news", "today", "latest", "breaking", "update", "headline"]):
        topic = "news"

    data = search_tavily_raw(query, max_results=max_results, topic=topic, include_images=include_images)
    if not data or not data.get("results"):
        data = search_duckduckgo_raw(query, max_results=max_results)
    return data or {"results": [], "images": [], "provider": "none"}


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

    academic_query = f"{query} research study paper analysis findings"
    web_data = execute_web_query(academic_query, max_results=6)
    results = web_data.get("results", [])

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
def search_news_mode(query):
    cached = get_cached(f"news:{query.lower()}")
    if cached:
        return cached

    news_data = search_tavily_raw(query, max_results=10, topic="news")
    if not news_data or not news_data.get("results"):
        news_data = execute_web_query(f"{query} latest news headlines", max_results=8)

    results = []
    for r in news_data.get("results", []):
        results.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "domain": r.get("domain", ""),
            "snippet": r.get("snippet", ""),
            "published_date": r.get("published_date") or "Recent News",
            "score": r.get("score", 1.0)
        })

    payload = {
        "category": "news",
        "query": query,
        "results": results,
        "provider": news_data.get("provider", "news")
    }
    set_cached(f"news:{query.lower()}", payload)
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
        url = img.get("url") if isinstance(img, dict) else img
        if url and url not in seen:
            seen.add(url)
            all_images.append({
                "url": url,
                "title": (img.get("title") if isinstance(img, dict) else query) or query,
                "source": "web"
            })

    payload = {
        "category": "images",
        "query": query,
        "images": all_images,
        "provider": "multisource"
    }
    set_cached(f"images:{query.lower()}", payload)
    return payload

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
        url = r.get("url", "")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        domain = r.get("domain", "")

        # Extract YouTube ID if available
        yt_match = re.search(r"(?:v=|youtu\.be/|embed/)([a-zA-Z0-9_-]{11})", url)
        video_id = yt_match.group(1) if yt_match else None

        thumbnail = ""
        if video_id:
            thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        else:
            thumbnail = f"https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=480&q=80"

        channel = "YouTube" if "youtube.com" in domain or "youtu.be" in domain else domain
        clean_title = re.sub(r" - YouTube$", "", title, flags=re.I)

        videos.append({
            "title": clean_title,
            "url": url,
            "thumbnail": thumbnail,
            "channel": channel,
            "domain": domain,
            "duration": "HD Video",
            "snippet": snippet
        })

    payload = {
        "category": "videos",
        "query": query,
        "videos": videos,
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
        url = r.get("url", "")
        is_pdf = url.lower().endswith(".pdf") or "pdf" in r.get("title", "").lower()
        file_type = "PDF" if is_pdf else "DOC"
        documents.append({
            "title": r.get("title", ""),
            "url": url,
            "domain": r.get("domain", ""),
            "snippet": r.get("snippet", ""),
            "file_type": file_type,
            "file_size": "Direct Download" if is_pdf else "Document Guide"
        })

    payload = {
        "category": "docs",
        "query": query,
        "documents": documents,
        "provider": web_data.get("provider", "docs")
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
        gh_resp = http_session.get(gh_url, headers={"User-Agent": "VASTUDA-Search-Engine"}, timeout=4)
        if gh_resp.status_code == 200:
            gh_data = gh_resp.json()
            for repo in gh_data.get("items", []):
                repos.append({
                    "name": repo.get("full_name", ""),
                    "url": repo.get("html_url", ""),
                    "description": repo.get("description", "No description provided"),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language") or "Code",
                    "owner": repo.get("owner", {}).get("login", ""),
                    "avatar": repo.get("owner", {}).get("avatar_url", "")
                })
    except Exception as e:
        logger.warning(f"GitHub API search error: {e}")

    # 2. Query web for developer discussions and documentation
    dev_query = f"{query} programming documentation github stackoverflow example"
    web_data = execute_web_query(dev_query, max_results=6)

    payload = {
        "category": "code",
        "query": query,
        "repositories": repos,
        "web_results": web_data.get("results", []),
        "provider": "github+web"
    }
    set_cached(f"code:{query.lower()}", payload)
    return payload


# CATEGORY: Shopping Discovery (Affiliate Ready)
def search_shopping_mode(query):
    cached = get_cached(f"shopping:{query.lower()}")
    if cached:
        return cached

    shop_query = f"{query} buy online price deals store specifications"
    web_data = execute_web_query(shop_query, max_results=10)

    products = []
    for r in web_data.get("results", []):
        domain = r.get("domain", "")
        title = r.get("title", "")
        snippet = r.get("snippet", "")
        url = r.get("url", "")

        # Extract price if present
        price_match = re.search(r"(\$|₹|£|€)\s?([\d,]+(?:\.\d{2})?)", snippet + " " + title)
        price_str = price_match.group(0) if price_match else "View Deal"

        merchant = domain.replace("www.", "").split(".")[0].capitalize()

        affiliate_url = url
        separator = "&" if "?" in url else "?"
        affiliate_url = f"{url}{separator}tag=vastuda-21"

        products.append({
            "title": title,
            "url": affiliate_url,
            "domain": domain,
            "merchant": merchant,
            "price": price_str,
            "snippet": snippet,
            "rating": "4.6 ★"
        })

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


# Master router
def route_search_category(query, category="all"):
    """Route query to the specific category search engine."""
    cat = (category or "all").lower().strip()
    if cat in ["all", "web"]:
        return None
    elif cat in ["ai", "assistant"]:
        return search_ai_mode(query)
    elif cat in ["research", "academic"]:
        return search_research_mode(query)
    elif cat in ["news"]:
        return search_news_mode(query)
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
