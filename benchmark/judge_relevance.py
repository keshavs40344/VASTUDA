#!/usr/bin/env python3
"""
VASTUDA — Human Relevance Judging Tool (5.2)

Selects 50 representative queries from the 200-query dataset.
For each query, fetches the LIVE top-10 results from VASTUDA.
Prompts the human judge to assign grades 0/1/2/3 per result.
Saves to benchmark/judgments.json after every query (resume-safe).

Grade scale:
  3 — Perfectly relevant: directly and completely answers the query
  2 — Mostly relevant: helpful, covers most of the query's need
  1 — Partially relevant: tangentially related, marginally useful
  0 — Not relevant: unrelated, wrong, or spam

Usage:
  python benchmark/judge_relevance.py
  python benchmark/judge_relevance.py --server http://127.0.0.1:5000
  python benchmark/judge_relevance.py --resume            # skip already judged
"""

import sys
import os
import json
import argparse
import requests
import textwrap
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VASTUDA_ROOT = os.path.dirname(SCRIPT_DIR)

DATASET_PATH = os.path.join(SCRIPT_DIR, "relevance_dataset.json")
JUDGMENTS_PATH = os.path.join(SCRIPT_DIR, "judgments.json")

DEFAULT_SERVER = "http://127.0.0.1:5000"
JUDGE_QUERY_COUNT = 50


# ---------------------------------------------------------------------------
# Query selection: 5 queries per category, 10 categories = 50 total
# ---------------------------------------------------------------------------

CATEGORIES = [
    "informational",
    "programming",
    "academic",
    "news_current",
    "hindi",
    "hinglish",
    "long_tail",
    "comparison",
    "definitions",
    "navigational",
]

QUERIES_PER_CATEGORY = 5


def select_representative_queries(dataset: list) -> list:
    """Pick 5 queries per category from the dataset for a 50-query judging set."""
    by_category = {}
    for item in dataset:
        cat = item.get("category", "").lower().replace(" ", "_").replace("/", "_")
        # Fuzzy-match categories
        matched = None
        for c in CATEGORIES:
            if c in cat or cat in c:
                matched = c
                break
        if matched is None:
            # Try partial matches
            for c in CATEGORIES:
                if any(part in cat for part in c.split("_")):
                    matched = c
                    break
        if matched:
            by_category.setdefault(matched, []).append(item)

    selected = []
    for cat in CATEGORIES:
        pool = by_category.get(cat, [])
        # Take first 5 (dataset is pre-ordered by quality)
        chosen = pool[:QUERIES_PER_CATEGORY]
        selected.extend(chosen)

    return selected


# ---------------------------------------------------------------------------
# Fetch live results from VASTUDA
# ---------------------------------------------------------------------------

def fetch_results(query: str, server: str, timeout: float = 12.0) -> list:
    """Fetch top-10 results from the live VASTUDA server."""
    try:
        url = f"{server}/api/search"
        params = {"q": query, "num": 10}
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return results[:10]
    except requests.exceptions.ConnectionError:
        print(f"\n  [ERROR] Cannot connect to VASTUDA server at {server}")
        print("  Make sure the server is running: python search_engine/server.py")
        sys.exit(1)
    except Exception as e:
        print(f"\n  [WARN] Could not fetch results for '{query}': {type(e).__name__}: {e}")
        return []


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

GRADE_LABELS = {
    "3": "Perfectly relevant",
    "2": "Mostly relevant",
    "1": "Partially relevant",
    "0": "Not relevant",
}

COLORS = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "cyan":   "\033[96m",
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "red":    "\033[91m",
    "dim":    "\033[2m",
    "blue":   "\033[94m",
}

def c(text, color):
    """Colorize text for terminal output."""
    if sys.stdout.isatty():
        return f"{COLORS.get(color, '')}{text}{COLORS['reset']}"
    return text


def display_result(idx: int, result: dict):
    """Pretty-print a single search result for judging."""
    title   = result.get("title", "(no title)").strip()[:120]
    url     = result.get("url", "(no url)").strip()[:100]
    snippet = result.get("snippet", result.get("description", "")).strip()

    print(f"\n  {c(f'[{idx}]', 'cyan')} {c(title, 'bold')}")
    print(f"      {c(url, 'blue')}")
    if snippet:
        wrapped = textwrap.fill(snippet, width=90, initial_indent="      ", subsequent_indent="      ")
        print(c(wrapped, "dim"))


def display_query_header(query_num: int, total: int, query: str, category: str):
    """Display the judging prompt header for one query."""
    bar = "─" * 70
    print(f"\n{c(bar, 'cyan')}")
    print(f"  {c(f'Query {query_num}/{total}', 'yellow')}  [{c(category, 'green')}]")
    print(f"  {c('QUERY:', 'bold')} {c(query, 'cyan')}")
    print(f"{c(bar, 'cyan')}")
    print()
    print(c("  Grade scale:", "dim"))
    for g, label in GRADE_LABELS.items():
        print(c(f"    {g} = {label}", "dim"))
    print()


