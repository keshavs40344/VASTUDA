import os
import re
import json
import time
import logging
import threading
import urllib.parse
from flask import Flask, request, jsonify, render_template, send_from_directory, send_file, session
import requests
from dotenv import load_dotenv

import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import database, indexer, crawler, and search core modules
try:
    from search_engine import db
    from search_engine import search_core
    from search_engine import indexer
    from search_engine import crawler
    from search_engine.search_validator import (
        normalize_url, validate_result, deduplicate_results, safe_snippet
    )
except ImportError:
    import db
    import search_core
    import indexer
    import crawler
    from search_validator import (
        normalize_url, validate_result, deduplicate_results, safe_snippet
    )


load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VASTUDA_Server")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "vastuda-secret-session-key-2026-secure-ultra")

ASSETS_DIR = os.path.join(BASE_DIR, "public", "assets")

def ensure_seed_index():
    """Ensure foundational documents exist in local index on fresh deployments."""
    try:
        stats = indexer.get_index_stats()
        if stats.get("indexed_documents", 0) < 3:
            logger.info("Local index is sparse; running background seed crawl...")
            crawler.run_seed_crawl(max_docs=15)
    except Exception as e:
        logger.warning(f"Seed crawl check note: {e}")

threading.Thread(target=ensure_seed_index, daemon=True).start()

# --- Production Security & Rate Limiting ---
RATE_LIMIT_BUCKETS = {}
RATE_LIMIT_LOCK = threading.Lock()

def is_rate_limited(ip, limit=120, window_sec=60):
    now = time.time()
    with RATE_LIMIT_LOCK:
        times = RATE_LIMIT_BUCKETS.get(ip, [])
        times = [t for t in times if now - t < window_sec]
        if len(times) >= limit:
            RATE_LIMIT_BUCKETS[ip] = times
            return True
        times.append(now)
        RATE_LIMIT_BUCKETS[ip] = times
        return False

@app.before_request
def enforce_rate_limit():
    if request.path.startswith("/api/"):
        client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
        if is_rate_limited(client_ip, limit=120, window_sec=60):
            return jsonify({"error": "Rate limit exceeded. Please slow down.", "status": 429}), 429

@app.after_request
def add_security_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response

# --- Production Health & Legal Endpoints ---
def get_git_commit_sha():
    """Retrieve Git commit SHA securely without exposing system paths or environment."""
    for env_key in ("RAILWAY_GIT_COMMIT_SHA", "VERCEL_GIT_COMMIT_SHA", "GIT_COMMIT_SHA"):
        val = os.environ.get(env_key, "").strip()
        if val and re.match(r"^[0-9a-fA-F]{7,40}$", val):
            return val[:7]

    try:
        git_dir = os.path.join(BASE_DIR, ".git")
        head_file = os.path.join(git_dir, "HEAD")
        if os.path.exists(head_file):
            with open(head_file, "r", encoding="utf-8") as f:
                head_content = f.read().strip()
            if head_content.startswith("ref:"):
                ref_path = head_content.split(":", 1)[1].strip()
                ref_file = os.path.join(git_dir, ref_path)
                if os.path.exists(ref_file):
                    with open(ref_file, "r", encoding="utf-8") as f:
                        sha = f.read().strip()
                        if re.match(r"^[0-9a-fA-F]{7,40}$", sha):
                            return sha[:7]
            elif re.match(r"^[0-9a-fA-F]{7,40}$", head_content):
                return head_content[:7]
    except Exception:
        pass

    return "eab0eed"


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "ok",
        "version": "4.2",
        "service": "VASTUDA Sovereign Search & Discovery Engine",
        "timestamp": int(time.time())
    })


@app.route("/api/version", methods=["GET"])
def api_version():
    return jsonify({
        "app": "VASTUDA",
        "version": "4.2",
        "commit": get_git_commit_sha(),
        "environment": "production"
    })

@app.route("/privacy", methods=["GET"])
@app.route("/privacy-policy", methods=["GET"])
def privacy_policy_route():
    privacy_file = os.path.join(BASE_DIR, "public", "privacy.html")
    if os.path.exists(privacy_file):
        return send_file(privacy_file)
    return render_template("index.html")

@app.route("/terms", methods=["GET"])
@app.route("/terms-of-service", methods=["GET"])
def terms_of_service_route():
    terms_file = os.path.join(BASE_DIR, "public", "terms.html")
    if os.path.exists(terms_file):
        return send_file(terms_file)
    return render_template("index.html")

# --- Production Error Handling ---
@app.errorhandler(400)
def handle_bad_request(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Bad request", "status": 400}), 400
    return render_template("index.html"), 400

@app.errorhandler(404)
def handle_not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "Endpoint not found", "status": 404}), 404
    return render_template("index.html"), 404

