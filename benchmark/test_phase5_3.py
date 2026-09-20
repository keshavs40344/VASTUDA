#!/usr/bin/env python3
"""
VASTUDA 5.3 — Comprehensive 25 Automated Tests for Ranking and Search Quality
Tests the actual ranking functions, query normalization, URL validation,
diversity damping, debug modes, and server contracts.
"""

import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from search_engine import indexer
from search_engine import query_engine
from search_engine import search_validator
from search_engine import search_core
from search_engine import server


class TestPhase53SearchQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = server.app.test_client()

    # 1. Exact match in title ranks higher than body-only match.
    def test_01_exact_title_match_ranks_higher_than_body_only(self):
        query = "python tutorial"
        q_info = query_engine.understand_query(query)
        doc_title = {
            "title": "Python Tutorial - Complete Beginner Guide",
            "body_text": "Here is an overview of programming concepts.",
            "headings": "Intro",
            "domain": "docs.example.org",
            "url": "https://docs.example.org/python",
            "language": "en"
        }
        doc_body = {
            "title": "General Programming Notes",
            "body_text": "In this guide we cover python tutorial steps for beginners.",
            "headings": "Intro",
            "domain": "docs.example.org",
            "url": "https://docs.example.org/notes",
            "language": "en"
        }
        score_title, b_title = indexer.compute_relevance_score(doc_title, query, query_info=q_info)
        score_body, b_body = indexer.compute_relevance_score(doc_body, query, query_info=q_info)
        self.assertGreater(score_title, score_body)
        self.assertGreater(b_title["title_boost"], b_body["title_boost"])

    # 2. Quoted phrase in body ranks higher than scattered token matches.
    def test_02_quoted_phrase_ranks_higher_than_scattered_tokens(self):
        query = '"machine learning models"'
        q_info = query_engine.understand_query(query)
        doc_quoted = {
            "title": "AI Documentation",
            "body_text": "We evaluate deep neural networks and machine learning models for production deployments.",
            "headings": "Overview",
            "domain": "ai.example.org",
            "url": "https://ai.example.org/models",
            "language": "en"
        }
        doc_scattered = {
            "title": "AI Documentation",
            "body_text": "We provide machine systems that support automated learning across different statistical models.",
            "headings": "Overview",
            "domain": "ai.example.org",
            "url": "https://ai.example.org/scattered",
            "language": "en"
        }
        score_quoted, b_quoted = indexer.compute_relevance_score(doc_quoted, query, query_info=q_info)
        score_scattered, b_scattered = indexer.compute_relevance_score(doc_scattered, query, query_info=q_info)
        self.assertGreater(score_quoted, score_scattered)
        self.assertGreater(b_quoted["phrase_boost"], b_scattered["phrase_boost"])

    # 3. Official/canonical doc domain ranks higher than unknown domain with identical token count.
    def test_03_canonical_doc_domain_ranks_higher_than_unknown(self):
        query = "python asyncio documentation"
        q_info = query_engine.understand_query(query)
        doc_official = {
            "title": "asyncio - Asynchronous I/O",
            "body_text": "Python asyncio documentation reference and event loop implementation details.",
            "headings": "Documentation",
            "domain": "python.org",
            "url": "https://python.org/doc/asyncio",
            "source_type": "documentation",
            "language": "en"
        }
        doc_unknown = {
            "title": "asyncio - Asynchronous I/O",
            "body_text": "Python asyncio documentation reference and event loop implementation details.",
            "headings": "Documentation",
            "domain": "random-blog-1234.net",
            "url": "https://random-blog-1234.net/asyncio",
            "source_type": "web",
            "language": "en"
        }
        score_off, b_off = indexer.compute_relevance_score(doc_official, query, query_info=q_info)
        score_unk, b_unk = indexer.compute_relevance_score(doc_unknown, query, query_info=q_info)
        self.assertGreater(score_off, score_unk)
        self.assertGreater(b_off["authority_boost"], b_unk["authority_boost"])

    # 4. Recent document ranks higher than 3-year-old document for 'latest release'.
    def test_04_freshness_boost_for_latest_release_query(self):
        query = "python latest release update"
        q_info = query_engine.understand_query(query)
        now = time.time()
        doc_fresh = {
            "title": "Python Latest Release Notes",
            "body_text": "Official release notes for the latest update and features in Python.",
            "domain": "python.org",
            "url": "https://python.org/news/latest",
            "published_at": now - 86400,  # 1 day ago
            "language": "en"
        }
        doc_old = {
            "title": "Python Latest Release Notes",
            "body_text": "Official release notes for the latest update and features in Python.",
            "domain": "python.org",
            "url": "https://python.org/news/old",
            "published_at": now - (3 * 365 * 86400),  # 3 years ago
            "language": "en"
        }
        score_fresh, b_fresh = indexer.compute_relevance_score(doc_fresh, query, query_info=q_info)
        score_old, b_old = indexer.compute_relevance_score(doc_old, query, query_info=q_info)
        self.assertGreater(score_fresh, score_old)
        self.assertGreater(b_fresh["freshness_boost"], b_old["freshness_boost"])

    # 5. Evergreen query does not overly penalize older high-quality documentation.
    def test_05_evergreen_query_does_not_severely_penalize_older_docs(self):
        query = "what is binary search algorithm"
        q_info = query_engine.understand_query(query)
        now = time.time()
        doc_evergreen_old = {
            "title": "Binary Search Algorithm Explanation",
            "body_text": "Binary search is an efficient divide and conquer algorithm for finding an item from a sorted list.",
            "domain": "algorithms.org",
            "url": "https://algorithms.org/binary-search",
            "published_at": now - (5 * 365 * 86400),
            "language": "en"
        }
        score, breakdown = indexer.compute_relevance_score(doc_evergreen_old, query, query_info=q_info)
        # In evergreen query, freshness boost should be non-negative (>= 0.0)
        self.assertGreaterEqual(breakdown["freshness_boost"], 0.0)

    # 6. site: restriction excludes non-matching domains from candidate pool.
    def test_06_site_restriction_filters_candidates(self):
        query = "python site:python.org"
        q_info = query_engine.understand_query(query)
        self.assertEqual(q_info.get("site_restriction"), "python.org")
        results = indexer.search_local_index("python", query_info=q_info)
        for r in results:
            self.assertIn("python.org", r.get("domain", "").lower())

    # 7. Stop words alone do not produce high ranking scores.
    def test_07_stop_words_produce_low_ranking(self):
        query = "the in and of to"
        q_info = query_engine.understand_query(query)
        doc = {
            "title": "General Document",
            "body_text": "The quick brown fox jumps over the lazy dog in and of itself.",
            "domain": "example.org",
            "url": "https://example.org/article",
            "language": "en"
        }
        score, breakdown = indexer.compute_relevance_score(doc, query, query_info=q_info)
        # Stop words stripped in tokens, so title boost and phrase boost should be low
        self.assertLess(breakdown["title_boost"], 10.0)

    # 8. Single consonant repetition typo normalized: 'pythonnn' -> 'python'.
    def test_08_consonant_repetition_normalized(self):
        norm = query_engine.normalize_query("pythonnn")
        self.assertEqual(norm["normalized_query"], "python")

    # 9. Multi-vowel word preserved: 'look' not mangled.
    def test_09_multi_vowel_word_preserved(self):
        norm = query_engine.normalize_query("look at the green tree")
        self.assertIn("look", norm["tokens"])
        self.assertIn("green", norm["tokens"])
        self.assertIn("tree", norm["tokens"])

    # 10. Mixed language Hindi/English normalized properly.
    def test_10_mixed_hindi_english_normalized(self):
        norm = query_engine.normalize_query("Python kaise sikhe beginner ke liye")
        self.assertEqual(norm["language"], "hinglish")
        self.assertIn("sikhe", norm["tokens"])
        self.assertIn("python", norm["tokens"])

    # 11. Punctuation stripped correctly without destroying terms.
    def test_11_punctuation_stripped_safely(self):
        norm = query_engine.normalize_query("what is C++ and node.js?!")
        self.assertIn("c++", norm["normalized_query"])
        self.assertIn("node.js", norm["normalized_query"])
        self.assertNotIn("?!", norm["normalized_query"])

    # 12. Empty query rejected with 400.
    def test_12_empty_query_rejected(self):
        resp = self.client.get("/api/search?q=")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    # 13. Very long query truncated without crash.
    def test_13_very_long_query_truncated_safely(self):
        long_q = "python " * 200  # 1400 chars
        resp = self.client.get(f"/api/search?q={long_q}")
        self.assertIn(resp.status_code, [200, 429])
        if resp.status_code == 200:
            data = resp.get_json()
            self.assertLessEqual(len(data.get("query", "")), 500)

    # 14. Whitespace-only query rejected with 400.
    def test_14_whitespace_query_rejected(self):
        resp = self.client.get("/api/search?q=     ")
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn("error", data)

    # 15. Special character only query handled safely.
    def test_15_special_characters_only_handled_safely(self):
        resp = self.client.get("/api/search?q=@@@###$$$%%%")
        self.assertIn(resp.status_code, [200, 400, 429])

    # 16. URL with tracking params normalized (utm_* stripped).
    def test_16_tracking_params_stripped(self):
        raw = "https://example.com/guide?utm_source=twitter&utm_medium=cpc&id=42&fbclid=XYZ123"
        clean = search_validator.normalize_url(raw)
        self.assertNotIn("utm_source", clean)
        self.assertNotIn("utm_medium", clean)
        self.assertNotIn("fbclid", clean)
        self.assertIn("id=42", clean)

    # 17. URL with fragment stripped: example.com#section -> example.com.
    def test_17_fragment_stripped(self):
        raw = "https://example.com/docs/api#section-installation"
        clean = search_validator.normalize_url(raw)
        self.assertEqual(clean, "https://example.com/docs/api")

    # 18. Duplicate canonical URLs deduplicated.
    def test_18_duplicate_canonical_urls_deduplicated(self):
        results = [
            {"title": "First Version", "url": "https://example.com/docs?utm_source=1", "domain": "example.com", "snippet": "Text 1"},
            {"title": "Second Version", "url": "https://example.com/docs?utm_source=2", "domain": "example.com", "snippet": "Text 2"}
        ]
        deduped = search_validator.deduplicate_results(results)
        self.assertEqual(len(deduped), 1)

    # 19. Same domain results capped at diversity limit in top results.
    def test_19_domain_diversity_damping(self):
        items = [
            {"title": f"Doc {i}", "url": f"https://monopoly.com/{i}", "domain": "monopoly.com", "score": 90.0 - i}
            for i in range(5)
        ]
        items.append({"title": "Alternative", "url": "https://other.org/1", "domain": "other.org", "score": 82.0})
        diversified = indexer.apply_domain_diversity(items, max_per_domain=2, max_results=5)
        domains_in_top = [r["domain"] for r in diversified[:3]]
        self.assertIn("other.org", domains_in_top)
        self.assertLessEqual(domains_in_top.count("monopoly.com"), 2)

    # 20. Keyword stuffing penalized.
    def test_20_keyword_stuffing_penalized(self):
        query = "python tutorial"
        q_info = query_engine.understand_query(query)
        doc_stuffed = {
            "title": "Python Tutorial",
            "body_text": "python python python python python python python python python python python python python python python python python python python python python python python python python python",
            "domain": "spam.com",
            "url": "https://spam.com/stuffed",
            "language": "en"
        }
        doc_normal = {
            "title": "Python Tutorial",
            "body_text": "In this complete guide to Python programming, we explore core syntax, data structures, and practical code examples for beginners.",
            "domain": "learn.org",
            "url": "https://learn.org/guide",
            "language": "en"
        }
        score_stuffed, b_stuffed = indexer.compute_relevance_score(doc_stuffed, query, query_info=q_info)
        score_normal, b_normal = indexer.compute_relevance_score(doc_normal, query, query_info=q_info)
        self.assertGreater(b_stuffed["spam_penalty"], 0.0)
        self.assertGreater(score_normal, score_stuffed)

    # 21. Thin page penalized.
    def test_21_thin_page_penalized(self):
        query = "python tutorial"
        q_info = query_engine.understand_query(query)
        doc_thin = {
            "title": "Python Tutorial",
            "body_text": "Click here to see tutorial.",  # very short (< 60 chars)
            "domain": "thin.org",
            "url": "https://thin.org/page",
            "language": "en"
        }
        score, breakdown = indexer.compute_relevance_score(doc_thin, query, query_info=q_info)
        self.assertGreaterEqual(breakdown["spam_penalty"], 40.0)

    # 22. Debug ranking mode returns score breakdowns.
    def test_22_debug_ranking_mode_returns_breakdowns(self):
        res = indexer.search_local_index("python", limit=2, debug=True)
        if res:
            self.assertIn("score_breakdown", res[0])
            self.assertIn("signals", res[0]["score_breakdown"])

    # 23. Non-debug ranking mode conceals score breakdowns.
    def test_23_non_debug_ranking_mode_conceals_breakdowns(self):
        res = indexer.search_local_index("python", limit=2, debug=False)
        if res:
            self.assertNotIn("score_breakdown", res[0])

    # 24. Response latency for local index search is within target (<100ms).
    def test_24_local_index_search_latency_under_100ms(self):
        t0 = time.time()
        res = indexer.search_local_index("python", limit=5)
        elapsed_ms = (time.time() - t0) * 1000
        self.assertLess(elapsed_ms, 100.0)

    # 25. Score breakdown components sum correctly to composite score.
    def test_25_score_breakdown_sums_to_composite_score(self):
        query = "python programming"
        q_info = query_engine.understand_query(query)
        doc = {
            "title": "Python Programming",
            "body_text": "A comprehensive book about Python programming language fundamentals and patterns.",
            "headings": "Overview",
            "domain": "python.org",
            "url": "https://python.org/book",
            "language": "en"
        }
        score, b = indexer.compute_relevance_score(doc, query, query_info=q_info)
        expected = round(
            b["bm25"] + b["title_boost"] + b["heading_boost"] + b["phrase_boost"] +
            b["url_boost"] + b["lang_boost"] + b["quality_boost"] + b["authority_boost"] +
            b["intent_boost"] + b["freshness_boost"] - b["spam_penalty"],
            2
        )
        self.assertAlmostEqual(score, expected, places=1)


if __name__ == "__main__":
    unittest.main()
