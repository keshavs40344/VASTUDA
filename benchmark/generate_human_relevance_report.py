import os
import sys
import json
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JUDGMENTS_PATH = os.path.join(SCRIPT_DIR, "judgments.json")
REPORT_PATH = os.path.join(SCRIPT_DIR, "human_relevance_report.json")
DATASET_PATH = os.path.join(SCRIPT_DIR, "relevance_dataset.json")

def calculate_dcg(relevances, k=10):
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 2)
    return dcg

def calculate_ndcg(relevances, k=10):
    actual_dcg = calculate_dcg(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    ideal_dcg = calculate_dcg(ideal_relevances, k)
    if ideal_dcg == 0.0:
        return 0.0
    return actual_dcg / ideal_dcg

def generate_report(total_target_queries=50):
    judgments = {}
    if os.path.exists(JUDGMENTS_PATH):
        try:
            with open(JUDGMENTS_PATH, "r", encoding="utf-8") as f:
                judgments = json.load(f)
        except Exception:
            judgments = {}

    queries_judged = 0
    queries_skipped = 0
    total_results_judged = 0

    all_p3 = []
    all_p5 = []
    all_p10 = []
    all_rec10 = []
    all_mrr = []
    all_ndcg10 = []

    per_query_details = []

    for q, entry in judgments.items():
        if entry.get("note") == "skipped" or entry.get("status") == "skipped":
            queries_skipped += 1
            continue

        grades = entry.get("grades", [])
        if not grades and entry.get("note") != "no_results":
            continue

        queries_judged += 1
        total_results_judged += len(grades)

        # Binary relevance threshold: grades 2 and 3 count as relevant
        binary_rel = [1 if g >= 2 else 0 for g in grades]

        p3 = sum(binary_rel[:3]) / 3.0 if len(binary_rel) >= 3 else (sum(binary_rel) / max(len(binary_rel), 1))
        p5 = sum(binary_rel[:5]) / 5.0 if len(binary_rel) >= 5 else (sum(binary_rel) / max(len(binary_rel), 1))
        p10 = sum(binary_rel[:10]) / 10.0 if len(binary_rel) >= 10 else (sum(binary_rel) / max(len(binary_rel), 1))

        # MRR
        mrr = 0.0
        for r_idx, b in enumerate(binary_rel, 1):
            if b == 1:
                mrr = 1.0 / r_idx
                break

        ndcg10 = calculate_ndcg(grades[:10], k=10)
        known_relevant = entry.get("total_known_relevant", max(sum(binary_rel), 1))
        rec10 = sum(binary_rel[:10]) / known_relevant if known_relevant > 0 else 0.0

        all_p3.append(p3)
        all_p5.append(p5)
        all_p10.append(p10)
        all_rec10.append(rec10)
        all_mrr.append(mrr)
        all_ndcg10.append(ndcg10)

        per_query_details.append({
            "query": q,
            "grades": grades,
            "total_known_relevant": known_relevant,
            "p3": round(p3, 4),
            "p5": round(p5, 4),
            "p10": round(p10, 4),
            "recall10": round(rec10, 4),
            "mrr": round(mrr, 4),
            "ndcg10": round(ndcg10, 4)
        })

    remaining = max(0, total_target_queries - queries_judged - queries_skipped)

    if queries_judged > 0:
        summary_metrics = {
            "Precision@3": round(sum(all_p3) / len(all_p3), 4),
            "Precision@5": round(sum(all_p5) / len(all_p5), 4),
            "Precision@10": round(sum(all_p10) / len(all_p10), 4),
            "Recall@10": round(sum(all_rec10) / len(all_rec10), 4),
            "MRR": round(sum(all_mrr) / len(all_mrr), 4),
            "nDCG@10": round(sum(all_ndcg10) / len(all_ndcg10), 4)
        }
    else:
        summary_metrics = {
            "Precision@3": "NOT YET MEASURED",
            "Precision@5": "NOT YET MEASURED",
            "Precision@10": "NOT YET MEASURED",
            "Recall@10": "NOT YET MEASURED",
            "MRR": "NOT YET MEASURED",
            "nDCG@10": "NOT YET MEASURED"
        }

    report = {
        "evaluation_type": "HUMAN_RELEVANCE_EVALUATION",
        "target_query_count": total_target_queries,
        "queries_judged": queries_judged,
        "queries_skipped": queries_skipped,
        "queries_remaining": remaining,
        "results_judged": total_results_judged,
        "status": "IN_PROGRESS" if remaining > 0 else "COMPLETED",
        "metrics": summary_metrics,
        "queries": per_query_details
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report

if __name__ == "__main__":
    rep = generate_report()
    print(json.dumps(rep, indent=2))
