import os
import sys
import json
import time
import math
import urllib.request
import urllib.parse
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass


def calculate_dcg(relevances, k=10):
    """Calculate Discounted Cumulative Gain at k with 2^rel - 1 formulation."""
    dcg = 0.0
    for i, rel in enumerate(relevances[:k]):
        dcg += (2.0 ** rel - 1.0) / math.log2(i + 2)
    return dcg


def calculate_ndcg(relevances, k=10):
    """Calculate Normalized Discounted Cumulative Gain at k."""
    actual_dcg = calculate_dcg(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    ideal_dcg = calculate_dcg(ideal_relevances, k)
    if ideal_dcg == 0.0:
        return 0.0
    return actual_dcg / ideal_dcg


def run_evaluation(base_url="http://127.0.0.1:5000",
                   dataset_path="benchmark/relevance_dataset.json",
                   output_path="benchmark/search_quality_report.json",
                   judgments_path="benchmark/judgments.json",
                   delay_between_queries=0.05):
    """
    Execute relevance evaluation across the dataset.
    Strictly observes the ground-truth principle:
    If human judgments do not exist for a query, metrics are labeled 'pending_human_judgment'.
    """
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Dataset not found at {dataset_path}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        queries = json.load(f)

    judgments = {}
    if os.path.exists(judgments_path):
        try:
            with open(judgments_path, "r", encoding="utf-8") as f:
                judgments = json.load(f)
        except Exception:
            judgments = {}

    print(f"============================================================")
    print(f"  VASTUDA 5.1 RELEVANCE EVALUATION HARNESS")
    print(f"  Target: {base_url}")
    print(f"  Queries: {len(queries)} across dataset")
    print(f"  Pre-loaded Judgments: {len(judgments)} query annotations")
    print(f"============================================================\n")

    query_results = []
    latencies = []
    category_metrics = {}
    provider_counts = {}
    total_zero_results = 0
    total_duplicates = 0
    total_local_hits = 0

    has_any_judgments = False
    all_p3 = []
    all_p5 = []
    all_p10 = []
    all_rec10 = []
    all_mrr = []
    all_ndcg10 = []

    for idx, item in enumerate(queries, 1):
        q = item["query"]
        cat = item.get("category", "general")
        lang = item.get("language", "en")

        start = time.perf_counter()
        req_url = f"{base_url}/api/search?q={urllib.parse.quote(q)}"
        results = []
        provider = "unknown"
        status_code = 0
        local_hit_count = 0

        try:
            req = urllib.request.Request(req_url, headers={"User-Agent": "VASTUDA-Relevance-Evaluator/5.1"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                status_code = resp.status
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                provider = data.get("provider", "none")
                if not results and not data.get("instant_answer") and not data.get("direct_nav"):
                    provider = "none"
        except Exception as e:
            status_code = 500
            provider = "error"

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        latencies.append(latency_ms)

        # Check duplicates
        seen_urls = set()
        dup_count = 0
        for r in results:
            u = r.get("url", "").strip()
            if u:
                if u in seen_urls:
                    dup_count += 1
                seen_urls.add(u)
            if r.get("source") == "VASTUDA Local Index" or r.get("provider") == "local_index":
                local_hit_count += 1

        total_duplicates += dup_count
        total_local_hits += local_hit_count
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        if not results:
            total_zero_results += 1

        # Check for human judgments
        q_judgments = judgments.get(q, {})
        has_judgments_for_q = bool(q_judgments and "grades" in q_judgments)
        
        q_p3 = "pending_human_judgment"
        q_p5 = "pending_human_judgment"
        q_p10 = "pending_human_judgment"
        q_rec10 = "pending_human_judgment"
        q_mrr = "pending_human_judgment"
        q_ndcg10 = "pending_human_judgment"

        if has_judgments_for_q:
            has_any_judgments = True
            grades = q_judgments.get("grades", [])  # list of ints (0, 1, 2, 3) for top 10
            # Pad with 0 if fewer grades than results
            while len(grades) < len(results[:10]):
                grades.append(0)
            
            # Binary relevance threshold: 2 or 3 is relevant
            binary_rel = [1 if g >= 2 else 0 for g in grades]
            
            p3 = sum(binary_rel[:3]) / 3.0
            p5 = sum(binary_rel[:5]) / 5.0
            p10 = sum(binary_rel[:10]) / 10.0 if len(binary_rel) >= 10 else (sum(binary_rel) / max(len(binary_rel), 1))
            
            # MRR
            mrr = 0.0
            for r_idx, b in enumerate(binary_rel, 1):
                if b == 1:
                    mrr = 1.0 / r_idx
                    break
            
            ndcg10 = calculate_ndcg(grades[:10], k=10)
            known_relevant = q_judgments.get("total_known_relevant", max(sum(binary_rel), 1))
            rec10 = sum(binary_rel[:10]) / known_relevant if known_relevant > 0 else 0.0

            q_p3 = round(p3, 4)
            q_p5 = round(p5, 4)
            q_p10 = round(p10, 4)
            q_rec10 = round(rec10, 4)
            q_mrr = round(mrr, 4)
            q_ndcg10 = round(ndcg10, 4)

            all_p3.append(p3)
            all_p5.append(p5)
            all_p10.append(p10)
            all_rec10.append(rec10)
            all_mrr.append(mrr)
            all_ndcg10.append(ndcg10)

        # Category accumulation
        if cat not in category_metrics:
            category_metrics[cat] = {
                "count": 0,
                "total_latency": 0.0,
                "local_hits": 0,
                "zero_results": 0,
                "providers": {}
            }
        c_m = category_metrics[cat]
        c_m["count"] += 1
        c_m["total_latency"] += latency_ms
        c_m["local_hits"] += local_hit_count
        if not results:
            c_m["zero_results"] += 1
        c_m["providers"][provider] = c_m["providers"].get(provider, 0) + 1

        query_results.append({
            "id": item.get("id", idx),
            "query": q,
            "category": cat,
            "language": lang,
            "status": status_code,
            "latency_ms": latency_ms,
            "result_count": len(results),
            "provider": provider,
            "local_hits": local_hit_count,
            "duplicates": dup_count,
            "metrics": {
                "precision_at_3": q_p3,
                "precision_at_5": q_p5,
                "precision_at_10": q_p10,
                "recall_at_10": q_rec10,
                "mrr": q_mrr,
                "ndcg_at_10": q_ndcg10
            },
            "top_3_titles": [r.get("title", "") for r in results[:3]],
            "top_3_urls": [r.get("url", "") for r in results[:3]]
        })

        disp_q = (q[:30] + "..") if len(q) > 32 else q.ljust(32)
        status_tag = "OK" if status_code == 200 else "FAIL"
        print(f"  [{idx:03d}/{len(queries)}] {disp_q} | {latency_ms:>7.1f}ms | Prov: {provider:<14} | Res: {len(results):>2}")

        if delay_between_queries > 0:
            time.sleep(delay_between_queries)

    # Compute overall latency percentiles
    latencies.sort()
    n = len(latencies)
    p50 = latencies[int(n * 0.50)] if n > 0 else 0.0
    p95 = latencies[int(n * 0.95)] if n > 0 else 0.0
    mean_lat = round(sum(latencies) / max(n, 1), 2)

    # Compile category averages
    cat_summary = {}
    for c, data in category_metrics.items():
        cnt = data["count"]
        cat_summary[c] = {
            "query_count": cnt,
            "avg_latency_ms": round(data["total_latency"] / max(cnt, 1), 2),
            "local_hits": data["local_hits"],
            "zero_results": data["zero_results"],
            "provider_breakdown": data["providers"]
        }

    report = {
        "evaluation_metadata": {
            "timestamp": int(time.time()),
            "datetime_utc": datetime.utcnow().isoformat() + "Z",
            "target_url": base_url,
            "dataset_path": dataset_path,
            "total_queries": len(queries),
            "judgment_system": {
                "scale": "0=irrelevant, 1=marginally_relevant, 2=relevant, 3=highly_relevant",
                "binary_relevance_threshold": ">= 2",
                "judged_queries_count": len([q for q in query_results if q["metrics"]["precision_at_3"] != "pending_human_judgment"])
            }
        },
        "summary": {
            "total_queries": len(queries),
            "successful_queries": sum(1 for q in query_results if q["status"] == 200),
            "failed_queries": sum(1 for q in query_results if q["status"] != 200),
            "zero_result_queries": total_zero_results,
            "zero_result_rate": round(total_zero_results / max(len(queries), 1), 4),
            "duplicate_urls_found": total_duplicates,
            "duplicate_rate": round(total_duplicates / max(sum(len(q["top_3_urls"]) for q in query_results), 1), 4),
            "total_local_index_hits": total_local_hits,
            "local_index_query_hit_rate": round(sum(1 for q in query_results if q["local_hits"] > 0) / max(len(queries), 1), 4),
            "external_only_fallback_rate": round(sum(1 for q in query_results if q["provider"] in ("tavily", "web", "external")) / max(len(queries), 1), 4),
            "latency_ms": {
                "p50_median": p50,
                "p95": p95,
                "mean": mean_lat,
                "min": latencies[0] if latencies else 0.0,
                "max": latencies[-1] if latencies else 0.0
            },
            "relevance_metrics": {
                "precision_at_3": round(sum(all_p3) / len(all_p3), 4) if all_p3 else None,
                "precision_at_5": round(sum(all_p5) / len(all_p5), 4) if all_p5 else None,
                "precision_at_10": round(sum(all_p10) / len(all_p10), 4) if all_p10 else None,
                "recall_at_10": round(sum(all_rec10) / len(all_rec10), 4) if all_rec10 else None,
                "mrr": round(sum(all_mrr) / len(all_mrr), 4) if all_mrr else None,
                "ndcg_at_10": round(sum(all_ndcg10) / len(all_ndcg10), 4) if all_ndcg10 else None,
                "status": "Human relevance metrics unavailable: 0 queries have been judged. Do not fabricate human judgments." if not all_p3 else "Judged against ground truth"
            },
            "provider_breakdown": provider_counts,
            "category_summaries": cat_summary
        },
        "query_details": query_results
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n============================================================")
    print(f"  EVALUATION COMPLETE")
    print(f"  Queries: {len(queries)} | Success: {report['summary']['successful_queries']}")
    print(f"  Latency: p50={p50}ms, p95={p95}ms, Mean={mean_lat}ms")
    print(f"  Zero-Result Rate: {report['summary']['zero_result_rate'] * 100:.1f}%")
    print(f"  Duplicate Rate: {report['summary']['duplicate_rate'] * 100:.2f}%")
    print(f"  Local Index Query Hit Rate: {report['summary']['local_index_query_hit_rate'] * 100:.1f}%")
    print(f"  External-Only Fallback Rate: {report['summary']['external_only_fallback_rate'] * 100:.1f}%")
    print(f"  Relevance Status: {report['summary']['relevance_metrics']['precision_at_3']}")
    print(f"  Report saved to: {output_path}")
    print(f"============================================================")
    return report


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
    out = sys.argv[2] if len(sys.argv) > 2 else "benchmark/search_quality_report.json"
    ds = sys.argv[3] if len(sys.argv) > 3 else "benchmark/relevance_dataset.json"
    judg = sys.argv[4] if len(sys.argv) > 4 else "benchmark/judgments.json"
    delay = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
    rep = run_evaluation(base_url=target, output_path=out, dataset_path=ds, judgments_path=judg, delay_between_queries=delay)
    # Also save to relevance_report.json for compatibility
    try:
        with open("benchmark/relevance_report.json", "w", encoding="utf-8") as f:
            json.dump(rep, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
