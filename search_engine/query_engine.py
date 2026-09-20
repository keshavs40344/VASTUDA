"""
VASTUDA 5.0 — Deterministic Query Understanding & Normalization Engine
Provides rich structured query analysis:
- Language detection (English, Hindi, Hinglish)
- Query normalization & transliteration variant expansion
- Fine-grained intent classification (13 intent classes)
- Entity & keyword extraction
- Freshness requirement detection
- Vertical routing
"""

import re
import unicodedata
import urllib.parse


# Common Hinglish stopwords & particles
HINGLISH_MARKERS = {
    "kaise", "seekhe", "sikhe", "sikhen", "kya", "hota", "hoti", "hote",
    "hai", "hain", "fayde", "nuksan", "banaye", "banae", "kare", "karein",
    "kese", "ke", "ki", "ko", "mein", "me", "se", "aur", "ka", "ye",
    "wo", "kyu", "kyun", "nahi", "kaun", "kab", "kahan", "kitna", "kitni"
}

# Transliteration & common variation normalization dictionary
HINGLISH_SYNONYMS = {
    "seekhe": "sikhe",
    "sikhen": "sikhe",
    "banae": "banaye",
    "banayein": "banaye",
    "kese": "kaise",
    "karein": "kare",
    "kyun": "kyu",
    "chahiye": "chahiye",
    "phn": "phone",
    "prog": "programming",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "doc": "document",
    "docs": "documents"
}

# Freshness triggering patterns (when latest/breaking news is requested)
FRESHNESS_TRIGGERS = [
    "latest", "today", "breaking", "recent", "current", "now", "update",
    "updates", "2026", "2025", "news", "live", "headlines", "this week",
    "this month", "right now"
]

# Intent classification rules
INTENT_RULES = {
    "calculation": [
        r"^[\d\s\+\-\*\/\(\)\.\%\^]+$"
    ],
    "direct_nav": [
        r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$",
        r"^(localhost|127\.0\.0\.1)(:\d+)?(\/.*)?$"
    ],
    "academic": [
        "arxiv", "paper", "research", "study", "journal", "academic",
        "methodology", "meta-analysis", "clinical trial", "dissertation",
        "thesis", "peer-reviewed", "nature review", "ieee", "springer"
    ],
    "code": [
        "github", "python", "javascript", "react", "golang", "c++", "rust",
        "function", "api", "docker", "npm", "pip", "sql", "bug", "syntax",
        "stackoverflow", "css", "html", "class", "method", "sdk", "regex",
        "tutorial", "documentation", "implementation", "algorithm"
    ],
    "news": [
        "news", "breaking", "today", "headlines", "election", "scandal",
        "war", "president", "minister", "parliament", "treaty", "market crash"
    ],
    "document": [
        "pdf", "whitepaper", "manual", "handbook", "filetype:pdf", "syllabus",
        "circular", "gazette", "ordinance", "form"
    ],
    "image": [
        "image", "images", "photo", "photos", "picture", "pictures",
        "wallpaper", "diagram", "chart", "infographic"
    ],
    "video": [
        "video", "videos", "youtube", "clip", "trailer", "movie", "song",
        "stream", "vimeo", "short film"
    ],
    "transactional": [
        "buy", "price", "discount", "under ₹", "under $", "deals", "amazon",
        "flipkart", "review", "order", "coupon", "cost", "cheap", "ticket"
    ],
    "local": [
        "near me", "in delhi", "in mumbai", "in bangalore", "restaurants in",
        "hospitals in", "hotels in", "weather in", "places to visit in"
    ],
    "navigational": [
        "login", "sign in", "official website", "portal", "homepage",
        "dashboard", "gov.in", ".edu", ".org", "w3schools", "wikipedia main page"
    ]
}


def detect_language(query: str) -> str:
    """
    Detect query language accurately:
    - 'hi' (Devanagari script)
    - 'hinglish' (Latin script with Hindi phonetic vocabulary)
    - 'en' (English default)
    """
    if not query:
        return "en"

    # Check for Devanagari Unicode block (0900–097F)
    if re.search(r"[\u0900-\u097F]", query):
        return "hi"

    # Check for Hinglish markers in Latin text
    tokens = set(re.sub(r"[^\w\s]", " ", query.lower()).split())
    if tokens & HINGLISH_MARKERS:
        return "hinglish"

    return "en"


def normalize_query_text(raw_query: str) -> dict:
    """
    Normalize query text:
    - NFKC Unicode normalization
    - Whitespace collapsing
    - Punctuation stripping for matching
    - Transliteration variant expansion
    """
    if not raw_query:
        return {"normalized": "", "tokens": [], "expanded_terms": []}

    # Unicode normalization
    norm = unicodedata.normalize("NFKC", raw_query)
    clean_whitespace = re.sub(r"\s+", " ", norm).strip()
    lower = clean_whitespace.lower()

    # Tokenization
    raw_tokens = re.sub(r"[^\w\s]", " ", lower).split()

    # Transliteration normalization
    normalized_tokens = [HINGLISH_SYNONYMS.get(t, t) for t in raw_tokens]

    # Expanded terms for multilingual search fallback
    expanded_terms = list(normalized_tokens)
    if "sikhe" in normalized_tokens or "seekhe" in raw_tokens:
        expanded_terms.extend(["tutorial", "learn", "course"])
    if "banaye" in normalized_tokens or "banae" in raw_tokens:
        expanded_terms.extend(["create", "build", "guide"])
    if "kya" in normalized_tokens and "hai" in normalized_tokens:
        expanded_terms.extend(["what is", "overview", "definition"])
    if "fayde" in normalized_tokens:
        expanded_terms.extend(["advantages", "benefits"])

    return {
        "raw": raw_query,
        "normalized": " ".join(normalized_tokens),
        "tokens": normalized_tokens,
        "expanded_terms": list(dict.fromkeys(expanded_terms))
    }


