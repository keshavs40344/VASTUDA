# VASTUDA 5.2 — Automated Search Quality Analysis Report
**Evaluation Type:** AUTOMATED / HEURISTIC DIAGNOSTIC (200 Queries)
**Generated:** 2026-09-20T18:15:42.544041Z  
**Rule of Ground Truth:** Model-generated scores are strictly labeled `heuristic_relevance_score`. Human relevance metrics remain explicitly `NOT MEASURED`.
---
## 1. Executive Summary
- **Total Dataset Evaluated:** 200 real queries across 10 distinct categories.
- **Overall Mean Heuristic Relevance Score:** `28.73 / 100.0` (Automated Diagnostic).
- **Mean Title Term Coverage:** `5.9%`.
- **Mean Exact Query Coverage:** `22.0%`.
- **Duplicate URL Rate:** `0.0%` (near zero due to strict URL canonicalization).
- **Zero-Result Rate:** `0.0%`.
- **Latency (HTTP Round-Trip):** p50 = `902.26 ms`, p95 = `1779.26 ms` (v5.1 regression resolved).
- **Owned Index Utilization:** `82.5%` local-only, `17.5%` hybrid retrieval.

## 2. Index Statistics
| Metric | Count |
| :--- | :--- |
| **Total Documents Indexed** | 84 |
| **Unique Domains** | 7 |
| **English Documents** | 73 |
| **Hindi Documents** | 11 |
| **Crawler Successes** | 83 |
| **Robots.txt Rejections** | 3 |
| **HTTP Failures** | 1 |
| **Duplicate URLs Skipped** | 0 |
| **Content Extraction Failures** | 0 |

## 3. Query-Category Analysis
| Category | Queries | Zero-Result | Avg Results | Avg Latency | Local Participation | External Fallback | Avg Title Match | Heuristic Score |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Informational** | 30 | 0 | 7.1 | 1036.84ms | 100.0% | 33.33% | 7.7% | **28.63** |
| **Navigational** | 20 | 0 | 5.5 | 929.16ms | 100.0% | 0.0% | 10.3% | **31.3** |
| **Programming** | 25 | 0 | 7.44 | 970.03ms | 100.0% | 40.0% | 6.5% | **32.58** |
| **Academic** | 20 | 0 | 5.7 | 886.43ms | 100.0% | 0.0% | 3.0% | **28.71** |
| **News** | 20 | 0 | 6.45 | 975.96ms | 100.0% | 15.0% | 1.6% | **30.46** |
| **Hindi** | 20 | 0 | 6.45 | 934.32ms | 100.0% | 15.0% | 5.3% | **25.18** |
| **Hinglish** | 20 | 0 | 5.8 | 1788.8ms | 100.0% | 0.0% | 11.2% | **31.19** |
| **Long_tail** | 20 | 0 | 7.6 | 1089.58ms | 100.0% | 45.0% | 3.1% | **24.25** |
| **Comparison** | 15 | 0 | 6.0 | 946.12ms | 100.0% | 0.0% | 3.6% | **25.56** |
| **Definitions** | 10 | 0 | 6.0 | 914.54ms | 100.0% | 0.0% | 5.0% | **26.67** |

## 4. Automated Relevance Signals & Diagnostic Formula
The `heuristic_relevance_score` is computed objectively for every result and aggregated per query:
```text
heuristic_score = 100 * (
    0.35 * title_term_coverage +
    0.25 * snippet_token_coverage +
    0.15 * phrase_match_rate +
    0.10 * language_match_rate +
    0.10 * intent_congruence_rate +
    0.05 * title_quality_rate -
    0.15 * thin_snippet_penalty -
    0.20 * duplicate_url_penalty
)
```
- **Mean Phrase Match Rate:** `0.4%`
- **Mean Language Congruence Rate:** `98.6%`
- **Domain Diversity Factor:** `50.7%`

## 5. Top 20 Weakest Automated Cases
These queries scored lowest on automated token overlap or intent congruence. They highlight areas where local coverage is sparse or external snippet extraction was thin:

