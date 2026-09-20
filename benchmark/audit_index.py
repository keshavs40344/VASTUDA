"""VASTUDA Sovereign Search Engine - Phase 5.4
Index Quality Audit Tool

Analyzes the local SQLite search index for:
- Total documents & unique domains
- Language distribution
- Document length metrics (min, max, avg, median word count)
- Structural density (heading count, paragraph count)
- Duplicate content hashes
- Thin pages (< 80 chars)
- Missing metadata (title, snippet)
- Top domains representation
"""

import os
import sys
import json
import sqlite3
import statistics
import urllib.parse
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from search_engine import db


def run_index_audit(db_path=None):
    if db_path is None:
        db_path = db.DB_PATH

    if not os.path.exists(db_path):
        return {
            "error": f"Database file not found at {db_path}",
            "total_documents": 0
        }

    conn = db.get_db()
    cursor = conn.cursor()

    try:
        # Check if columns exist
        cursor.execute("PRAGMA table_info(documents)")
        cols = [r["name"] for r in cursor.fetchall()]

        has_word_count = "word_count" in cols
        has_content_hash = "content_hash" in cols
        has_language = "language" in cols
        has_headings = "heading_count" in cols
        has_paragraphs = "paragraph_count" in cols

        # Fetch all document rows
        query_fields = ["id", "url", "title", "body_text", "meta_desc"]
        if has_language:
            query_fields.append("language")
        if has_word_count:
            query_fields.append("word_count")
        if has_content_hash:
            query_fields.append("content_hash")
        if has_headings:
            query_fields.append("heading_count")
        if has_paragraphs:
            query_fields.append("paragraph_count")

        cursor.execute(f"SELECT {', '.join(query_fields)} FROM documents")
        rows = cursor.fetchall()
        total_docs = len(rows)

        if total_docs == 0:
            return {
                "total_documents": 0,
                "message": "Index is empty"
            }

        domains = []
        languages = []
        word_counts = []
        heading_counts = []
        paragraph_counts = []
        content_hashes = []
        thin_pages = []
        missing_titles = []
        missing_content = []

        for row in rows:
            url = row["url"] or ""
            domain = ""
            if url:
                try:
                    domain = urllib.parse.urlparse(url).netloc.lower()
                except Exception:
                    domain = ""
            if domain:
                domains.append(domain)

            lang = row["language"] if has_language else "en"
            languages.append(lang or "unknown")

            body = row["body_text"] or ""
            title = row["title"] or ""

            if not title.strip() or title.strip().lower() == "untitled":
                missing_titles.append(url)

            if not body.strip():
                missing_content.append(url)

            # Character length
            char_len = len(body.strip())
            if char_len < 80:
                thin_pages.append({"url": url, "chars": char_len, "title": title[:40]})

            # Word count
            if has_word_count and row["word_count"] is not None and row["word_count"] > 0:
                wc = row["word_count"]
            else:
                wc = len(body.split())
            word_counts.append(wc)

            if has_headings and row["heading_count"] is not None:
                heading_counts.append(row["heading_count"])
            if has_paragraphs and row["paragraph_count"] is not None:
                paragraph_counts.append(row["paragraph_count"])

            if has_content_hash and row["content_hash"]:
                content_hashes.append(row["content_hash"])

        # Calculations
        domain_counts = Counter(domains)
        lang_counts = Counter(languages)
        hash_counts = Counter(content_hashes)
        duplicate_hashes = {h: cnt for h, cnt in hash_counts.items() if cnt > 1}

        wc_min = min(word_counts) if word_counts else 0
        wc_max = max(word_counts) if word_counts else 0
        wc_avg = round(statistics.mean(word_counts), 1) if word_counts else 0
        wc_median = round(statistics.median(word_counts), 1) if word_counts else 0

        audit_results = {
            "total_documents": total_docs,
            "unique_domains_count": len(domain_counts),
            "top_domains": dict(domain_counts.most_common(15)),
            "language_distribution": dict(lang_counts),
            "word_count_stats": {
                "min": wc_min,
                "max": wc_max,
                "avg": wc_avg,
                "median": wc_median
            },
            "structural_metrics": {
                "avg_headings": round(statistics.mean(heading_counts), 1) if heading_counts else 0,
                "avg_paragraphs": round(statistics.mean(paragraph_counts), 1) if paragraph_counts else 0
            },
            "duplicate_content_hashes_count": len(duplicate_hashes),
            "duplicate_content_groups": duplicate_hashes,
            "thin_pages_count": len(thin_pages),
            "thin_pages_sample": thin_pages[:10],
            "missing_titles_count": len(missing_titles),
            "missing_content_count": len(missing_content),
            "quality_grade": "HEALTHY" if (len(thin_pages) == 0 and len(duplicate_hashes) == 0) else "NEEDS_CLEANUP"
        }
        return audit_results

    finally:
        conn.close()


def print_audit_report(report):
    print("=" * 60)
    print("        VASTUDA SOVEREIGN INDEX AUDIT REPORT")
    print("=" * 60)
    print(f"Total Documents Indexed : {report.get('total_documents', 0)}")
    print(f"Unique Domains Crawled  : {report.get('unique_domains_count', 0)}")
    print(f"Index Quality Grade     : {report.get('quality_grade', 'N/A')}")
    print("\n[Language Distribution]")
    for lang, count in report.get("language_distribution", {}).items():
        print(f"  - {lang}: {count}")

    print("\n[Word Count Statistics]")
    wc = report.get("word_count_stats", {})
    print(f"  - Min: {wc.get('min', 0)} | Max: {wc.get('max', 0)} | Avg: {wc.get('avg', 0)} | Median: {wc.get('median', 0)}")

    print("\n[Top Represented Domains]")
    for domain, count in report.get("top_domains", {}).items():
        print(f"  - {domain}: {count} documents")

    print("\n[Quality & Duplication Flags]")
    print(f"  - Duplicate Content Hashes: {report.get('duplicate_content_hashes_count', 0)}")
    print(f"  - Thin Pages (< 80 chars) : {report.get('thin_pages_count', 0)}")
    print(f"  - Missing Titles          : {report.get('missing_titles_count', 0)}")
    print(f"  - Missing Content         : {report.get('missing_content_count', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    results = run_index_audit()
    print_audit_report(results)
    output_json = os.path.join(BASE_DIR, "benchmark", "index_audit_report.json")
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Detailed audit saved to {output_json}")