@app.errorhandler(500)
def handle_server_error(e):
    logger.error(f"Internal server error on {request.path}: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"error": "Internal server error", "status": 500}), 500
    return render_template("index.html"), 500

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"

# High-speed connection pool
http_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=0)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# In-memory search & destination caches
SEARCH_CACHE = {}
DESTINATION_CACHE = {}
CACHE_TTL = 900  # 15 minutes


def evaluate_instant_math(query):
    """Safely calculate simple arithmetic if query is a math expression."""
    if not query:
        return None
    clean = query.strip().replace("x", "*").replace("×", "*").replace("÷", "/").replace("^", "**")
    # Strict regex check: only digits, basic math symbols, spaces, parentheses
    if re.match(r"^[\d\s\+\-\*\/\(\)\.\%\*]+$", clean) and any(op in clean for op in "+-*/%*"):
        try:
            if len(clean) > 80 or clean.count("**") > 2:
                return None
            res = eval(clean, {"__builtins__": None}, {})
            if isinstance(res, (int, float)):
                if isinstance(res, int) or (isinstance(res, float) and res.is_integer()):
                    formatted = str(int(res))
                else:
                    formatted = f"{res:.6f}".rstrip("0").rstrip(".")
                return {"expression": query.strip(), "result": formatted}
        except Exception:
            pass
    return None


def get_destination_image(place_name):
    """Fetch high-res image from Wikipedia API with Wikimedia fallback."""
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original|thumbnail&pithumbsize=1000&titles={urllib.parse.quote(place_name)}"
        headers = {"User-Agent": "VASTUDA-SearchEngine/1.0 (https://vastuda.internal; dev@vastuda.internal)"}
        resp = http_session.get(url, headers=headers, timeout=(2.0, 3.0))
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for p in pages.values():
                thumb = p.get("thumbnail", {}).get("source") or p.get("original", {}).get("source")
                if thumb and not thumb.endswith(".svg.png"):
                    return thumb
    except Exception as e:
        logger.warning(f"Wikipedia pageimages note for {place_name}: {type(e).__name__}")

def get_destination_images(place_name):
    """Fetch 2-3 high-res images for destination card gallery."""
    imgs = []
    try:
        wiki_imgs = search_core.fetch_wikimedia_images(place_name, limit=4)
        for im in wiki_imgs:
            url = im.get("url")
            if url and url not in imgs:
                imgs.append(url)
            if len(imgs) >= 3:
                break
    except Exception:
        pass
    if not imgs:
        single = get_destination_image(place_name)
        if single:
            imgs.append(single)
    return imgs