def extract_entities(query: str) -> list:
    """Extract named entities or key subject noun phrases from query."""
    clean = re.sub(r"[^\w\s]", " ", query).strip()
    words = clean.split()
    entities = []

    # Quoted terms
    quotes = re.findall(r'"([^"]+)"', query)
    entities.extend(quotes)

    # Capitalized multi-word phrases (proper nouns)
    caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
    entities.extend([c for c in caps if len(c) > 3 and c not in entities])

    # Common technical terms
    tech_terms = ["python", "javascript", "react", "vue", "docker", "kubernetes", "dns", "ai", "crispr", "sqlite", "nginx", "constitution"]
    for t in tech_terms:
        if re.search(rf"\b{t}\b", query, re.I) and t not in [e.lower() for e in entities]:
            entities.append(t.title())

    return list(dict.fromkeys(entities))


def understand_query(query: str) -> dict:
    """
    Core structured query understanding pipeline:
    Returns structured query model adhering to Search Quality 5.0 specifications.
    """
    raw_q = (query or "").strip()
    if not raw_q:
        return {
            "raw_query": "",
            "normalized_query": "",
            "language": "en",
            "intent": "informational",
            "entities": [],
            "freshness_required": False,
            "vertical": "all",
            "location": None
        }

    lang = detect_language(raw_q)
    norm_data = normalize_query_text(raw_q)
    norm_q = norm_data["normalized"]
    lower_raw = raw_q.lower()

    # 1. Calculation Intent Check
    clean_math = lower_raw.replace("x", "*").replace("×", "*").replace("÷", "/")
    if any(op in clean_math for op in "+-*/%^") and re.match(r"^[\d\s\+\-\*\/\(\)\.\%\^]+$", clean_math):
        return {
            "raw_query": raw_q,
            "normalized_query": norm_q,
            "language": lang,
            "intent": "calculation",
            "entities": [],
            "freshness_required": False,
            "vertical": "all",
            "location": None
        }

    # 2. Direct Navigation Check
    if (
        re.match(r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$", lower_raw) or
        lower_raw.startswith(("localhost", "127.0.0.1", "www.")) or
        (re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/.*)?$", lower_raw) and " " not in lower_raw)
    ):
        return {
            "raw_query": raw_q,
            "normalized_query": norm_q,
            "language": lang,
            "intent": "direct_nav",
            "entities": [raw_q],
            "freshness_required": False,
            "vertical": "web",
            "location": None
        }

    # 3. Freshness Requirement Detection
    freshness_required = any(
        re.search(rf"\b{re.escape(trigger)}\b", lower_raw)
        for trigger in FRESHNESS_TRIGGERS
    )

    # 4. Vertical & Intent Classification
    intent = "informational"
    vertical = "all"

    # Rule checks in priority order
    if any(k in lower_raw for k in ["news", "latest", "breaking", "headlines"]):
        intent = "news"
        vertical = "news"
    elif any(k in lower_raw for k in ["pdf", "whitepaper", "syllabus", "manual", "handbook"]) or "filetype:" in lower_raw:
        intent = "document"
        vertical = "documents"
    elif any(k in lower_raw.split() for k in ["paper", "research", "study", "journal", "academic", "arxiv"]):
        intent = "academic"
        vertical = "research"
    elif any(k in lower_raw for k in ["images", "image", "photos", "wallpaper", "picture"]):
        intent = "image"
        vertical = "images"
    elif any(k in lower_raw for k in ["video", "videos", "youtube", "clip", "trailer", "movie"]):
        intent = "video"
        vertical = "videos"
    elif any(k in lower_raw.split() for k in ["buy", "price", "discount", "under ₹", "under $", "deals"]):
        intent = "transactional"
        vertical = "all"
    elif any(k in lower_raw for k in ["near me", "weather in", "hotels in", "flights to", "places to visit"]):
        intent = "local"
        vertical = "all"
    elif any(k in lower_raw for k in ["github", "tutorial", "how to code", "function", "docker", "npm", "pip", "sql"]):
        intent = "code"
        vertical = "developer"
    elif any(k in lower_raw for k in ["login", "sign in", "portal", "official website"]):
        intent = "navigational"
        vertical = "all"

    # Entities
    entities = extract_entities(raw_q)

    return {
        "raw_query": raw_q,
        "normalized_query": norm_q,
        "expanded_terms": norm_data["expanded_terms"],
        "language": lang,
        "intent": intent,
        "entities": entities,
        "freshness_required": freshness_required,
        "vertical": vertical,
        "location": None
    }
