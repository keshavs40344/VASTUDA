import os
import sys
import json
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

BENCHMARK_QUERIES = {
    "informational": [
        "machine learning",
        "what is quantum computing",
        "Indian Constitution",
        "how does DNS work",
        "photosynthesis process",
        "black hole event horizon",
        "solar system planets order",
        "global warming causes",
        "human circulatory system",
        "history of internet"
    ],
    "navigational": [
        "python official website",
        "github login",
        "wikipedia main page",
        "google scholar",
        "stack overflow",
        "npm registry",
        "arxiv preprints",
        "supreme court of india",
        "university of delhi",
        "w3schools python"
    ],
    "academic": [
        "transformer architecture attention is all you need",
        "deep learning nature review",
        "CRISPR gene editing mechanism",
        "theory of relativity summary",
        "quantum entanglement experiment",
        "semiconductor physics basics",
        "economics supply and demand elasticity",
        "sociological theories of urbanization",
        "neuroscience neuroplasticity mechanisms",
        "algorithmic game theory nash equilibrium"
    ],
    "programming": [
        "Python tutorial",
        "Python list comprehension",
        "best Python libraries",
        "javascript async await example",
        "docker compose tutorial",
        "git merge vs rebase",
        "react useEffect hook explained",
        "binary search python implementation",
        "sql inner join vs left join",
        "rust ownership and borrowing"
    ],
    "news": [
        "latest AI news",
        "tech industry layoffs 2026",
        "space mission launches 2026",
        "global renewable energy trends",
        "semiconductor chip manufacturing news",
        "autonomous vehicles regulation",
        "cybersecurity threats report",
        "quantum computing breakthrough",
        "electric vehicles battery innovation",
        "tech startup venture capital updates"
    ],
    "hindi": [
        "भारत का संविधान",
        "कृत्रिम बुद्धिमत्ता क्या है",
        "सौर मंडल के ग्रह",
        "भारत की राजधानी",
        "भारतीय अर्थव्यवस्था का इतिहास",
        "महात्मा गांधी का जीवन परिचय",
        "जलवायु परिवर्तन के प्रभाव",
        "कंप्यूटर कैसे काम करता है",
        "लोकतंत्र का महत्व",
        "अंतरिक्ष अनुसंधान संगठन इसरो"
    ],
    "hinglish": [
        "Python kaise sikhe",
        "website kaise banaye",
        "machine learning kya hota hai",
        "cloud computing ke fayde",
        "programming me career kaise banaye",
        "stock market me invest kaise kare",
        "cybersecurity me job kaise paye",
        "artificial intelligence ka future kya hai",
        "computer networking ke basics",
        "data science roadmap for beginners"
    ],
    "long_tail": [
        "how to optimize sqlite query performance for large datasets",
        "difference between generative adversarial networks and diffusion models",
        "step by step guide to setup cloudflare tunnel on windows",
        "how to calculate compound annual growth rate in python pandas",
        "best practices for handling rate limits in REST API clients",
        "how to configure nginx reverse proxy with ssl certificate",
        "understanding time complexity of red black tree insertion",
        "how to extract text from pdf using python without ocr",
        "architectural differences between microservices and modular monoliths",
        "how does transformer self attention mechanism scale with sequence length"
    ],
    "questions": [
        "what is the speed of light",
        "why is the sky blue",
        "who invented the world wide web",
        "how do airplanes generate lift",
        "why do batteries degrade over time",
        "what is the difference between ram and rom",
        "how does public key cryptography work",
        "why is water a universal solvent",
        "what happens during a solar eclipse",
        "how do search engines index the web"
    ],
    "comparisons": [
        "React vs Vue",
        "Python vs Go",
        "PostgreSQL vs MongoDB",
        "Docker vs Kubernetes",
        "TCP vs UDP",
        "HTTP/2 vs HTTP/3",
        "REST vs GraphQL",
        "Git vs SVN",
        "CPU vs GPU",
        "SSD vs HDD"
    ]
}


