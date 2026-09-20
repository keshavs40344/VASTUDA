"""
VASTUDA 5.4 — Deterministic Vocabulary-Aware Spell Checker
Features:
- Damerau-Levenshtein edit-distance spell correction (distance <= 2)
- Seeded from real SQLite index vocabulary + curated technical dictionary
- Strict safety rules: never mutates code symbols (c++, node.js), operators (site:, filetype:),
  URLs, domain names, technical identifiers, or quoted phrases.
- Returns machine-readable correction output with confidence scores.
"""

import os
import re
import time
import logging
from search_engine import db, indexer

logger = logging.getLogger("VASTUDA_SpellChecker")

# Curated high-confidence technical & programming dictionary
CORE_TECH_TERMS = {
    # Languages & Runtimes
    "python": 1000, "javascript": 1000, "typescript": 900, "rust": 900, "golang": 800,
    "java": 900, "kotlin": 700, "swift": 700, "ruby": 700, "php": 700,
    "perl": 600, "scala": 600, "elixir": 600, "erlang": 500, "clojure": 500,
    "haskell": 600, "lua": 600, "dart": 600, "bash": 800, "shell": 800,

    # Databases & Storage
    "sqlite": 1000, "postgres": 900, "postgresql": 900, "mysql": 900, "mongodb": 800,
    "redis": 900, "mariadb": 700, "cassandra": 600, "elasticsearch": 700,

    # Frameworks & Libraries
    "react": 1000, "vue": 800, "angular": 800, "svelte": 700, "django": 900,
    "flask": 900, "fastapi": 900, "express": 800, "nextjs": 800, "nuxt": 600,
    "framework": 950, "frameworks": 850,
    "spring": 800, "laravel": 800, "rails": 800, "pytorch": 900, "tensorflow": 900,
    "pandas": 900, "numpy": 900, "scipy": 800, "scikit-learn": 800,

    # DevOps, Tools & Systems
    "docker": 1000, "kubernetes": 900, "git": 1000, "github": 1000, "gitlab": 800,
    "linux": 1000, "ubuntu": 900, "debian": 800, "arch": 700, "fedora": 700,
    "nginx": 900, "apache": 800, "webpack": 700, "vite": 800, "ansible": 700,
    "terraform": 800, "jenkins": 700, "prometheus": 700, "grafana": 700,

    # Concepts & CS Fundamentals
    "algorithm": 900, "database": 900, "tutorial": 1000, "documentation": 1000,
    "asynchronous": 800, "recursion": 800, "multithreading": 800, "concurrency": 800,
    "compiler": 800, "interpreter": 800, "encryption": 800, "cryptography": 800,
    "blockchain": 800, "microservices": 800, "artificial": 900, "intelligence": 900,
    "machine": 900, "learning": 900, "quantum": 900, "computing": 900,

    # Common English terms
    "complete": 800, "beginner": 900, "advanced": 800, "guide": 900, "overview": 800,
    "reference": 800, "function": 900, "variable": 900, "structure": 800,
    "programming": 1000, "development": 900, "software": 900, "engineering": 900
}

# Immutable technical tokens that MUST NEVER be altered by the spell checker
PROTECTED_TOKENS = {
    "c++", "c#", "f#", "node.js", "vue.js", "next.js", "react.js",
    "d3.js", "three.js", ".net", "asp.net", "g++", "gcc", "clang",
    "sha256", "md5", "utf-8", "utf-16", "ascii", "ipv4", "ipv6",
    "tcp/ip", "http", "https", "grpc", "graphql", "rest", "api",
    "__init__", "stdout", "stdin", "stderr", "npm", "pip", "cargo",
    "sql", "nosql", "fts5", "wal", "json", "yaml", "xml", "csv"
}

_VOCABULARY_CACHE = None
_VOCAB_LAST_LOADED = 0


def get_combined_vocabulary() -> dict:
    """Build or retrieve frequency-weighted vocabulary combining curated terms and SQLite index tokens."""
    global _VOCABULARY_CACHE, _VOCAB_LAST_LOADED
    now = time.time()
    if _VOCABULARY_CACHE is not None and (now - _VOCAB_LAST_LOADED < 300):
        return _VOCABULARY_CACHE

    combined = dict(CORE_TECH_TERMS)
    try:
        index_vocab = indexer.get_index_vocabulary(min_freq=1)
        for term, freq in index_vocab.items():
            t_clean = term.lower()
            if len(t_clean) >= 3 and not re.match(r'^\d+$', t_clean):
                combined[t_clean] = combined.get(t_clean, 0) + (freq * 10)
    except Exception as e:
        logger.warning(f"Error loading index vocabulary for spell-checker: {e}")

    _VOCABULARY_CACHE = combined
    _VOCAB_LAST_LOADED = now
    return combined