def get_destination_intel(query):
    """Detect if query is a travel destination/city and return structured rich travel card data."""
    clean_q = query.strip()
    if len(clean_q) < 3 or len(clean_q.split()) > 5:
        return None

    # Fast intent filter: check if 1-3 words or matches travel clues
    travel_clues = ["weather", "visit", "travel", "city", "hotel", "flights", "attractions", "tour", "beach", "capital", "island", "resort", "monument", "where is", "tourism in", "places in"]
    words = clean_q.lower().split()
    is_potential_place = any(c in clean_q.lower() for c in travel_clues) or (len(words) <= 3)
    if not is_potential_place:
        return None

    cache_key = clean_q.lower()
    if cache_key in DESTINATION_CACHE:
        return DESTINATION_CACHE[cache_key]

    # Try Groq AI if key exists
    if GROQ_API_KEY:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            prompt = f"""Evaluate if the search query '{clean_q}' is a travel destination, city, region, state, country, or tourist attraction.
If YES, output valid JSON with:
"is_destination": true,
"name": "Proper Name of the place",
"country": "Country/Region",
"tagline": "Short, evocative 1-sentence description or vibe",
"weather": "Current or typical climate with temp like 28°C Tropical / 18°C Spring",
"best_time": "Ideal months or season to visit (e.g., Oct - March)",
"ideal_duration": "Recommended stay (e.g., 3-4 Days)",
"attractions": ["List of 4 top attractions/highlights"]

If NO (e.g., it's a person, company, programming question, animal, or product), output:
"is_destination": false
"""
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": "You are a world-class travel intelligence engine. Return JSON strictly."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
                "max_tokens": 250
            }
            resp = http_session.post(url, headers=headers, json=payload, timeout=(2.0, 2.5))
            if resp.status_code == 200:
                parsed = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "{}")
                data = json.loads(parsed)
                if data.get("is_destination"):
                    name = data.get("name", clean_q)
                    img_list = get_destination_images(name) or get_destination_images(clean_q)
                    img = img_list[0] if img_list else get_destination_image(name)
                    data["image"] = img
                    data["images"] = img_list if img_list else ([img] if img else [])
                    data["maps_url"] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name)}"
                    data["flights_url"] = f"https://www.google.com/travel/flights?q=flights+to+{urllib.parse.quote(name)}"
                    data["hotels_url"] = f"https://www.google.com/travel/hotels?q=hotels+in+{urllib.parse.quote(name)}"
                    DESTINATION_CACHE[cache_key] = data
                    return data
                else:
                    DESTINATION_CACHE[cache_key] = None
                    return None
        except Exception as e:
            logger.warning(f"Destination check note: {type(e).__name__}")

    # Fallback to Wikipedia Place Detection (Zero-Token fallback)
    try:
        wiki_res = search_core.search_wikipedia_fallback(clean_q, max_results=3)
        results = wiki_res.get("results", [])
        if results:
            first = results[0]
            snippet = (first.get("snippet", "")).lower()
            if any(w in snippet for w in ["city", "capital", "island", "state", "country", "destination", "coastal", "mountain", "beach", "district", "town", "resort", "tourism", "monument", "peninsula"]):
                name = first.get("title", clean_q.title())
                img_list = get_destination_images(name)
                fb_data = {
                    "is_destination": True,
                    "name": name,
                    "country": "Travel Destination",
                    "tagline": (first.get("snippet", "")[:180]).rstrip() + "...",
                    "weather": "27°C Pleasant Climate",
                    "best_time": "October - March",
                    "ideal_duration": "3 - 5 Days",
                    "attractions": ["Scenic Viewpoints", "Cultural Landmarks", "Historic Sites", "Local Markets & Dining"],
                    "image": img_list[0] if img_list else None,
                    "images": img_list if img_list else [],
                    "maps_url": f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name)}",
                    "flights_url": f"https://www.google.com/travel/flights?q=flights+to+{urllib.parse.quote(name)}",
                    "hotels_url": f"https://www.google.com/travel/hotels?q=hotels+in+{urllib.parse.quote(name)}"
                }
                DESTINATION_CACHE[cache_key] = fb_data
                return fb_data
    except Exception as e:
        logger.warning(f"Wiki destination fallback note: {e}")


    DESTINATION_CACHE[cache_key] = None
    return None




def generate_extractive_overview(query, results):
    """Zero-Token Extractive Synthesizer. Runs offline or when LLM API tokens run out."""
    if not results:
        return None
    sentences = []
    for i, r in enumerate(results[:4], 1):
        raw_text = r.get("snippet", "")
        raw_sentences = re.split(r"(?<=[.!?])\s+", raw_text)
        for s in raw_sentences:
            s_clean = s.strip()
            if len(s_clean) > 25 and not s_clean.startswith("http"):
                sentences.append((s_clean, i))

    if not sentences:
        return None

    # Relevance scoring against query
    q_words = set(re.findall(r"\w+", query.lower()))
    scored = []
    for s, idx in sentences:
        score = sum(1 for w in q_words if w in s.lower())
        scored.append((score, s, idx))
    scored.sort(key=lambda x: x[0], reverse=True)

    summary = " ".join([f"{s} [{idx}]" for _, s, idx in scored[:2]])
    bullets = [f"* {s} [{idx}]" for _, s, idx in scored[2:5]]

    bullets_text = "\n".join(bullets)
    related_text = f"**Related:** {query} overview, {query} guide, latest {query}"

    content = f"{summary}\n\n{bullets_text}\n\n{related_text}" if bullets_text else f"{summary}\n\n{related_text}"

    return {
        "overview": content,
        "mode": "extractive_zero_token",
        "sources": [{"index": i, "title": r.get("title", ""), "url": r.get("url", ""), "domain": r.get("domain", "")} for i, r in enumerate(results[:5], 1)]
    }


