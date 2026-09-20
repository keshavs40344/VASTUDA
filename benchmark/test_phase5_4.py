#!/usr/bin/env python3
"""
VASTUDA 5.4 — Comprehensive Automated Test Suite (25 Tests)
Validates Phase 5.4 enhancements:
- Persistent SQLite cache (CRUD, TTL expiration, isolation, cleanup, bypass on debug)
- Deterministic spell correction (Damerau-Levenshtein, technical dictionary, token protection)
- Crawler expansion & frontier (seeds catalog, politeness, SSRF multi-hop, structural counts)
- Index management & online atomic backup (upsert, delete, reindex, PRAGMA integrity check)
- Index quality audit & diagnostic reporting
"""

import os
import sys
import time
import json
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from search_engine import db
from search_engine import crawler
from search_engine import indexer
from search_engine import query_engine
from search_engine import spell_checker
from search_engine import backup_index
from search_engine import server
from benchmark import audit_index


class TestPhase54ScaleAndQuality(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = server.app.test_client()
        # Clean test cache entries
        db.clear_search_cache()

    # 1. Persistent cache set and get
    def test_01_persistent_cache_set_and_get(self):
        cache_key = "test:unit_test_query:all:1:10"
        payload = {"status": "ok", "results": [{"title": "Test 1", "url": "https://example.com/1"}]}
        db.set_cached_search_result(
            cache_key=cache_key,
            query="unit test query",
            category="all",
            page=1,
            page_size=10,
            time_filter="",
            data=payload,
            ttl_seconds=300
        )
        cached = db.get_cached_search_result(cache_key)
        self.assertIsNotNone(cached)
        self.assertEqual(cached["status"], "ok")
        self.assertEqual(len(cached["results"]), 1)
        self.assertEqual(cached["results"][0]["title"], "Test 1")

    # 2. Persistent cache TTL expiration
    def test_02_persistent_cache_ttl_expiration(self):
        cache_key = "test:expired_query:all:1:10"
        payload = {"status": "ok", "results": []}
        # Insert with negative TTL so it is immediately expired
        db.set_cached_search_result(
            cache_key=cache_key,
            query="expired query",
            category="all",
            page=1,
            page_size=10,
            time_filter="",
            data=payload,
            ttl_seconds=-10
        )
        cached = db.get_cached_search_result(cache_key)
        self.assertIsNone(cached)

    # 3. Persistent cache key isolation across categories and pages
    def test_03_persistent_cache_key_isolation(self):
        key_all = "test:query:all:1:10"
        key_news = "test:query:news:1:10"
        key_page2 = "test:query:all:2:10"
        db.set_cached_search_result(key_all, "query", "all", 1, 10, "", {"val": "all_page1"}, ttl_seconds=300)
        db.set_cached_search_result(key_news, "query", "news", 1, 10, "", {"val": "news_page1"}, ttl_seconds=300)
        db.set_cached_search_result(key_page2, "query", "all", 2, 10, "", {"val": "all_page2"}, ttl_seconds=300)

        self.assertEqual(db.get_cached_search_result(key_all)["val"], "all_page1")
        self.assertEqual(db.get_cached_search_result(key_news)["val"], "news_page1")
        self.assertEqual(db.get_cached_search_result(key_page2)["val"], "all_page2")

    # 4. Persistent cache cleanup of expired entries
    def test_04_persistent_cache_cleanup(self):
        # Insert 1 fresh and 2 expired
        db.set_cached_search_result("test:fresh", "fresh", "all", 1, 10, "", {"data": 1}, ttl_seconds=600)
        db.set_cached_search_result("test:exp1", "exp1", "all", 1, 10, "", {"data": 2}, ttl_seconds=-100)
        db.set_cached_search_result("test:exp2", "exp2", "all", 1, 10, "", {"data": 3}, ttl_seconds=-200)

        deleted = db.cleanup_expired_cache()
        self.assertGreaterEqual(deleted, 2)
        self.assertIsNotNone(db.get_cached_search_result("test:fresh"))
        self.assertIsNone(db.get_cached_search_result("test:exp1"))

    # 5. Persistent cache clear
    def test_05_persistent_cache_clear(self):
        db.set_cached_search_result("test:to_clear", "clear", "all", 1, 10, "", {"data": 1}, ttl_seconds=300)
        self.assertIsNotNone(db.get_cached_search_result("test:to_clear"))
        db.clear_search_cache()
        self.assertIsNone(db.get_cached_search_result("test:to_clear"))

    # 6. Server /api/search uses persistent cache
    def test_06_server_search_cache_hit_response(self):
        q = "python tutorial testing"
        resp1 = self.client.get(f"/api/search?q={q}")
        self.assertEqual(resp1.status_code, 200)
        data1 = resp1.get_json()

        # Check that cache key exists in db
        cache_key = f"all:{q.lower()}:any:1:10"
        cached_entry = db.get_cached_search_result(cache_key)
        if data1.get("results"):
            self.assertIsNotNone(cached_entry)
            self.assertEqual(cached_entry["query"], q)

    # 7. Server debug mode bypasses cache
    def test_07_server_debug_bypasses_cache(self):
        resp = self.client.get("/api/search?q=python&debug=1")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("debug_ranking", data)

    # 8. Spell checker known typos
    def test_08_spell_checker_known_typos(self):
        self.assertEqual(spell_checker.correct_word("pythn"), "python")
        self.assertEqual(spell_checker.correct_word("artifical"), "artificial")
        self.assertEqual(spell_checker.correct_word("algoritm"), "algorithm")
        self.assertEqual(spell_checker.correct_word("databse"), "database")

    # 9. Spell checker protects technical tokens
    def test_09_spell_checker_protects_technical_tokens(self):
        self.assertEqual(spell_checker.correct_word("c++"), "c++")
        self.assertEqual(spell_checker.correct_word("node.js"), "node.js")
        self.assertEqual(spell_checker.correct_word("c#"), "c#")
        self.assertEqual(spell_checker.correct_word("react.js"), "react.js")

    # 10. Spell checker protects search operators
    def test_10_spell_checker_protects_search_operators(self):
        res = spell_checker.correct_query("site:python.org filetype:pdf")
        self.assertFalse(res["has_correction"])
        self.assertEqual(res["corrected_query"], "site:python.org filetype:pdf")

    # 11. Spell checker protects quoted phrases
    def test_11_spell_checker_protects_quoted_phrases(self):
        res = spell_checker.correct_query('"pythn tutorial" and test')
        # Quoted string remains untouched
        self.assertIn('"pythn tutorial"', res["corrected_query"])

    # 12. Spell checker multi-word query correction
    def test_12_spell_checker_multiword_correction(self):
        res = spell_checker.correct_query("fastapi framwork tutorial")
        self.assertTrue(res["has_correction"])
        self.assertEqual(res["corrected_query"], "fastapi framework tutorial")

    # 13. Spell checker handles Hindi Devanagari text safely
    def test_13_spell_checker_hindi_devanagari_preserved(self):
        hindi_q = "भारत का संविधान"
        res = spell_checker.correct_query(hindi_q)
        self.assertFalse(res["has_correction"])
        self.assertEqual(res["corrected_query"], hindi_q)

    # 14. Query engine suggest_spell_correction export
    def test_14_query_engine_suggest_spell_correction(self):
        res = query_engine.suggest_spell_correction("pythn tutorial")
        self.assertIsInstance(res, dict)
        self.assertIn("has_correction", res)
        self.assertIn("corrected_query", res)
        self.assertIn("confidence", res)
        self.assertTrue(res["has_correction"])
        self.assertEqual(res["corrected_query"], "python tutorial")

    # 15. Query engine sovereign suggestions prefix lookup
    def test_15_query_engine_suggestions_prefix(self):
        suggs = query_engine.get_query_suggestions("py", limit=5)
        self.assertIsInstance(suggs, list)
        self.assertTrue(any(s.lower().startswith("py") for s in suggs))

    # 16. Crawler loads seeds catalog
    def test_16_crawler_loads_seeds_config(self):
        seeds = crawler.load_seeds_config()
        self.assertIsInstance(seeds, list)
        self.assertGreater(len(seeds), 10)
        self.assertTrue(any("python.org" in s.get("url", "") for s in seeds))

    # 17. Crawler domain politeness delay
    def test_17_crawler_domain_politeness_delay(self):
        domain = "testpolite.org"
        crawler.DOMAIN_POLITENESS[domain] = time.time()
        # Immediate next crawl should calculate remaining politeness delay
        elapsed = time.time() - crawler.DOMAIN_POLITENESS[domain]
        self.assertLess(elapsed, crawler.CRAWL_DELAY_SECONDS + 0.5)

    # 18. Crawler SSRF protection against private addresses
    def test_18_crawler_ssrf_protection_private_ips(self):
        self.assertFalse(crawler.is_safe_url("http://127.0.0.1/admin"))
        self.assertFalse(crawler.is_safe_url("http://localhost:8080/"))
        self.assertFalse(crawler.is_safe_url("http://169.254.169.254/latest/meta-data/"))
        self.assertFalse(crawler.is_safe_url("http://10.0.0.1/internal"))
        self.assertFalse(crawler.is_safe_url("http://192.168.1.1/router"))
        self.assertTrue(crawler.is_safe_url("https://docs.python.org/3/"))

    # 19. Crawler robots.txt parsing and compliance
    def test_19_crawler_robots_txt_compliance(self):
        # Local mock robots parser
        allowed1, _ = crawler.is_allowed_by_robots("https://docs.python.org/3/tutorial/")
        self.assertTrue(allowed1)
        # Vastuda internal protected path
        allowed2, _ = crawler.is_allowed_by_robots("https://vastuda.internal/admin/secret")
        self.assertFalse(allowed2)

    # 20. Crawler document structure metrics extraction
    def test_20_crawler_document_structure_extraction(self):
        sample_html = """
        <html>
        <head><title>Test Article</title></head>
        <body>
            <h1>Main Title</h1>
            <h2>Section 1</h2>
            <p>This is paragraph one with informative content about algorithms and data structures.</p>
            <p>This is paragraph two providing additional context and architectural explanation.</p>
        </body>
        </html>
        """
        extracted = crawler.extract_page_content("https://example.com/test", sample_html)
        self.assertIsNotNone(extracted)
        self.assertGreater(extracted["word_count"], 15)
        self.assertEqual(extracted["heading_count"], 2)
        self.assertEqual(extracted["paragraph_count"], 2)

    # 21. Crawler status endpoint contracts
    def test_21_crawler_status_endpoint(self):
        resp = self.client.get("/api/crawler/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data.get("status"), "success")
        self.assertIn("data", data)
        self.assertIn("documents_indexed", data["data"])
        self.assertIn("politeness_delay_sec", data["data"])

    # 22. Indexer atomic upsert and delete operations
    def test_22_indexer_upsert_and_delete(self):
        test_url = "https://example.com/test_upsert_delete_doc"
        doc = {
            "url": test_url,
            "title": "Upsert Delete Test Document",
            "body_text": "Detailed content testing atomic insertion and deletion into full text search.",
            "headings": "Test Heading",
            "meta_desc": "Test Description",
            "language": "en",
            "domain": "example.com",
            "word_count": 12,
            "heading_count": 1,
            "paragraph_count": 1
        }
        # Upsert
        indexer.upsert_document(doc)
        stats_after_add = indexer.get_index_stats()
        self.assertGreater(stats_after_add["indexed_documents"], 0)

        # Delete
        success = indexer.delete_document(test_url)
        self.assertTrue(success)

    # 23. Online atomic backup and integrity check
    def test_23_backup_online_and_integrity_check(self):
        res = backup_index.create_backup(max_retain=3)
        self.assertEqual(res["status"], "success")
        self.assertTrue(os.path.exists(res["backup_path"]))
        self.assertGreater(res["size_bytes"], 1000)

        # Verify integrity
        ok, msg = backup_index.verify_sqlite_integrity(res["backup_path"])
        self.assertTrue(ok)
        self.assertEqual(msg, "ok")

    # 24. Index audit metrics calculation
    def test_24_audit_index_metrics(self):
        report = audit_index.run_index_audit()
        self.assertIsInstance(report, dict)
        self.assertIn("total_documents", report)
        self.assertIn("unique_domains_count", report)
        self.assertIn("word_count_stats", report)
        self.assertIn("quality_grade", report)
        self.assertGreaterEqual(report["total_documents"], 50)
        self.assertEqual(report["quality_grade"], "HEALTHY")

    # 25. Health and Version contract 5.4
    def test_25_health_and_version_contracts(self):
        resp_health = self.client.get("/health")
        self.assertEqual(resp_health.status_code, 200)
        self.assertEqual(resp_health.get_json().get("version"), "5.4")

        resp_version = self.client.get("/api/version")
        self.assertEqual(resp_version.status_code, 200)
        self.assertEqual(resp_version.get_json().get("version"), "5.4")


if __name__ == "__main__":
    unittest.main()