def run_single_query(category, query, base_url="http://127.0.0.1:5000"):
    encoded = urllib.parse.quote(query)
    url = f"{base_url}/api/search?q={encoded}"
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VASTUDA-Benchmark/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            latency_ms = round((time.time() - t0) * 1000, 2)
            data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            provider = data.get("provider", "unknown")
            instant_answer = data.get("instant_answer")
            direct_nav = data.get("direct_nav")

            # Check for domain/url duplicates in top 10
            urls = [r.get("url") for r in results if r.get("url")]
            unique_urls = set(urls)
            dup_count = len(urls) - len(unique_urls)
            dup_rate = round(dup_count / max(len(urls), 1), 3)

            # Check if any came from VASTUDA local index
            local_hits = sum(1 for r in results if "local" in str(r.get("source", "")).lower() or "vastuda" in str(r.get("source", "")).lower())

            # Domains present
            domains = list(dict.fromkeys([r.get("domain", "") for r in results if r.get("domain")]))

            return {
                "category": category,
                "query": query,
                "status": 200,
                "latency_ms": latency_ms,
                "provider": provider,
                "results_count": len(results),
                "top_domains": domains[:5],
                "duplicate_rate": dup_rate,
                "local_index_hits": local_hits,
                "has_instant_answer": bool(instant_answer),
                "has_direct_nav": bool(direct_nav),
                "top_3_titles": [r.get("title", "") for r in results[:3]],
                "error": None
            }
    except Exception as e:
        latency_ms = round((time.time() - t0) * 1000, 2)
        return {
            "category": category,
            "query": query,
            "status": 500,
            "latency_ms": latency_ms,
            "provider": "error",
            "results_count": 0,
            "top_domains": [],
            "duplicate_rate": 0.0,
            "local_index_hits": 0,
            "has_instant_answer": False,
            "has_direct_nav": False,
            "top_3_titles": [],
            "error": str(e)
        }


def execute_benchmark(base_url="http://127.0.0.1:5000", output_file="benchmark/baseline_results.json"):
    print("=" * 60)
    print("  VASTUDA SEARCH QUALITY 5.0 — 100-QUERY BENCHMARK")
    print("=" * 60)

    total_queries = sum(len(qlist) for qlist in BENCHMARK_QUERIES.values())
    print(f"Executing {total_queries} queries across {len(BENCHMARK_QUERIES)} categories...")

    all_results = []
    category_summaries = {}

    # Run sequentially with small pause to avoid rate limiting
    start_total = time.time()
    for cat_idx, (cat, qlist) in enumerate(BENCHMARK_QUERIES.items(), 1):
        print(f"\n[{cat_idx}/10] Testing Category: {cat.upper()} ({len(qlist)} queries)...")
        cat_results = []
        for q in qlist:
            res = run_single_query(cat, q, base_url=base_url)
            cat_results.append(res)
            all_results.append(res)
            status_sym = "OK" if res["status"] == 200 else "ERR"
            disp_q = q[:30].encode('ascii', errors='replace').decode('ascii').ljust(30)
            print(f"  [{status_sym}] {disp_q} | {res['latency_ms']}ms | Prov: {res['provider']} | Res: {res['results_count']}")
            time.sleep(0.15)  # 150ms delay

        # Category aggregate
        latencies = [r["latency_ms"] for r in cat_results if r["status"] == 200]
        avg_lat = round(sum(latencies) / max(len(latencies), 1), 2)
        total_res = sum(r["results_count"] for r in cat_results)
        cat_summaries = {
            "query_count": len(qlist),
            "avg_latency_ms": avg_lat,
            "total_results": total_res,
            "avg_results_per_query": round(total_res / len(qlist), 1),
            "local_hits": sum(r["local_index_hits"] for r in cat_results)
        }
        category_summaries[cat] = cat_summaries

    total_time = round(time.time() - start_total, 2)
    successful = [r for r in all_results if r["status"] == 200]
    latencies = sorted([r["latency_ms"] for r in successful])
    median_lat = latencies[len(latencies) // 2] if latencies else 0
    p95_lat = latencies[int(len(latencies) * 0.95)] if latencies else 0

    providers = {}
    for r in successful:
        p = r["provider"]
        providers[p] = providers.get(p, 0) + 1

    overall_summary = {
        "benchmark_timestamp": int(time.time()),
        "total_queries": len(all_results),
        "successful_queries": len(successful),
        "failed_queries": len(all_results) - len(successful),
        "total_execution_time_seconds": total_time,
        "latency_ms": {
            "median": median_lat,
            "p95": p95_lat,
            "mean": round(sum(latencies) / max(len(latencies), 1), 2),
            "min": latencies[0] if latencies else 0,
            "max": latencies[-1] if latencies else 0
        },
        "provider_breakdown": providers,
        "total_local_index_hits": sum(r["local_index_hits"] for r in all_results),
        "category_summaries": category_summaries
    }

    final_payload = {
        "summary": overall_summary,
        "query_results": all_results
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_payload, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("  BENCHMARK COMPLETE")
    print(f"  Queries: {len(all_results)} | Success: {len(successful)} | Failed: {len(all_results) - len(successful)}")
    print(f"  Latency: Median={median_lat}ms, p95={p95_lat}ms, Mean={overall_summary['latency_ms']['mean']}ms")
    print(f"  Providers: {providers}")
    print(f"  Local Index Hits: {overall_summary['total_local_index_hits']}")
    print(f"  Results saved to: {output_file}")
    print("=" * 60)

    return final_payload


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
    out = sys.argv[2] if len(sys.argv) > 2 else "benchmark/baseline_results.json"
    execute_benchmark(base_url=target, output_file=out)