def damerau_levenshtein(s1: str, s2: str) -> int:
    """Compute Damerau-Levenshtein distance (insert, delete, substitute, transpose)."""
    d = {}
    len1 = len(s1)
    len2 = len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1

    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,       # deletion
                d[(i, j - 1)] + 1,       # insertion
                d[(i - 1, j - 1)] + cost # substitution
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + cost) # transposition

    return d[(len1 - 1, len2 - 1)]


def find_best_candidate(word: str, vocabulary: dict) -> tuple:
    """Find the highest-frequency vocabulary term within edit distance <= 2. Returns (candidate, distance)."""
    w_lower = word.lower()
    if w_lower in vocabulary:
        return w_lower, 0

    best_cand = None
    min_dist = 3
    best_freq = -1

    len_w = len(w_lower)
    for term, freq in vocabulary.items():
        # Optimization: length difference must be <= 2
        if abs(len(term) - len_w) > 2:
            continue
        # Term must share at least 1 character if short, or first letter if length >= 4
        if len_w >= 4 and term[0] != w_lower[0] and term[1] != w_lower[0]:
            continue

        dist = damerau_levenshtein(w_lower, term)
        if dist <= 2:
            if dist < min_dist:
                min_dist = dist
                best_cand = term
                best_freq = freq
            elif dist == min_dist and freq > best_freq:
                best_cand = term
                best_freq = freq

    return (best_cand, min_dist) if best_cand else (w_lower, 0)


def correct_query(raw_query: str) -> dict:
    """
    Safely evaluate query for spell corrections:
    - Never changes protected symbols, URLs, domains, site: operators, or quoted phrases.
    - Suggests corrections only when confidence is high.
    Returns:
    {
      "original_query": str,
      "corrected_query": str,
      "confidence": float,
      "has_correction": bool
    }
    """
    original = (raw_query or "").strip()
    if not original:
        return {"original_query": "", "corrected_query": "", "confidence": 1.0, "has_correction": False}

    # Safety: Skip if direct URL, domain, site restriction, or math calculation
    lower_q = original.lower()
    if (
        lower_q.startswith(("http://", "https://", "www.")) or
        re.match(r"^[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(/.*)?$", lower_q) or
        "site:" in lower_q or
        "filetype:" in lower_q or
        re.match(r"^[\d\s\+\-\*\/\(\)\.\%\*]+$", lower_q) or
        re.search(r"^(?:sqrt|square\s*root)\s*\(", lower_q)
    ):
        return {"original_query": original, "corrected_query": original, "confidence": 1.0, "has_correction": False}

    # Safety: Check if entire query is in protected tokens
    if lower_q in PROTECTED_TOKENS:
        return {"original_query": original, "corrected_query": original, "confidence": 1.0, "has_correction": False}

    # Check for Devanagari Hindi (do not alter Hindi words with English spell checker)
    if re.search(r'[\u0900-\u097F]', original):
        return {"original_query": original, "corrected_query": original, "confidence": 1.0, "has_correction": False}

    # Preserve exact quoted phrases
    quoted_parts = re.findall(r'["“]([^"”]+)["”]', original)
    if quoted_parts:
        return {"original_query": original, "corrected_query": original, "confidence": 1.0, "has_correction": False}

    vocab = get_combined_vocabulary()
    words = original.split()
    corrected_words = []
    total_dist = 0
    words_changed = 0

    for w in words:
        w_clean = re.sub(r'^[^\w\+\#\.]+|[^\w\+\#\.]+$', '', w)
        w_lower = w_clean.lower()

        # Check protected tokens
        if not w_clean or w_lower in PROTECTED_TOKENS or "." in w_lower or ":" in w_lower or len(w_clean) <= 2:
            corrected_words.append(w)
            continue

        cand, dist = find_best_candidate(w_lower, vocab)
        if dist > 0 and cand != w_lower:
            # Preserve original casing capitalization if needed
            new_word = cand.title() if w[0].isupper() else cand
            corrected_words.append(new_word)
            total_dist += dist
            words_changed += 1
        else:
            corrected_words.append(w)

    corrected_query = " ".join(corrected_words)
    has_correction = words_changed > 0 and corrected_query.lower() != original.lower()

    # Calculate confidence based on edit distance and word length
    confidence = 1.0
    if has_correction:
        confidence = max(0.5, round(1.0 - (total_dist * 0.15), 2))

    return {
        "original_query": original,
        "corrected_query": corrected_query,
        "confidence": confidence,
        "has_correction": has_correction
    }


def correct_word(word: str) -> str:
    """Helper to correct a single word or token."""
    res = correct_query(word)
    return res.get("corrected_query", word)

