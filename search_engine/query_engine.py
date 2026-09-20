"""
VASTUDA 5.3 — Production-Grade Query Understanding, Normalization & Intent Engine

Implements safe, lossless query preprocessing:
- Preserves original_query alongside normalized_query
- Unicode NFKC normalization, whitespace canonicalization, punctuation handling
- Quoted phrase extraction ("..." and “...”)
- Repeated-character cleanup (>=3 repetitions reduced, preserving C++, C#, .NET)
- Site-restricted and filetype-restricted syntax parsing (site:domain.com, filetype:pdf)
- Lightweight deterministic intent classification (informational, navigational,
  transactional, url, domain, exact_phrase, news, technical, ambiguous)
- Multilingual detection (English, Hindi Devanagari, Hinglish phonetic)
- Preserves full backward compatibility with VASTUDA 5.0-5.2 query contracts
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

# Standard query stopwords that can be de-emphasized in ranking but preserved in tokens
BASIC_STOPWORDS = {
    "a", "an", "the", "in", "on", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before", "after",
    "above", "below", "to", "from", "up", "down", "is", "are", "was", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did"
}

# Domain TLD pattern
TLD_PATTERN = r"\.(com|org|net|gov|edu|mil|in|co|io|dev|ai|me|info|biz|uk|ca|de|jp|fr|au|app|site|tech|online)$"


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


def clean_repeated_characters(word: str) -> str:
    """
    Reduce accidental 3+ character repetitions (e.g., 'sooo' -> 'so', 'pythonnn' -> 'python'),
    while preserving standard double-letter words and special tokens.
    """
    if len(word) <= 2:
        return word
    if word in ("c++", "c#", ".net"):
        return word
    # Replace 3 or more consecutive identical consonants with 1
    word = re.sub(r'([bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ])\1{2,}', r'\1', word)
    # Replace 3 or more consecutive vowels with 2
    word = re.sub(r'([aeiouAEIOU])\1{2,}', r'\1\1', word)
    return word


def extract_quoted_phrases(text: str) -> tuple[list[str], str]:
    """
    Extract quoted phrases ("phrase" or “phrase”) from query text.
    Returns (list_of_phrases, remainder_text_without_quotes).
    """
    if not text:
        return [], ""

    # Match standard and curly quotes
    phrases = []
    pattern = r'["“]([^"”]+)["”]'
    for match in re.finditer(pattern, text):
        phrase = match.group(1).strip()
        if phrase:
            phrases.append(phrase)

    remainder = re.sub(pattern, " ", text)
    remainder = re.sub(r"\s+", " ", remainder).strip()
    return phrases, remainder


def normalize_query(raw_query: str) -> dict:
    """
    Safe query normalization layer (Phase 5.3):
    - Preserves original_query
    - Produces normalized_query
    - Extracts tokens and quoted phrases
    - Handles site: and filetype: operators
    - Detects URL / domain queries
    - Cleans whitespace, Unicode NFKC, repeated chars
    """
    original = (raw_query or "").strip()
    if not original:
        return {
            "original_query": "",
            "normalized_query": "",
            "tokens": [],
            "phrases": [],
            "query_type": "text",
            "site_restriction": None,
            "filetype_restriction": None,
            "raw": "",
            "normalized": "",
            "expanded_terms": []
        }

    # 1. Unicode NFKC Normalization
    norm_nfkc = unicodedata.normalize("NFKC", original)

    # 2. Extract Quoted Phrases
    phrases, without_quotes = extract_quoted_phrases(norm_nfkc)

    # 3. Extract site: and filetype: operators
    site_restriction = None
    site_match = re.search(r'\bsite:([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b', without_quotes, re.I)
    if site_match:
        site_restriction = site_match.group(1).lower()
        without_quotes = re.sub(r'\bsite:[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', " ", without_quotes, flags=re.I)

    filetype_restriction = None
    filetype_match = re.search(r'\bfiletype:([a-zA-Z0-9]+)\b', without_quotes, re.I)
    if filetype_match:
        filetype_restriction = filetype_match.group(1).lower()
        without_quotes = re.sub(r'\bfiletype:[a-zA-Z0-9]+\b', " ", without_quotes, flags=re.I)

    # 4. Whitespace and case normalization
    clean_text = re.sub(r"\s+", " ", without_quotes).strip()
    lower_text = clean_text.lower()

    # 5. Tokenization & Repeated character cleanup
    raw_tokens = re.sub(r"[^\w\s\+\#\.]", " ", lower_text).split()
    tokens = []
    for t in raw_tokens:
        clean_t = clean_repeated_characters(t)
        # Apply Hinglish transliteration if available
        norm_t = HINGLISH_SYNONYMS.get(clean_t, clean_t)
        if norm_t:
            tokens.append(norm_t)

    # Reconstruct clean normalized text
    norm_parts = list(tokens)
    if phrases:
        norm_parts.extend([p.lower() for p in phrases])
    normalized_query = " ".join(norm_parts).strip()

    # 6. Expanded terms for multilingual search fallback
    expanded_terms = list(tokens)
    if "sikhe" in tokens:
        expanded_terms.extend(["tutorial", "learn", "course"])
    if "banaye" in tokens:
        expanded_terms.extend(["create", "build", "guide"])
    if "kya" in tokens and "hai" in tokens:
        expanded_terms.extend(["what is", "overview", "definition"])
    if "fayde" in tokens:
        expanded_terms.extend(["advantages", "benefits"])

    # 7. Query Type Identification
    lower_orig = original.lower()
    query_type = "text"
    if site_restriction:
        query_type = "site_restricted"
    elif (
        original.startswith(("http://", "https://", "www.")) or
        re.match(r"^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(:\d+)?(\/.*)?$", lower_orig)
    ):
        query_type = "url"
    elif re.search(TLD_PATTERN, lower_orig) and " " not in lower_orig:
        query_type = "domain"
    elif phrases and not without_quotes.strip():
        query_type = "exact_phrase"

    return {
        "original_query": original,
        "normalized_query": normalized_query or original,
        "tokens": tokens,
        "phrases": phrases,
        "query_type": query_type,
        "site_restriction": site_restriction,
        "filetype_restriction": filetype_restriction,
        "language": detect_language(original),
        # Backward-compatible fields
        "raw": original,
        "normalized": normalized_query or original,
        "expanded_terms": list(dict.fromkeys(expanded_terms))
    }


def normalize_query_text(raw_query: str) -> dict:
    """Backward-compatible alias for normalize_query."""
    return normalize_query(raw_query)


def classify_intent_deterministic(query_norm: dict) -> tuple[str, str, dict]:
    """
    Lightweight, deterministic intent classifier (Phase 5.3):
    Returns (primary_intent, target_vertical, intent_signals).

    Possible intents:
    - informational
    - navigational
    - transactional
    - url
    - domain
    - exact_phrase
    - news
    - technical (code/docs)
    - ambiguous
    """
    orig = query_norm.get("original_query", "").lower()
    tokens = query_norm.get("tokens", [])
    q_type = query_norm.get("query_type", "text")
    tokens_set = set(tokens)

    signals = {}

    # 1. Calculation Check
    clean_math = orig.replace("x", "*").replace("×", "*").replace("÷", "/")
    if any(op in clean_math for op in "+-*/%^") and re.match(r"^[\d\s\+\-\*\/\(\)\.\%\^]+$", clean_math):
        signals["math_expression"] = 1.0
        return "calculation", "all", signals

    # 2. URL / Domain
    if q_type == "url":
        signals["url_structure"] = 1.0
        return "url", "web", signals
    if q_type == "domain":
        signals["domain_pattern"] = 1.0
        return "domain", "web", signals
    if q_type == "exact_phrase":
        signals["quoted_exact"] = 1.0
        return "exact_phrase", "all", signals

    # 3. Transactional / Commercial
    commercial_terms = {"buy", "price", "discount", "under", "cost", "cheap", "order", "coupon", "deal", "deals"}
    if tokens_set & commercial_terms or any(curr in orig for curr in ["₹", "$", "rs", "inr"]):
        signals["commercial_terms"] = 0.9
        return "transactional", "all", signals

    # 4. News / Current
    news_terms = {"news", "breaking", "today", "headlines", "live", "election", "scandal", "war", "announced"}
    if tokens_set & news_terms or any(f in orig for f in ["latest updates", "this week", "2026 news"]):
        signals["news_terms"] = 0.95
        return "news", "news", signals

    # 5. Documents
    doc_terms = {"pdf", "whitepaper", "syllabus", "manual", "handbook", "ordinance", "circular", "form"}
    if tokens_set & doc_terms or query_norm.get("filetype_restriction") == "pdf":
        signals["document_extension"] = 0.95
        return "document", "documents", signals

    # 6. Technical / Code
    tech_terms = {
        "python", "javascript", "react", "golang", "c++", "rust", "function", "api",
        "docker", "npm", "pip", "sql", "bug", "syntax", "stackoverflow", "css", "html",
        "class", "method", "sdk", "regex", "tutorial", "algorithm", "git", "sqlite",
        "compiler", "recursion", "array", "pointer", "stack", "queue", "big-o"
    }
    if tokens_set & tech_terms or any(prefix in orig for prefix in ["how to code", "implement in", "example of"]):
        signals["technical_terms"] = 0.9
        return "technical", "developer", signals

    # 7. Academic / Research
    academic_terms = {"paper", "research", "study", "journal", "academic", "arxiv", "theorem", "hypothesis"}
    if tokens_set & academic_terms:
        signals["academic_terms"] = 0.9
        return "academic", "research", signals

    # 8. Navigational
    navigational_terms = {"login", "signin", "portal", "official", "website", "homepage", "dashboard"}
    if tokens_set & navigational_terms or any(orig.endswith(f" {brand}") for brand in ["login", "portal", "official site"]):
        signals["navigational_terms"] = 0.85
        return "navigational", "all", signals

    # 9. Media (Image / Video)
    if tokens_set & {"image", "images", "photo", "photos", "wallpaper", "picture", "pictures"}:
        signals["image_terms"] = 0.9
        return "image", "images", signals
    if tokens_set & {"video", "videos", "youtube", "clip", "trailer", "movie"}:
        signals["video_terms"] = 0.9
        return "video", "videos", signals

    # 10. Ambiguous / Informational
    if len(tokens) <= 1 and not query_norm.get("phrases"):
        signals["short_single_token"] = 0.5
        return "ambiguous", "all", signals

    signals["default_informational"] = 0.8
    return "informational", "all", signals


def extract_entities(query: str) -> list:
    """Extract named entities, quoted terms, and technical key subject terms."""
    if not query:
        return []

    entities = []

    # Quoted terms
    quotes = re.findall(r'["“]([^"”]+)["”]', query)
    entities.extend(quotes)

    # Capitalized multi-word phrases (proper nouns)
    caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
    entities.extend([c for c in caps if len(c) > 3 and c not in entities])

    # Common technical terms
    tech_terms = [
        "python", "javascript", "react", "vue", "docker", "kubernetes", "dns",
        "ai", "crispr", "sqlite", "nginx", "constitution", "git", "linux", "html", "css"
    ]
    for t in tech_terms:
        if re.search(rf"\b{t}\b", query, re.I) and t.title() not in entities:
            entities.append(t.title())

    return list(dict.fromkeys(entities))


def understand_query(query: str) -> dict:
    """
    Core structured query understanding pipeline (Phase 5.3):
    Maintains full backward compatibility while adding rich deterministic signals.
    """
    raw_q = (query or "").strip()
    if not raw_q:
        return {
            "original_query": "",
            "normalized_query": "",
            "tokens": [],
            "phrases": [],
            "query_type": "text",
            "language": "en",
            "intent": "informational",
            "intent_signals": {},
            "entities": [],
            "freshness_required": False,
            "vertical": "all",
            "location": None,
            "raw_query": "",
            "expanded_terms": []
        }

    lang = detect_language(raw_q)
    norm = normalize_query(raw_q)
    intent, vertical, intent_signals = classify_intent_deterministic(norm)

    # Freshness requirement detection
    lower_raw = raw_q.lower()
    freshness_required = any(
        re.search(rf"\b{re.escape(trigger)}\b", lower_raw)
        for trigger in FRESHNESS_TRIGGERS
    )

    entities = extract_entities(raw_q)

    # Map technical intent to code for backward compatibility with search_core
    compat_intent = "code" if intent == "technical" else ("direct_nav" if intent in ("url", "domain") else intent)

    return {
        # New 5.3 structured attributes
        "original_query": norm["original_query"],
        "normalized_query": norm["normalized_query"],
        "tokens": norm["tokens"],
        "phrases": norm["phrases"],
        "query_type": norm["query_type"],
        "site_restriction": norm["site_restriction"],
        "filetype_restriction": norm["filetype_restriction"],
        "intent_signals": intent_signals,

        # Backward-compatible 5.0-5.2 fields
        "raw_query": raw_q,
        "expanded_terms": norm["expanded_terms"],
        "language": lang,
        "intent": compat_intent,
        "entities": entities,
        "freshness_required": freshness_required,
        "vertical": vertical,
        "location": None
    }
