import os
import re
import json
import time
import logging
import urllib.parse
from flask import Flask, request, jsonify, render_template, send_from_directory, session
import requests
from dotenv import load_dotenv

import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Import database and search core modules
try:
    from search_engine import db
    from search_engine import search_core
except ImportError:
    import db
    import search_core


load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("VASTUDA_Server")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.getenv("SECRET_KEY", "vastuda-secret-session-key-2026-secure-ultra")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "qwen/qwen3.8-27b"

# High-speed connection pool
http_session = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=25, pool_maxsize=25, max_retries=1)
http_session.mount("https://", adapter)
http_session.mount("http://", adapter)

# In-memory search & destination caches
SEARCH_CACHE = {}
DESTINATION_CACHE = {}
CACHE_TTL = 900  # 15 minutes


def evaluate_instant_math(query):
    """Safely calculate simple arithmetic if query is a math expression."""
    clean = query.strip().replace("x", "*").replace("×", "*").replace("÷", "/")
    if re.match(r"^[\d\s\+\-\*\/\(\)\.\%]+$", clean) and any(op in clean for op in "+-*/%"):
        try:
            res = eval(clean, {"__builtins__": None}, {})
            if isinstance(res, (int, float)):
                return {"expression": query, "result": f"{res:,.4f}".rstrip("0").rstrip(".")}
        except Exception:
            pass
    return None


def get_destination_image(place_name):
    """Fetch high-res image from Wikipedia API with Wikimedia fallback."""
    try:
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=pageimages&format=json&piprop=original|thumbnail&pithumbsize=1000&titles={urllib.parse.quote(place_name)}"
        headers = {"User-Agent": "VASTUDA-SearchEngine/1.0 (https://vastuda.internal; dev@vastuda.internal)"}
        resp = http_session.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            pages = resp.json().get("query", {}).get("pages", {})
            for p in pages.values():
                thumb = p.get("thumbnail", {}).get("source") or p.get("original", {}).get("source")
                if thumb and not thumb.endswith(".svg.png"):
                    return thumb
    except Exception as e:
        logger.warning(f"Wikipedia pageimages error for {place_name}: {e}")

    # Fallback to search_core.fetch_wikimedia_images
    try:
        wiki_imgs = search_core.fetch_wikimedia_images(place_name, limit=2)
        if wiki_imgs and len(wiki_imgs) > 0:
            return wiki_imgs[0].get("url")
    except Exception:
        pass
    return None


def get_destination_intel(query):
    """Detect if query is a travel destination/city and return structured rich travel card data."""
    clean_q = query.strip()
    if len(clean_q) < 3 or len(clean_q.split()) > 5:
        return None

    cache_key = clean_q.lower()
    if cache_key in DESTINATION_CACHE:
        return DESTINATION_CACHE[cache_key]

    if not GROQ_API_KEY:
        return None

    try:
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

