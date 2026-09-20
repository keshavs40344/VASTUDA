import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JUDGMENTS_PATH = os.path.join(SCRIPT_DIR, "judgments.json")

def record_query_judgment(query, grades, total_known_relevant=None, note=None):
    judgments = {}
    if os.path.exists(JUDGMENTS_PATH):
        try:
            with open(JUDGMENTS_PATH, "r", encoding="utf-8") as f:
                judgments = json.load(f)
        except Exception:
            judgments = {}

    if note == "skipped":
        judgments[query] = {
            "grades": [],
            "total_known_relevant": 0,
            "status": "skipped"
        }
    else:
        if total_known_relevant is None:
            total_known_relevant = sum(1 for g in grades if g >= 2)
        judgments[query] = {
            "grades": grades,
            "total_known_relevant": max(total_known_relevant, sum(1 for g in grades if g >= 2))
        }

    tmp = JUDGMENTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(judgments, f, indent=2, ensure_ascii=False)
    os.replace(tmp, JUDGMENTS_PATH)

    # Re-generate report
    from benchmark.generate_human_relevance_report import generate_report
    report = generate_report()
    return report

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python record_judgment.py <query> <grades_comma_separated> [total_known_relevant]")
        sys.exit(1)
    q = sys.argv[1]
    raw_grades = sys.argv[2]
    if raw_grades.lower() in ("s", "skip"):
        rep = record_query_judgment(q, [], note="skipped")
    else:
        grades = [int(x.strip()) for x in raw_grades.split(",") if x.strip()]
        tkr = int(sys.argv[3]) if len(sys.argv) > 3 else None
        rep = record_query_judgment(q, grades, tkr)
    print("Updated judgments. Total judged:", rep["queries_judged"], "Remaining:", rep["queries_remaining"])