def grade_prompt(result_num: int) -> str:
    """Prompt the judge for a single result grade, returns '0','1','2','3' or 's'(skip)."""
    while True:
        try:
            raw = input(f"  Grade for result [{result_num}] (0/1/2/3, or s=skip query, q=quit): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n\nJudging interrupted. Progress saved.")
            sys.exit(0)
        if raw in ("0", "1", "2", "3", "s", "q"):
            return raw
        print("  Invalid input. Enter 0, 1, 2, 3, s, or q.")


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def load_judgments() -> dict:
    """Load existing judgments file, or return empty dict."""
    if os.path.exists(JUDGMENTS_PATH):
        try:
            with open(JUDGMENTS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_judgments(judgments: dict):
    """Save judgments to disk atomically."""
    tmp_path = JUDGMENTS_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(judgments, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, JUDGMENTS_PATH)


# ---------------------------------------------------------------------------
# Main judging loop
# ---------------------------------------------------------------------------

def judge_query(query: str, category: str, results: list, query_num: int, total: int) -> dict | None:
    """
    Display a query's results and collect human grades.
    Returns {"grades": [...], "total_known_relevant": n} or None if skipped.
    """
    display_query_header(query_num, total, query, category)

    if not results:
        print(c("  [!] No results returned by VASTUDA for this query.", "red"))
        print("  Recording as empty result (grades=[]).\n")
        return {"grades": [], "total_known_relevant": 0, "note": "no_results"}

    for i, result in enumerate(results, 1):
        display_result(i, result)

    print()
    grades = []
    skip_query = False
    for i, result in enumerate(results, 1):
        grade = grade_prompt(i)
        if grade == "q":
            print("\nQuit signal received. Saving progress and exiting.")
            return None  # caller handles quit
        if grade == "s":
            skip_query = True
            break
        grades.append(int(grade))

    if skip_query:
        print(c("  [~] Query skipped.", "yellow"))
        return None  # skip: don't save anything for this query

    # Ask for estimated total relevant docs in top-10 universe
    total_known_relevant = sum(1 for g in grades if g >= 2)
    print()
    try:
        tr_input = input(
            f"  Estimated total relevant docs (default={total_known_relevant}, "
            "or enter a number if you know more exist): "
        ).strip()
        if tr_input.isdigit():
            total_known_relevant = max(total_known_relevant, int(tr_input))
    except (EOFError, KeyboardInterrupt):
        pass

    entry = {
        "grades": grades,
        "total_known_relevant": total_known_relevant,
    }
    print(c(f"\n  OK Saved: grades={grades}, total_known_relevant={total_known_relevant}", "green"))
    return entry


def run_judging_session(server: str, resume: bool):
    print(c("\n+======================================================================+", "cyan"))
    print(c("|         VASTUDA — Human Relevance Judging Tool (v5.2)               |", "cyan"))
    print(c("+======================================================================+", "cyan"))
    print()
    print(f"  Server  : {c(server, 'green')}")
    print(f"  Dataset : {c(DATASET_PATH, 'dim')}")
    print(f"  Output  : {c(JUDGMENTS_PATH, 'dim')}")
    print()

    # Load dataset
    if not os.path.exists(DATASET_PATH):
        print(c(f"[ERROR] Dataset not found: {DATASET_PATH}", "red"))
        print("  Run benchmark/evaluate_relevance.py first to generate the dataset.")
        sys.exit(1)

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    queries = select_representative_queries(dataset)
    if len(queries) < JUDGE_QUERY_COUNT:
        print(c(f"[WARN] Only {len(queries)} queries found across categories (expected 50). "
                "Proceeding with available queries.", "yellow"))

    # Load existing judgments
    judgments = load_judgments()

    if resume and judgments:
        already_done = len(judgments)
        print(c(f"  Resume mode: {already_done} queries already judged, continuing...", "yellow"))
    elif judgments and not resume:
        print(c(f"  [INFO] Found existing judgments.json with {len(judgments)} entries.", "yellow"))
        choice = input("  Overwrite existing judgments? (y/n, default=n): ").strip().lower()
        if choice != "y":
            print("  Use --resume to continue from where you left off.")
            sys.exit(0)
        judgments = {}

    total = len(queries)
    judged_count = 0
    skipped_count = 0

    for i, item in enumerate(queries, 1):
        query    = item.get("query", "").strip()
        category = item.get("category", "unknown")

        if not query:
            continue

        # Skip already-judged queries in resume mode
        if resume and query in judgments:
            print(c(f"  [{i}/{total}] SKIP (already judged): {query[:60]}", "dim"))
            continue

        # Fetch live results
        print(c(f"\n  Fetching results for: {query[:70]}...", "dim"), end="", flush=True)
        t0 = time.time()
        results = fetch_results(query, server)
        elapsed_ms = int((time.time() - t0) * 1000)
        print(c(f" ({elapsed_ms}ms, {len(results)} results)", "dim"))

        # Judge
        entry = judge_query(query, category, results, i, total)

        if entry is None:
            # Check if user wants to quit or just skipped
            skipped_count += 1
            continue

        judgments[query] = entry
        judged_count += 1
        save_judgments(judgments)

    print()
    print(c("=" * 70, "cyan"))
    print(c(f"  Judging session complete!", "green"))
    print(f"  Queries judged   : {c(str(judged_count), 'bold')}")
    print(f"  Queries skipped  : {skipped_count}")
    print(f"  Total in file    : {len(judgments)}")
    print(f"  Output saved to  : {c(JUDGMENTS_PATH, 'green')}")
    print(c("=" * 70, "cyan"))
    print()
    print(c("  Next step: run python benchmark/evaluate_relevance.py to compute metrics.", "yellow"))
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="VASTUDA Human Relevance Judging Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"VASTUDA server URL (default: {DEFAULT_SERVER})"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing judgments.json, skipping already-judged queries"
    )
    args = parser.parse_args()

    run_judging_session(server=args.server, resume=args.resume)


if __name__ == "__main__":
    main()