If NO (it is not a place, or it is technical/general knowledge/math/concept), output:
"is_destination": false"""

        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "You are a world-class travel intelligence engine. Return JSON strictly."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": 250
        }
        resp = http_session.post(url, headers=headers, json=payload, timeout=4)
        if resp.status_code == 200:
            parsed = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "{}")
            data = json.loads(parsed)
            if data.get("is_destination"):
                name = data.get("name", clean_q)
                img = get_destination_image(name) or get_destination_image(clean_q)
                data["image"] = img
                data["maps_url"] = f"https://www.google.com/maps/search/?api=1&query={urllib.parse.quote(name)}"
                data["flights_url"] = f"https://www.google.com/travel/flights?q=flights+to+{urllib.parse.quote(name)}"
                data["hotels_url"] = f"https://www.google.com/travel/hotels?q=hotels+in+{urllib.parse.quote(name)}"
                if img:
                    DESTINATION_CACHE[cache_key] = data
                return data
            else:
                DESTINATION_CACHE[cache_key] = None
                return None
    except Exception as e:
        logger.warning(f"Destination check error: {e}")
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
    """Generate synthesized AI answer with SQLite persistent cache and Zero-Token fallback."""
    if not results:
        return None

    # 1. Tier 1: Check Persistent SQLite Cache (0 Tokens, Instant Return)
    cached = db.get_cached_ai_overview(query)
    if cached:
        return cached

    # 2. Tier 2: Call Groq with Multi-Model Rotation (Fast Free Tier)
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
3. Do NOT write long paragraphs or over-explain. Keep it sharp and factual.
4. Cite sources using [1], [2].
5. End with "**Related:**" followed by 3 short comma-separated search terms."""

            # Try primary ultra-fast free model first, fallback to qwen
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
                            {"role": "system", "content": "You are VASTUDA AI. Provide ultra-concise, factual overviews without filler."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.2,
                        "max_tokens": 200
                    }
                    resp = http_session.post(url, headers=headers, json=payload, timeout=10)
                    if resp.status_code == 200:
                        content = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                        result = {
                            "overview": content,
                            "mode": "neural_llm",
                            "sources": [{"index": i, "title": r.get("title", ""), "url": r.get("url", ""), "domain": r.get("domain", "")} for i, r in enumerate(results[:5], 1)]
                        }
                        # Save permanently in SQLite cache
                        db.cache_ai_overview(query, result)
                        return result
                    elif resp.status_code == 429:
                        logger.warning(f"Groq {model_name} rate limited (429), trying next model...")
                        continue
                except Exception as model_err:
                    logger.warning(f"Groq {model_name} failed: {model_err}")
                    continue
        except Exception as e:
            logger.error(f"Error calling Groq overview: {e}")

    # 3. Tier 3: Zero-Token Extractive Fallback (Guarantees AI Overview ALWAYS Appears)
    logger.info("Using Zero-Token Extractive Synthesizer fallback")
    fallback = generate_extractive_overview(query, results)
    if fallback:
        db.cache_ai_overview(query, fallback)
    return fallback



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


# --- Core Search Endpoint (Multi-Category Routing) ---

@app.route("/api/search", methods=["GET"])
def api_search():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "all").strip().lower()

    if not query:
        return jsonify({"error": "Empty query"}), 400

    # Auto-log search history if user is logged in
    user_id = session.get("user_id")
    if user_id:
        try:
            db.record_search_history(user_id, query, category=category)
        except Exception as e:
            logger.warning(f"History record error: {e}")

    # 1. Specialized Categories
    if category != "all":
        specialized_res = search_core.route_search_category(query, category)
        if specialized_res is not None:
            return jsonify(specialized_res)

    # 2. General / Web Search (All Category)
    cache_key = f"all:{query.lower()}"
    now = time.time()
    if cache_key in SEARCH_CACHE:
        cached_time, cached_payload = SEARCH_CACHE[cache_key]
        if now - cached_time < CACHE_TTL:
            return jsonify(cached_payload)

    # Instant calculation check
    instant_math = evaluate_instant_math(query)

    # Destination Intelligence check
    destination_data = get_destination_intel(query)

    # Fast Web Search (Tavily with DDG fallback)
    search_data = search_core.execute_web_query(query, max_results=8, include_images=False)

    # Fetch visual preview images (Wikimedia high-res public images)
    preview_images = search_core.fetch_wikimedia_images(query, limit=6)

    payload = {
        "query": query,
        "category": "all",
        "provider": search_data.get("provider", "unknown"),
        "instant_answer": instant_math,
        "destination": destination_data,
        "results": search_data.get("results", []),
        "images": preview_images or search_data.get("images", [])
    }
    if payload.get("results"):
        SEARCH_CACHE[cache_key] = (now, payload)
    return jsonify(payload)



@app.route("/api/destination", methods=["GET"])
def api_destination():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify(None)
    return jsonify(get_destination_intel(query))


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

    if not query or not results:
        return jsonify({"error": "Missing query or results"}), 400

    overview_data = generate_ai_overview(query, results)
    if not overview_data:
        return jsonify({"status": "unavailable", "message": "AI overview unavailable"}), 200

    return jsonify({"status": "success", "data": overview_data})


@app.route("/api/suggest", methods=["GET"])
def api_suggest():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    try:
        url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={urllib.parse.quote(query)}"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            suggestions = resp.json()[1]
            return jsonify(suggestions[:8])
    except Exception:
        pass

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