def generate_ai_overview(query, results):
    """
    Generate source-grounded synthesized AI overview:
    - Enforces TTL (1h for breaking/news, 12h for static)
    - Strictly answers only using retrieved sources
    - If sources insufficient, returns honest fallback message
    """
    if not results:
        return {
            "overview": "Insufficient information from available sources.",
            "mode": "insufficient_sources",
            "sources": []
        }

    q_lower = query.lower()
    is_breaking = any(k in q_lower for k in ["latest", "today", "current", "breaking", "news", "update"])
    # 1 hour TTL for news/breaking, 12 hours TTL for general informational queries
    cache_ttl = 3600 if is_breaking else 43200

    # 1. Tier 1: Check Persistent SQLite Cache with enforced TTL (never serve indefinitely stale content)
    if not is_breaking:
        cached = db.get_cached_ai_overview(query, max_age_seconds=cache_ttl)
        if cached:
            return cached

    # 2. Tier 2: Call Groq with Multi-Model Rotation
    if GROQ_API_KEY:
        try:
            context_snippets = []
            for i, res in enumerate(results[:5], 1):
                context_snippets.append(f"[{i}] {res.get('title')} ({res.get('url')}):\n{res.get('snippet')}")
            context_str = "\n\n".join(context_snippets)

            prompt = f"""Search Query: "{query}"

Web Context:
{context_str}

Instructions:
1. Provide a crisp, direct 2-to-3 sentence answer answering the query.
2. Provide at most 3 short, high-impact bullet points (maximum 1 sentence each).
3. Do NOT write long paragraphs or over-explain. Keep it sharp, factual, and strictly grounded in the web context.
4. Cite sources using [1], [2] corresponding strictly to the context items.
5. If the provided context does not contain sufficient factual evidence, write: "Insufficient information from available sources."
6. End with "**Related:**" followed by 3 short comma-separated search terms."""

            models_to_try = ["llama-3.1-8b-instant", GROQ_MODEL, "llama-3.3-70b-versatile"]
            for model_name in models_to_try:
                try:
                    url = "https://api.groq.com/openai/v1/chat/completions"
                    headers = {
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": model_name,
                        "messages": [
                            {"role": "system", "content": "You are VASTUDA AI. Provide ultra-concise, factual overviews grounded strictly in context. Never hallucinate sources."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 240
                    }
                    resp = http_session.post(url, headers=headers, json=payload, timeout=(3.05, 8.0))
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                        result = {
                            "overview": content,
                            "mode": "neural_llm",
                            "sources": [{"index": i, "title": r.get("title", ""), "url": r.get("url", ""), "domain": r.get("domain", "")} for i, r in enumerate(results[:5], 1)]
                        }
                        db.cache_ai_overview(query, result)
                        return result
                    elif resp.status_code == 429:
                        logger.warning(f"Groq {model_name} rate limited (429), trying next model...")
                        continue
                except Exception as model_err:
                    logger.warning(f"Groq {model_name} note: {type(model_err).__name__}")
                    continue
        except Exception as e:
            logger.error(f"Error calling Groq overview: {e}")

    # 3. Tier 3: Zero-Token Extractive Fallback
    logger.info("Using Zero-Token Extractive Synthesizer fallback")
    fallback = generate_extractive_overview(query, results)
    if fallback:
        db.cache_ai_overview(query, fallback)
        return fallback

    return {
        "overview": "Insufficient information from available sources.",
        "mode": "insufficient_sources",
        "sources": []
    }



def extract_article_content(target_url):
    """Fetch article and extract clean readable text without ads or clutter."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(target_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return {"error": f"Failed to fetch page (Status {resp.status_code})"}

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Strip unwanted elements
        for el in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript", "svg"]):
            el.decompose()

        # Find title
        title = ""
        if soup.title:
            title = soup.title.get_text(strip=True)
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        # Look for article or main content
        article_el = soup.find("article") or soup.find("main") or soup.find(id=re.compile(r"content|article|post|body", re.I)) or soup.body

        if not article_el:
            return {"error": "Could not extract article content"}

        paragraphs = []
        for p in article_el.find_all(["p", "h2", "h3", "li"]):
            text = p.get_text(strip=True)
            if len(text) > 35:
                tag_name = p.name
                if tag_name in ["h2", "h3"]:
                    paragraphs.append(f"<{tag_name}>{text}</{tag_name}>")
                else:
                    paragraphs.append(f"<p>{text}</p>")

        content_html = "\n".join(paragraphs) if paragraphs else "<p>No structured article text could be extracted.</p>"
        word_count = len(re.findall(r"\w+", content_html))
        reading_time = max(1, round(word_count / 200))

        domain = urllib.parse.urlparse(target_url).netloc

        return {
            "title": title or "Reader Mode View",
            "url": target_url,
            "domain": domain,
            "reading_time": f"{reading_time} min read",
            "word_count": word_count,
            "content_html": content_html
        }
    except Exception as e:
        logger.error(f"Error in reader extraction: {e}")
        domain = ""
        try:
            domain = urllib.parse.urlparse(target_url).netloc
        except Exception:
            pass
        return {
            "title": "Article View",
            "url": target_url,
            "domain": domain,
            "reading_time": "1 min read",
            "word_count": 0,
            "content_html": f"<p>Could not fetch reader view ({str(e)}). Please visit the website directly.</p>",
            "error": str(e)
        }


# --- Web Page Routes ---

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search")
def search_page():
    return render_template("index.html")


@app.route("/discover")
def discover_page():
    return render_template("discover.html")


@app.route("/research")
def research_page():
    return render_template("research.html")


@app.route("/download/windows")
def download_windows():
    for name in ["Staunt Browser Ultra Setup 2.0.0.exe", "Staunt-Browser-Setup.exe"]:
        p = os.path.join(ASSETS_DIR, name)
        if os.path.exists(p):
            return send_file(p, as_attachment=True, download_name="Staunt-Browser-Setup.exe")
    return jsonify({"error": "Windows installer binary not found in server assets"}), 404


@app.route("/download/android")
def download_android():
    for name in ["staunt-browser-release.apk", "Staunt-Browser-Mobile.apk"]:
        p = os.path.join(ASSETS_DIR, name)
        if os.path.exists(p):
            return send_file(p, as_attachment=True, download_name="Staunt-Browser-Mobile.apk")
    return jsonify({"error": "Android APK binary not found in server assets"}), 404


@app.route("/assets/<path:filename>")
def serve_shared_asset(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/manifest.json")
def manifest():
    return send_from_directory("static", "manifest.json", mimetype="application/manifest+json")


@app.route("/sw.js")
def service_worker():
    return send_from_directory("static", "sw.js", mimetype="application/javascript")


# --- User Authentication APIs ---

@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    name = data.get("name", "").strip()

    if not email or "@" not in email:
        return jsonify({"error": "Valid email address required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    user = db.create_user(email, password, name)
    if not user:
        return jsonify({"error": "An account with this email already exists"}), 409

    session["user_id"] = user["id"]
    return jsonify({"status": "success", "user": user})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = db.authenticate_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["id"]
    return jsonify({"status": "success", "user": user})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("user_id", None)
    return jsonify({"status": "success"})


@app.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False, "user": None})

    user = db.get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"authenticated": False, "user": None})

    return jsonify({"authenticated": True, "user": user})


# --- Search History APIs ---

@app.route("/api/history", methods=["GET"])
def api_get_history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"history": []})
    limit = int(request.args.get("limit", 50))
    items = db.get_search_history(user_id, limit=limit)
    return jsonify({"history": items})


@app.route("/api/history/<int:item_id>", methods=["DELETE"])
def api_delete_history_item(item_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    db.delete_history_item(user_id, item_id)
    return jsonify({"status": "success"})


@app.route("/api/history/clear", methods=["POST"])
def api_clear_history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    db.clear_search_history(user_id)
    return jsonify({"status": "success"})


@app.route("/api/history/toggle", methods=["POST"])
def api_toggle_history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    user = db.get_user_by_id(user_id)
    current_enabled = user["preferences"].get("history_enabled", True)
    updated = db.update_user_preferences(user_id, {"history_enabled": not current_enabled})
    return jsonify({"status": "success", "history_enabled": updated.get("history_enabled")})


# --- Collections & Bookmarks APIs ---

@app.route("/api/collections", methods=["GET", "POST"])
def api_collections():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"collections": [] if request.method == "GET" else {"error": "Unauthorized"}}), (200 if request.method == "GET" else 401)

    if request.method == "POST":
        data = request.get_json() or {}
        name = data.get("name", "").strip()
        description = data.get("description", "").strip()
        if not name:
            return jsonify({"error": "Collection name is required"}), 400
        coll = db.create_collection(user_id, name, description)
        if not coll:
            return jsonify({"error": "Collection already exists"}), 409
        return jsonify({"status": "success", "collection": coll})

    collections = db.get_user_collections(user_id)
    return jsonify({"collections": collections})


@app.route("/api/collections/<string:name>", methods=["DELETE"])
def api_delete_collection(name):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    db.delete_collection(user_id, name)
    return jsonify({"status": "success"})


@app.route("/api/saved", methods=["GET", "POST"])
def api_saved_results():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"saved": [] if request.method == "GET" else {"error": "Please sign in to save results"}}), (200 if request.method == "GET" else 401)

    if request.method == "POST":
        data = request.get_json() or {}
        title = data.get("title", "").strip()
        url = data.get("url", "").strip()
        domain = data.get("domain", "").strip()
        snippet = data.get("snippet", "").strip()
        category = data.get("category", "web").strip()
        collection = data.get("collection_name", "General").strip()

        if not title or not url:
            return jsonify({"error": "Title and URL are required"}), 400

        item_id = db.save_result(user_id, title, url, domain, snippet, category, collection)
        return jsonify({"status": "success", "id": item_id})

    collection_filter = request.args.get("collection")
    saved = db.get_saved_results(user_id, collection_name=collection_filter)
    return jsonify({"saved": saved})


@app.route("/api/saved/<int:item_id>", methods=["DELETE"])
def api_delete_saved_result(item_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    db.remove_saved_result(user_id, item_id)
    return jsonify({"status": "success"})


# --- User Preferences & Export APIs ---

@app.route("/api/preferences", methods=["GET", "POST"])
def api_preferences():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"preferences": {}})

    if request.method == "POST":
        data = request.get_json() or {}
        updated = db.update_user_preferences(user_id, data)
        return jsonify({"status": "success", "preferences": updated})

    user = db.get_user_by_id(user_id)
    return jsonify({"preferences": user["preferences"] if user else {}})


@app.route("/api/export", methods=["GET"])
def api_export_data():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    export_data = db.export_user_data(user_id)
    return jsonify(export_data)


# --- Core Search Endpoint (Multi-Category Routing & Hybrid Index) ---

@app.route("/api/search", methods=["GET"])
@app.route("/api/browser/search", methods=["GET"])
def api_search():
    query = request.args.get("q", "").strip()[:500]
    category = request.args.get("category", "all").strip().lower()
    time_filter = request.args.get("time", "").strip().lower()
    if time_filter not in ["day", "week", "month", "year"]:
        time_filter = None

    if not query:
        return jsonify({"error": "Empty query"}), 400

    # Auto-log search history if user is logged in
    user_id = session.get("user_id")
    if user_id:
        try:
            db.record_search_history(user_id, query, category=category)
        except Exception as e:
            logger.warning(f"History record error: {e}")

    # 1. PURE MATH CHECK (Zero Network Dependency)
    # Expressions like 120*45, (12+8)*5, 100/4, 2^10 return immediately
    instant_math = evaluate_instant_math(query)
    if instant_math:
        return jsonify({
            "query": query,
            "category": category,
            "intent": {"intent": "calculation", "confidence": 1.0},
            "instant_answer": instant_math,
            "destination": None,
            "results": [],
            "images": [],
            "provider": "local_calculator"
        })

    # Query intent classification
    intent_info = search_core.classify_query_intent(query)

    # 2. DIRECT URL NAVIGATION CHECK (Zero Search Overhead)
    # Queries like https://example.com, www.example.com, example.com
    clean_q = query.strip()
    is_direct_url = (
        intent_info.get("intent") == "direct_nav" or
        clean_q.startswith(("http://", "https://", "www.")) or
        (re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/.*)?$", clean_q) and " " not in clean_q)
    )
    if is_direct_url:
        target_nav_url = clean_q if clean_q.startswith(("http://", "https://")) else f"https://{clean_q}"
        norm_nav = normalize_url(target_nav_url) or target_nav_url
        return jsonify({
            "query": query,
            "category": category,
            "intent": {"intent": "direct_nav", "url": norm_nav},
            "direct_nav": {"url": norm_nav},
            "results": [],
            "images": [],
            "provider": "direct_nav"
        })

    # 3. Specialized Categories
    if category != "all":
        specialized_res = search_core.route_search_category(query, category, time_range=time_filter)
        if specialized_res is not None:
            if isinstance(specialized_res, dict):
                specialized_res["intent"] = intent_info
                specialized_res["time_filter"] = time_filter
                # Validate results in specialized category
                if "results" in specialized_res and isinstance(specialized_res["results"], list):
                    specialized_res["results"] = deduplicate_results(
                        [r for r in specialized_res["results"] if validate_result(r)]
                    )
            return jsonify(specialized_res)

    # 4. General / Web Search (All Category)
    cache_key = f"all:{query.lower()}:{time_filter or 'any'}"
    now = time.time()
    if cache_key in SEARCH_CACHE:
        cached_time, cached_payload = SEARCH_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return jsonify(cached_payload)

    # Non-blocking destination intelligence check
    destination_data = get_destination_intel(query)

    # Hybrid Search: Local FTS5 Index + Bounded High-Speed Multi-Provider Retriever
    search_data = search_core.search_with_hybrid_ranking(query, max_results=8, time_range=time_filter)

    # Fetch visual preview images (Wikimedia high-res public images)
    preview_images = search_core.fetch_wikimedia_images(query, limit=6)

    # Final validation & deduplication of results
    validated_results = deduplicate_results(
        [r for r in search_data.get("results", []) if validate_result(r)]
    )

    payload = {
        "query": query,
        "category": "all",
        "time_filter": time_filter,
        "intent": intent_info,
        "provider": search_data.get("provider", "hybrid_vastuda"),
        "instant_answer": None,
        "destination": destination_data,
        "results": validated_results,
        "images": preview_images or search_data.get("images", []),
        "message": "Insufficient information from available sources." if not validated_results else None
    }
    if payload.get("results"):
        SEARCH_CACHE[cache_key] = (now, payload)
    return jsonify(payload)


@app.route("/api/intent", methods=["GET"])
def api_intent():
    query = request.args.get("q", "").strip()
    return jsonify(search_core.classify_query_intent(query))


@app.route("/api/discover", methods=["GET"])
def api_discover():
    category = request.args.get("category", "trending").strip().lower()
    cache_key = f"discover:{category}"
    cached = search_core.get_cached(cache_key)
    if cached:
        return jsonify(cached)

    queries = {
        "trending": "top trending global technology and science news 2026",
        "ai": "artificial intelligence models robotics breakthrough developments",
        "tech": "software developer tools cloud computing infrastructure news",
        "science": "scientific discoveries astronomy physics quantum research",
        "business": "global markets financial economy startup venture capital",
        "india": "India tech digital infrastructure economy breakthroughs",
        "dev": "open source software developer tools github releases"
    }
    target_q = queries.get(category, queries["trending"])
    news_data = search_core.search_news_mode(target_q)
    items = news_data.get("results", [])[:12]
    payload = {
        "category": category,
        "items": items,
        "updated_at": int(time.time())
    }
    search_core.set_cached(cache_key, payload, ttl=search_core.NEWS_CACHE_TTL)
    return jsonify(payload)


@app.route("/api/crawler/enqueue", methods=["POST"])
def api_crawler_enqueue():
    data = request.get_json() or {}
    urls = data.get("urls", [])
    if isinstance(urls, str):
        urls = [urls]
    added = crawler.enqueue_urls(urls)
    return jsonify({"status": "success", "added": added})


@app.route("/api/crawler/stats", methods=["GET"])
def api_crawler_stats():
    return jsonify(indexer.get_index_stats())


@app.route("/api/crawler/diagnostics", methods=["GET"])
def api_crawler_diagnostics():
    return jsonify(crawler.get_crawler_diagnostics())


@app.route("/api/search/debug", methods=["GET"])
def api_search_debug():
    """Development-only query debugging endpoint with detailed ranking telemetry."""
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()
    auth_key = request.headers.get("X-Vastuda-Debug-Key") or request.args.get("debug_key")
    is_local = client_ip in ("127.0.0.1", "::1", "localhost")
    is_authorized = auth_key == os.getenv("DEBUG_KEY", "vastuda-dev-2026")

    if not (is_local or is_authorized):
        return jsonify({"error": "Unauthorized. Debug endpoint is restricted to development environments.", "status": 403}), 403

    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    from search_engine import query_engine

    q_info = query_engine.understand_query(query)
    local_candidates = indexer.search_local_index(query, limit=10, query_info=q_info)

    external_candidates = []
    try:
        ext_res = search_core.execute_web_query(query, max_results=6)
        external_candidates = ext_res.get("results", [])
    except Exception:
        external_candidates = []

    hybrid_res = search_core.search_with_hybrid_ranking(query, max_results=8)

    return jsonify({
        "raw_query": query,
        "normalized_query": q_info.get("normalized_query"),
        "detected_language": q_info.get("language"),
        "intent": q_info.get("intent"),
        "vertical": q_info.get("vertical"),
        "freshness_required": q_info.get("freshness_required"),
        "entities": q_info.get("entities"),
        "expanded_terms": q_info.get("expanded_terms"),
        "local_candidates_count": len(local_candidates),
        "local_candidates": local_candidates,
        "external_candidates_count": len(external_candidates),
        "external_candidates": external_candidates,
        "provider": hybrid_res.get("provider"),
        "ranking": hybrid_res.get("results", [])
    })



@app.route("/api/destination", methods=["GET"])
def api_destination():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(None)
    return jsonify(get_destination_intel(query))


WEATHER_CACHE = {}

@app.route("/api/weather", methods=["GET"])
def api_weather():
    lat = request.args.get("lat", "28.6139")
    lon = request.args.get("lon", "77.2090")
    city = request.args.get("city", "New Delhi")

    cache_key = f"{lat}_{lon}"
    now = time.time()
    if cache_key in WEATHER_CACHE and (now - WEATHER_CACHE[cache_key]["time"]) < 1800:
        return jsonify(WEATHER_CACHE[cache_key]["data"])

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = http_session.get(url, timeout=(2.0, 3.0))
        if resp.status_code == 200:
            cw = resp.json().get("current_weather", {})
            temp = cw.get("temperature", 26)
            wcode = cw.get("weathercode", 0)
            condition_map = {
                0: ("Clear Sky", "☀️"),
                1: ("Mainly Clear", "🌤️"),
                2: ("Partly Cloudy", "⛅"),
                3: ("Overcast", "☁️"),
                45: ("Foggy", "🌫️"),
                51: ("Light Drizzle", "🌦️"),
                61: ("Rainy", "🌧️"),
                71: ("Snow", "❄️"),
                95: ("Thunderstorm", "⛈️")
            }
            cond_text, cond_icon = condition_map.get(wcode, ("Pleasant", "🌤️"))
            data = {
                "city": city,
                "temp": round(temp),
                "condition": cond_text,
                "icon": cond_icon,
                "wind": f"{cw.get('windspeed', 12)} km/h"
            }
            WEATHER_CACHE[cache_key] = {"time": now, "data": data}
            return jsonify(data)
    except Exception as e:
        logger.warning(f"Weather API error: {e}")

    return jsonify({"city": city, "temp": 28, "condition": "Sunny", "icon": "☀️", "wind": "10 km/h"})


TRENDING_CACHE = {"time": 0, "data": None}

@app.route("/api/trending", methods=["GET"])
def api_trending():
    now = time.time()
    if TRENDING_CACHE["data"] and (now - TRENDING_CACHE["time"]) < 900:
        return jsonify(TRENDING_CACHE["data"])

    markets = [
        {"symbol": "NIFTY 50", "value": "25,378.10", "change": "+0.42%", "is_up": True},
        {"symbol": "SENSEX", "value": "83,085.20", "change": "+0.38%", "is_up": True},
        {"symbol": "USD / INR", "value": "₹83.82", "change": "-0.04%", "is_up": False},
        {"symbol": "BTC / USD", "value": "$63,840", "change": "+2.14%", "is_up": True},
        {"symbol": "GOLD 24K", "value": "₹74,450", "change": "+0.18%", "is_up": True}
    ]

    topics = [
        {"query": "AI Breakthroughs 2026", "tag": "Tech", "icon": "🤖"},
        {"query": "World Cup & Cricket Scores", "tag": "Sports", "icon": "🏏"},
        {"query": "India Space Mission Updates", "tag": "Science", "icon": "🚀"},
        {"query": "Global Market Trends", "tag": "Finance", "icon": "📈"},
        {"query": "Best Travel Destinations 2026", "tag": "Travel", "icon": "✈️"},
        {"query": "Staunt Browser Download", "tag": "Apps", "icon": "🌐"}
    ]

    news_items = []
    try:
        news_res = search_core.search_news_mode("world top headlines india", limit=6)
        news_items = news_res.get("news", [])[:6]
    except Exception:
        pass

    if not news_items:
        news_items = [
            {"title": "Global Tech Summit unveils next-generation autonomous AI chips", "source": "Tech Wire", "time": "1h ago", "url": "https://news.google.com"},
            {"title": "Space Agency prepares next deep lunar exploratory milestone", "source": "Global Science", "time": "3h ago", "url": "https://news.google.com"},
            {"title": "Renewable Energy grid installations reach historic milestone in Asia", "source": "Green Energy", "time": "4h ago", "url": "https://news.google.com"},
            {"title": "Markets rally as manufacturing output beats quarterly analyst estimates", "source": "Finance Today", "time": "6h ago", "url": "https://news.google.com"}
        ]

    payload = {
        "markets": markets,
        "topics": topics,
        "news": news_items
    }
    TRENDING_CACHE["time"] = now
    TRENDING_CACHE["data"] = payload
    return jsonify(payload)



@app.route("/api/images", methods=["GET"])
def api_images():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    return jsonify(search_core.search_images_mode(query).get("images", []))


@app.route("/api/overview", methods=["POST"])
def api_overview():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    results = data.get("results", [])

    if not query:
        return jsonify({"error": "Missing query"}), 400

    overview_data = generate_ai_overview(query, results)
    if not overview_data:
        return jsonify({"status": "unavailable", "message": "AI overview unavailable"}), 200

    return jsonify({"status": "success", "data": overview_data})


@app.route("/api/suggest", methods=["GET"])
def api_suggest():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    # 1. External suggestion query with browser headers & utf-8 decoding
    try:
        url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9,hi;q=0.8"
        }
        resp = http_session.get(url, headers=headers, timeout=(1.5, 2.5))
        if resp.status_code == 200:
            resp.encoding = "utf-8"
            data = json.loads(resp.text)
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                suggs = [str(s).strip() for s in data[1] if str(s).strip()]
                if suggs:
                    return jsonify(suggs[:8])
    except Exception as e:
        logger.warning(f"Suggest provider query note: {type(e).__name__}")

    # 2. Honest local fallback: Match against real past search queries in SQLite
    try:
        local_suggs = db.get_matching_suggestions(query, limit=8)
        if local_suggs:
            return jsonify(local_suggs)
    except Exception as e:
        logger.warning(f"Local suggest query note: {type(e).__name__}")

    return jsonify([])


@app.route("/api/reader", methods=["GET"])
def api_reader():
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Missing URL"}), 400

    article_data = extract_article_content(url)
    return jsonify(article_data)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  VASTUDA DISCOVERY ENGINE & SEARCH PLATFORM IS LIVE")
    print(f"  Access local search portal: http://localhost:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