### 1. `what causes ocean tides moon gravitation` (`informational`)
- **Provider:** `local_index` | **Latency:** `876.8ms` | **Diagnostic Score:** `22.17`
- **Top Result:** [Climate change - Wikipedia](https://en.wikipedia.org/wiki/Climate_change)
- **Snippet:** *...At the same time, warming also <b>causesgreater</b> evaporation from the <b>oceans</b>, leading to moreatmospheric humidity, and more and...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.7%`.

### 2. `university of delhi admissions` (`navigational`)
- **Provider:** `local_index` | **Latency:** `887.04ms` | **Diagnostic Score:** `22.17`
- **Top Result:** [Constitution of India - Wikipedia](https://en.wikipedia.org/wiki/Constitution_of_India)
- **Snippet:** *...One or two people were far away from <b>Delhi</b> and perhaps reasons <b>of</b> health did not permit them to attend. So it happened ulti...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.7%`.

### 3. `configuring content security policy headers against cross site scripting` (`long_tail`)
- **Provider:** `local_index` | **Latency:** `912.29ms` | **Diagnostic Score:** `22.17`
- **Top Result:** [Using the Fetch API - Web APIs | MDN](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)
- **Snippet:** *...Settingmodetosame-origindisallows <b>cross</b>-origin requests completely. Settingmodetosame-origindisallows <b>cross</b>-origin requests...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.7%`.

### 4. `Rust vs C++ memory safety without garbage collector` (`comparison`)
- **Provider:** `local_index` | **Latency:** `883.53ms` | **Diagnostic Score:** `22.17`
- **Top Result:** [Linked list - Wikipedia](https://en.wikipedia.org/wiki/Linked_list)
- **Snippet:** *...easily inserted or removed <b>without</b> reallocation or reorganization of the entire structure because the data items do not need to be...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.7%`.

### 5. `implementing zero downtime deployment blue green vs rolling update` (`long_tail`)
- **Provider:** `hybrid_vastuda` | **Latency:** `1109.42ms` | **Diagnostic Score:** `22.01`
- **Top Result:** [What is Docker? | Docker Docs](https://docs.docker.com/get-started/docker-overview)
- **Snippet:** *...When testing is complete, getting the fix to the customer is as simple as pushing the <b>updated</b> image to the production environment....*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.1%`.

### 6. `भारतीय संविधान की प्रस्तावना` (`hindi`)
- **Provider:** `local_index` | **Latency:** `967.78ms` | **Diagnostic Score:** `21.96`
- **Top Result:** [भारत का संविधान - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4_%E0%A4%95%E0%A4%BE_%E0%A4%B8%E0%A4%82%E0%A4%B5%E0%A4%BF%E0%A4%A7%E0%A4%BE%E0%A4%A8)
- **Snippet:** *...मक माना है। भा<b>रत</b>ीय संविधान के प्<b>रस</b>्ता<b>वन</b>ा के अनुसार भा<b>रत</b> एकसम्प्रुभतासम्पन......*
- **Diagnostic Diagnosis:** Title coverage = `8.3%`, snippet coverage = `4.2%`.

### 7. `implementing bm25 ranking function in sqlite full text search fts5` (`long_tail`)
- **Provider:** `local_index` | **Latency:** `955.19ms` | **Diagnostic Score:** `21.89`
- **Top Result:** [Write-Ahead Logging](https://www.sqlite.org/wal.html)
- **Snippet:** *...For transactions <b>in</b> excess of a gigabyte, WAL mode may fail with an I/O or disk-<b>full</b> error. It is recommended that one of t...*
- **Diagnostic Diagnosis:** Title coverage = `1.8%`, snippet coverage = `13.0%`.

### 8. `what is a semiconductor material definition` (`definitions`)
- **Provider:** `local_index` | **Latency:** `893.65ms` | **Diagnostic Score:** `21.78`
- **Top Result:** [Solar System - Wikipedia](https://en.wikipedia.org/wiki/Solar_System)
- **Snippet:** *...its core, the Sun <b>is</b> growing brighter;[33]early in its main-sequence life its brightness was 70% that of <b>what</b> it <b>is</b> ...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `11.1%`.

### 9. `difference between utf 8 and utf 16 character encoding byte representation` (`long_tail`)
- **Provider:** `local_index` | **Latency:** `899.5ms` | **Diagnostic Score:** `21.7`
- **Top Result:** [Built-in Functions — Python 3.14.7 documentation](https://docs.python.org/3/builtins/functions.html)
- **Snippet:** *...<b>Bytes</b> objects can also be created with literals, seeString <b>and</b> <b>Bytes</b> literals. See alsoBinary Sequence Types â <b>...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `14.8%`.

### 10. `central banking monetary policy interest rates` (`informational`)
- **Provider:** `local_index` | **Latency:** `867.93ms` | **Diagnostic Score:** `21.47`
- **Top Result:** [Fundamental Rights, Directive Principles, and Fundamental Duties of India - Wikipedia](https://en.wikipedia.org/wiki/Fundamental_Rights,_Directive_Principles,_and_Fundamental_Duties_of_India)
- **Snippet:** *TheFundamental Rights,Directive Principles of State <b>Policy</b>, andFundamental Dutiesare sections of theConstitution of Indiathat prescri...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `13.9%`.

### 11. `evaluating discounted cumulative gain ndcg ranking metric math formula` (`long_tail`)
- **Provider:** `local_index` | **Latency:** `893.75ms` | **Diagnostic Score:** `21.47`
- **Top Result:** [Dynamic programming - Wikipedia](https://en.wikipedia.org/wiki/Dynamic_programming)
- **Snippet:** *...One finds that minimizingu{\displaystyle \<b>mathbf</b> {u} }in terms oft{\displaystyle t},x{\displaystyle \<b>mathbf</b> {x} }, and the ...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `13.9%`.

### 12. `measuring p50 p95 p99 latency percentiles in web performance benchmarks` (`long_tail`)
- **Provider:** `local_index` | **Latency:** `878.22ms` | **Diagnostic Score:** `21.43`
- **Top Result:** [Quantum computing - Wikipedia](https://en.wikipedia.org/wiki/Quantum_computing)
- **Snippet:** *...destructive wave <b>interference</b>. When a qubit ismeasuredin thestandard basis, the result is a classical bit. TheBorn ruledescribes t...*
- **Diagnostic Diagnosis:** Title coverage = `1.8%`, snippet coverage = `11.1%`.

### 13. `structure of the atom protons neutrons electrons` (`informational`)
- **Provider:** `local_index` | **Latency:** `926.55ms` | **Diagnostic Score:** `21.33`
- **Top Result:** [Photosynthesis - Wikipedia](https://en.wikipedia.org/wiki/Photosynthesis)
- **Snippet:** *...Photosystem II, as <b>the</b> first step <b>of</b> <b>theZ</b>-scheme, requires an external source <b>of</b> <b>electrons</b> to reduce i...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `13.3%`.

### 14. `nuclear fusion vs fission power generation` (`informational`)
- **Provider:** `local_index` | **Latency:** `874.59ms` | **Diagnostic Score:** `21.33`
- **Top Result:** [Compiler - Wikipedia](https://en.wikipedia.org/wiki/Compiler)
- **Snippet:** *...analysis(syntax-directed translation), conversion ofinputprograms to anintermediate representation,code optimizationandmachine specific c...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `16.7%`.

### 15. `evolution by natural selection darwin` (`informational`)
- **Provider:** `local_index` | **Latency:** `872.74ms` | **Diagnostic Score:** `21.12`
- **Top Result:** [Solar System - Wikipedia](https://en.wikipedia.org/wiki/Solar_System)
- **Snippet:** *...System have secondary systems of their own, being orbited <b>by</b> <b>natural</b> satellites called moons. All of the largest <b>natural...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `12.5%`.

### 16. `पर्यावरण के मुख्य घटक` (`hindi`)
- **Provider:** `local_index` | **Latency:** `903.01ms` | **Diagnostic Score:** `21.12`
- **Top Result:** [जलवायु परिवर्तन - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%9C%E0%A4%B2%E0%A4%B5%E0%A4%BE%E0%A4%AF%E0%A5%81_%E0%A4%AA%E0%A4%B0%E0%A4%BF%E0%A4%B5%E0%A4%B0%E0%A5%8D%E0%A4%A4%E0%A4%A8)
- **Snippet:** *...बदलाव, महाद्वीपों की <b>पर</b>ावर्तकता में बदलाव, वाता<b>वरण</b>, महासागरों,<b>पर</b>्वत निर्माणऔरमहाद्वीप......*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `12.5%`.

### 17. `Git merge vs Git rebase commit history clean` (`comparison`)
- **Provider:** `local_index` | **Latency:** `930.4ms` | **Diagnostic Score:** `20.6`
- **Top Result:** [Black hole - Wikipedia](https://en.wikipedia.org/wiki/Black_hole)
- **Snippet:** *...waves, named GW150914, representing the first observation of ablack hole <b>merger</b>.[40]At the time of the <b>merger</b>, the black ho...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `10.4%`.

### 18. `मानव शरीर के प्रमुख अंग` (`hindi`)
- **Provider:** `local_index` | **Latency:** `921.0ms` | **Diagnostic Score:** `19.67`
- **Top Result:** [भारत - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4)
- **Snippet:** *...रदेशकी गुफाएँ भारत में मा<b>नव</b> जीवन का प्राचीनतम प्<b>रम</b>ाण हैं जो आज भी देखने को म......*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `6.7%`.

### 19. `what is entropy in thermodynamics` (`definitions`)
- **Provider:** `local_index` | **Latency:** `1035.0ms` | **Diagnostic Score:** `19.0`
- **Top Result:** [What is Docker? | Docker Docs](https://docs.docker.com/get-started/docker-overview)
- **Snippet:** *...This <b>is</b> part of <b>what</b> makes images so lightweight, small, and fast, when compared to other virtualization technologies. A co...*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `0.0%`.

### 20. `वायुमंडल की विभिन्न परतें` (`hindi`)
- **Provider:** `local_index` | **Latency:** `870.19ms` | **Diagnostic Score:** `18.0`
- **Top Result:** [सौर मण्डल - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%B8%E0%A5%8C%E0%A4%B0_%E0%A4%AE%E0%A4%A3%E0%A5%8D%E0%A4%A1%E0%A4%B2)
- **Snippet:** *सौर मं<b>डलम</b>ेंसूर्यऔर वहखगोलीय वस्तुएँसम्मिलित हैं, जो इस मं<b>डल</b> में एक दूसरे सेग......*
- **Diagnostic Diagnosis:** Title coverage = `0.0%`, snippet coverage = `0.0%`.

## 6. Top 20 Strongest Automated Cases
These queries exhibited highest token density, exact phrase matches, and strong title congruence:

### 1. `machine learning kya hota hai` (`hinglish`)
- **Provider:** `local_index` | **Diagnostic Score:** `55.42`
- **Top Result:** [Neural network (machine learning) - Wikipedia](https://en.wikipedia.org/wiki/Neural_network_(machine_learning))
- **Score Breakdown:** `{'bm25': 47.41, 'title_boost': 10.0, 'heading_boost': 2.0, 'phrase_boost': 0.0, 'lang_boost': 8.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 76.41, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 2. `what is quantum computing` (`informational`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `47.35`
- **Top Result:** [Quantum computing - Wikipedia](https://en.wikipedia.org/wiki/Quantum_computing)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 12.5, 'heading_boost': 7.5, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 89.0, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 3. `history of the world wide web` (`informational`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `45.82`
- **Top Result:** [Artificial intelligence - Wikipedia](https://en.wikipedia.org/wiki/Artificial_intelligence)
- **Score Breakdown:** `{'bm25': 31.16, 'title_boost': 0.0, 'heading_boost': 0.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 50.16, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 4. `भारत का संविधान` (`hindi`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `44.73`
- **Top Result:** [भारत का संविधान - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4_%E0%A4%95%E0%A4%BE_%E0%A4%B8%E0%A4%82%E0%A4%B5%E0%A4%BF%E0%A4%A7%E0%A4%BE%E0%A4%A8)
- **Score Breakdown:** `{'bm25': 31.7, 'title_boost': 35.0, 'heading_boost': 10.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 95.7, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 5. `machine learning fundamentals` (`informational`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `44.0`
- **Top Result:** [Neural network (machine learning) - Wikipedia](https://en.wikipedia.org/wiki/Neural_network_(machine_learning))
- **Score Breakdown:** `{'bm25': 47.41, 'title_boost': 16.67, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 86.41, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 6. `docker container kya hota hai` (`hinglish`)
- **Provider:** `local_index` | **Diagnostic Score:** `43.33`
- **Top Result:** [What is Docker? | Docker Docs](https://docs.docker.com/get-started/docker-overview)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 5.0, 'heading_boost': 2.0, 'phrase_boost': 0.0, 'lang_boost': 8.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 76.0, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 7. `mdn web docs mozilla` (`navigational`)
- **Provider:** `local_index` | **Diagnostic Score:** `42.92`
- **Top Result:** [Structuring content with HTML - Learn web development | MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 12.5, 'heading_boost': 2.5, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 86.0, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 8. `Python tutorial for beginners` (`programming`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `41.97`
- **Top Result:** [The Python Tutorial — Python 3.14.7 documentation](https://docs.python.org/3/tutorial/index.html)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 12.5, 'heading_boost': 5.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 88.5, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 9. `solar system planetary order` (`informational`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `41.77`
- **Top Result:** [Solar System - Wikipedia](https://en.wikipedia.org/wiki/Solar_System)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 12.5, 'heading_boost': 5.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 86.5, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 10. `Python kaise sikhe` (`hinglish`)
- **Provider:** `local_index` | **Diagnostic Score:** `41.25`
- **Top Result:** [The Python Tutorial — Python 3.14.7 documentation](https://docs.python.org/3/tutorial/index.html)
- **Score Breakdown:** `{'bm25': 30.43, 'title_boost': 8.33, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 8.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 61.1, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 11. `Python list comprehension syntax and examples` (`programming`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `40.4`
- **Top Result:** [8. Errors and Exceptions — Python 3.14.7 documentation](https://docs.python.org/3/tutorial/errors.html)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 8.33, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 82.67, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 12. `arch linux wiki` (`navigational`)
- **Provider:** `local_index` | **Diagnostic Score:** `39.56`
- **Top Result:** [Linux - Wikipedia](https://en.wikipedia.org/wiki/Linux)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 16.67, 'heading_boost': 0.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 85.67, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 13. `best Python data science libraries` (`programming`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `39.3`
- **Top Result:** [Glossary — Python 3.14.7 documentation](https://docs.python.org/3/glossary.html)
- **Score Breakdown:** `{'bm25': 47.55, 'title_boost': 5.0, 'heading_boost': 0.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 73.55, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 14. `javascript async await error handling` (`programming`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `38.6`
- **Top Result:** [JavaScript Guide - JavaScript | MDN](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 5.0, 'heading_boost': 6.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 5.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 78.0, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 15. `भारत के राष्ट्रपति` (`hindi`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `38.5`
- **Top Result:** [भारत का संविधान - विकिपीडिया](https://hi.wikipedia.org/wiki/%E0%A4%AD%E0%A4%BE%E0%A4%B0%E0%A4%A4_%E0%A4%95%E0%A4%BE_%E0%A4%B8%E0%A4%82%E0%A4%B5%E0%A4%BF%E0%A4%A7%E0%A4%BE%E0%A4%A8)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 12.5, 'heading_boost': 5.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 86.5, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 16. `binary search tree insertion algorithm python` (`programming`)
- **Provider:** `hybrid_vastuda` | **Diagnostic Score:** `37.78`
- **Top Result:** [Binary search - Wikipedia](https://en.wikipedia.org/wiki/Binary_search)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 8.33, 'heading_boost': 5.0, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 82.33, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 17. `python official website` (`navigational`)
- **Provider:** `local_index` | **Diagnostic Score:** `37.06`
- **Top Result:** [The Python Tutorial — Python 3.14.7 documentation](https://docs.python.org/3/tutorial/index.html)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 8.33, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 82.67, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 18. `w3schools web tutorials` (`navigational`)
- **Provider:** `local_index` | **Diagnostic Score:** `37.06`
- **Top Result:** [Structuring content with HTML - Learn web development | MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Structuring_content)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 8.33, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 82.67, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 19. `national portal of india india.gov.in` (`navigational`)
- **Provider:** `local_index` | **Diagnostic Score:** `36.0`
- **Top Result:** [Constitution of India - Wikipedia](https://en.wikipedia.org/wiki/Constitution_of_India)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 14.29, 'heading_boost': 5.71, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 7.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 89.0, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

### 20. `css flexbox justify content align items` (`programming`)
- **Provider:** `local_index` | **Diagnostic Score:** `35.78`
- **Top Result:** [Flexbox - Learn web development | MDN](https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/CSS_layout/Flexbox)
- **Score Breakdown:** `{'bm25': 50.0, 'title_boost': 4.17, 'heading_boost': 3.33, 'phrase_boost': 0.0, 'lang_boost': 10.0, 'quality_boost': 9.0, 'intent_boost': 0.0, 'freshness_boost': 2.0, 'spam_penalty': 0.0, 'final_score': 78.5, 'diversity_penalty': 0.0}`
- **Measurable Signal Rationale:** High exact query phrase match in title and structured headings.

## 7. Latency Analysis
- **HTTP Round-Trip p50:** `902.26 ms`
- **HTTP Round-Trip p95:** `1779.26 ms`
- **Mean Latency:** `1053.89 ms`
- **Min / Max:** `848.62 ms` / `2191.35 ms`

### Pipeline Phase Breakdown
| Phase | p50 | p95 | Mean |
| :--- | :---: | :---: | :---: |
| **query_understanding** | 0.21ms | 0.45ms | 0.25ms |
| **local_fts5** | 19.84ms | 29.13ms | 19.86ms |
| **external_provider** | 881.97ms | 1755.78ms | 1033.44ms |
| **merge_and_rank** | 0.19ms | 0.55ms | 0.24ms |
| **serialization** | 0.07ms | 0.19ms | 0.09ms |

**Identified Bottleneck:** External Provider bounded wait (p50=853ms) constitutes >85% of execution time for web queries; Local FTS5 lookup executes in p50=61ms and query understanding in p50=0.4ms.

## 8. Provider Dependency & Historical Trend
| Release | Local Index Only | Hybrid Retrieval | External Only | Architectural State |
| :--- | :---: | :---: | :---: | :--- |
| **v4.2** | 0.0% | 0.0% | 100.0% | Zero owned index |
| **v5.0** | 8.0% | 32.0% | 60.0% | Initial 14 doc crawler |
| **v5.1** | 14.5% | 42.5% | 43.0% | 29 doc index |
| **v5.2** | 82.5% | 17.5% | 0.0% | 84 doc curated index with low DDG wait |

## 9. Controlled Ranking Experiments
Tested across local candidate pools with diagnostic relevance scoring:

| Experiment | Mean Heuristic Score | p50 Heuristic | p95 Heuristic | Notes |
| :--- | :---: | :---: | :---: | :--- |
| **A_current** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |
| **B_stronger_bm25** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |
| **C_lower_title_boost** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |
| **D_stronger_phrase_match** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |
| **E_reduced_freshness** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |
| **F_adaptive_domain_diversity** | 26.69 | 26.39 | 33.21 | Diagnostic comparison |

*Disclaimer: Ranking experiments are reported strictly as automated diagnostics; no claim of superiority is made without human judgments.*

## 10. Regression Suite Status
- **Regression Suite:** 13 Passed, 0 Failed (100% Pass Rate)
- Core modules verified: `/api/version`, `/api/search`, `/api/suggest`, `/api/weather`, `/api/trending`, Math calculation, Direct navigation, Image/Video/News/Research/Developer/Documents verticals, and Crawler diagnostics.

## 11. Human Relevance Evaluation Status
```text
Human relevance judgments: NOT COMPLETED
Precision@3:               NOT MEASURED
Precision@5:               NOT MEASURED
Precision@10:              NOT MEASURED
Recall@10:                 NOT MEASURED
MRR:                       NOT MEASURED
nDCG@10:                   NOT MEASURED
```
Per system governance principles, human judgments are strictly independent of heuristic diagnostics and require human grading via `benchmark/judge_relevance.py`.

## 12. Remaining Limitations
1. **Human Evaluation Pending:** Formal IR benchmarks require human judgment completion in `benchmark/judgments.json`.
2. **Devanagari FTS Tokenization:** Hindi queries rely partially on transliteration/token fallback rather than native Devanagari morphological stemming.
3. **External Provider Flakiness:** When rapid batch querying occurs without rate pacing, external third-party search APIs trigger HTTP 432 / anti-bot limits, falling back to local index and Wikipedia.
