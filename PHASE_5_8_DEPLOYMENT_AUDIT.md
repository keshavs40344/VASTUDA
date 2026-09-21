# PHASE 5.8 DEPLOYMENT AUDIT
# VASTUDA / STAUNT — Production Hardening & Public Infrastructure

**Audit Date:** 2026-09-21  
**Baseline Commit:** `5c8bbf0` (Phase 5.7 frozen)  
**Baseline Tests:** 116/116 PASS (25+25+33+20+13)  
**Search Engine:** Running on `http://127.0.0.1:5000` (task-4844, `python search_engine/server.py`)  
**Temporary Tunnel:** `https://paying-andrews-focused-potential.trycloudflare.com` (task-5128, LIVE ✅)

---

## PHASE 1 — SEARCH ENGINE AUDIT

### Entrypoint
- **`search_engine/server.py`** — 1,345 lines, Flask app
- `app.run(host="0.0.0.0", port=port, debug=False)` only when `__name__ == "__main__"`
- Production WSGI via `wsgi.py` (30 lines) — imports app from `search_engine.server`, inits WAL mode, uses Waitress with 8 threads

### API Endpoints Verified (All HTTP 200)
| Endpoint | Method | Status |
|---|---|---|
| `/` | GET | 200 ✅ |
| `/health` | GET | 200 ✅ |
| `/api/version` | GET | 200 ✅ |
| `/api/suggest?q=python` | GET | 200 ✅ |
| `/api/search?q=python` | GET | 200 ✅ |
| `/api/search` (all categories) | GET | 200 ✅ |
| `/api/overview` | POST | 200 ✅ |
| `/api/images` | GET | 200 ✅ |
| `/api/trending` | GET | 200 ✅ |
| `/api/crawler/stats` | GET | 200 ✅ |
| `/api/reader` | GET | 200 ✅ |

### Rate Limiting
- `is_rate_limited(ip, limit=120, window_sec=60)` — in-memory token bucket per IP
- Applied via `@app.before_request` on all `/api/` paths
- Returns HTTP 429 with JSON `{"error": "Rate limit exceeded.", "status": 429}`
- **ISSUE:** No `Retry-After` header returned on 429

### CORS
- `Access-Control-Allow-Origin: *` — **wildcard** (Phase 14 mandates non-wildcard)
- `Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type, Authorization`

---

## PHASE 2 — PUBLIC API CONTRACT

### `/health` endpoint
```json
{
  "status": "ok",
  "service": "VASTUDA Sovereign Search & Discovery Engine",
  "version": "5.4",
  "timestamp": 1789992179
}
```
**Status:** All 4 required keys present ✅  
**Latency:** 9ms ✅ (no expensive searches)

### `/api/version`
```json
{"app": "VASTUDA", "version": "5.4", "commit": "5c8bbf0", "environment": "production"}
```

---

## PHASE 5 — SQLITE / FTS5 INDEX AUDIT

### Database: `search_engine/vastuda.db`
- **Size:** 3,596,288 bytes main + 32,768 shm + 1,705,712 WAL = **~5.1 MB total**
- **WAL mode:** ENABLED (set via `wsgi.py` on startup)
- **Tables (15):** ai_overview_cache, collections, crawl_queue, documents, documents_fts (FTS5), saved_results, search_analytics, search_history, search_results_cache, sqlite_sequence, users

### Document Counts
| Table | Count |
|---|---|
| documents | 89 |
| documents_fts | 89 |
| crawl_queue | 90 |
| ai_overview_cache | 4 |
| search_results_cache | 2 |
| users | 2 |

**Observation:** Local index is sparse (89 docs). Enough for local testing, thin for production search coverage. Auto-seed runs on startup if < 3 docs.

### Index Persistence
- SQLite file is gitignored (`.gitignore` excludes `*.db`)
- Index **does NOT survive fresh deployments** on platforms like Render that wipe the filesystem
- Backup directory: `backups/` (also gitignored)
- Auto-backup: present in `backup_index.py`

---

## PHASE 6 — PERSISTENT STORAGE LOCATIONS

| Data | Location | Notes |
|---|---|---|
| SQLite / FTS index | `search_engine/vastuda.db` | Local only; gitignored |
| Crawl state | `crawl_queue` table in vastuda.db | Same file |
| AI overview cache | `ai_overview_cache` table | Same file |
| Search result cache | `search_results_cache` table | Same file |
| In-memory search cache | `SEARCH_CACHE = {}` dict | Lost on restart |
| Backups | `backups/` | gitignored |

**Risk:** On Render free tier, the filesystem is ephemeral. SQLite survives restarts of the same instance but is wiped on new deploys. Persistent Disk not available on Render free plan.

---

## PHASE 10 — LATENCY BENCHMARK

**10-query first-hit benchmark (no cache):**

| Query | Latency | Results | Provider |
|---|---|---|---|
| python | 43ms | 10 | hybrid_vastuda (cached) |
| machine learning | 1,708ms | 10 | hybrid_vastuda |
| india | 2,478ms | 10 | hybrid_vastuda |
| how to learn javascript | 1,398ms | 10 | hybrid_vastuda |
| recipe chicken | 1,651ms | 10 | hybrid_vastuda |
| weather today | 1,372ms | 10 | local_index |
| best laptop 2026 | 1,222ms | 10 | local_index |
| artificial intelligence | 1,288ms | 4 | local_index |
| github copilot | 1,313ms | 1 | local_index |
| nepal travel | 1,298ms | 10 | local_index |

**SLA:** p50 = 1,372ms | p95 = 2,478ms | min = 43ms | max = 2,478ms

**Observation:** Cache hit (python) = 43ms ✅. Fresh external queries = 1.2–2.5s (dominated by Tavily/DuckDuckGo provider calls). Local-only fallback = ~1.2–1.4s.

---

## PHASE 11 — SUGGEST ENDPOINT AUDIT

| Input | Status | Suggestions |
|---|---|---|
| Empty (`q=`) | 200 | [] ✅ |
| `q=py` | 200 | 8 suggestions ✅ |
| `q=namaste` | 200 | Hindi suggestions ✅ |
| `q=%40%40%40` | 200 | 8 suggestions (Google fallback) |

---

## PHASE 12 — RATE LIMITING AUDIT

- Rate limit: 120 req/min per IP — in-memory
- HTTP 429 returned with JSON error on breach
- **MISSING:** `Retry-After` header on 429 response
- **MISSING:** separate rate limits for `/api/suggest` vs `/api/search` vs `/api/overview`

---

## PHASE 13 — ZERO TRACKING AUDIT

| Tracker | Status |
|---|---|
| google-analytics | ✅ NOT PRESENT |
| gtag | ✅ NOT PRESENT |
| mixpanel | ✅ NOT PRESENT |
| amplitude | ✅ NOT PRESENT |
| hotjar | ✅ NOT PRESENT |
| segment.io | ✅ NOT PRESENT |
| facebook.com/tr | ✅ NOT PRESENT |

**Result:** Zero tracking ✅

---

## PHASE 14 — CORS AUDIT

| Header | Current Value | Required |
|---|---|---|
| Access-Control-Allow-Origin | `*` (wildcard) | Non-wildcard |
| Access-Control-Allow-Methods | GET, POST, PUT, DELETE, OPTIONS | OK |
| Access-Control-Allow-Headers | Content-Type, Authorization | OK |

**Issue:** CORS is wildcard. Must restrict to specific origins: `https://vastuda.com`, `http://localhost:*`, `app://` (Electron), or the production domain once established.

---

## PHASE 15 — HTTPS AUDIT

- Local: HTTP only (localhost, expected)
- Cloudflare tunnel: HTTPS ✅ (terminated at Cloudflare edge)
- No self-signed certs needed — Cloudflare handles TLS
- HTTP→HTTPS redirect: handled by Cloudflare
- **Status:** PASS via tunnel, N/A for direct self-hosting

---

## PHASE 16 — SECURITY HEADERS AUDIT

| Header | Status | Value |
|---|---|---|
| X-Content-Type-Options | ✅ OK | nosniff |
| X-Frame-Options | ✅ OK | SAMEORIGIN |
| Referrer-Policy | ✅ OK | strict-origin-when-cross-origin |
| Permissions-Policy | ✅ OK | geolocation=(), microphone=(), camera=() |
| Content-Security-Policy | ❌ MISSING | Must add |
| Strict-Transport-Security | ❌ MISSING | Must add (behind HTTPS proxy) |

---

## PHASE 17 — PERMANENT DOMAIN STATUS

**Current Status:** `trycloudflare.com` is temporary. URL changes every restart.

> [!CAUTION]
> **NO PERMANENT DOMAIN EXISTS.**  
> The user has `cloudflared.exe` installed but is using the free Quick Tunnel (`--url` mode) which assigns random temporary subdomains.
>
> To get a permanent domain via Cloudflare Tunnel requires:
> 1. A Cloudflare account (free)
> 2. A domain pointed to Cloudflare (or use `pages.dev`/`workers.dev` free subdomain)
> 3. Named tunnel with fixed UUID
>
> **Alternative: Render.com free deployment** — `render.yaml` already exists. Would give a permanent `*.onrender.com` URL (e.g., `vastuda-search.onrender.com`). Free tier sleeps after 15 min inactivity.

---

## PHASE 18 — DEPLOYMENT FILE INVENTORY

| File | Status | Notes |
|---|---|---|
| `render.yaml` | ✅ EXISTS | Gunicorn, 2 workers, 4 threads, port 10000 |
| `Procfile` | ✅ EXISTS | Same Gunicorn command |
| `wsgi.py` | ✅ EXISTS | Waitress (8 threads), WAL init |
| `requirements.txt` | ✅ EXISTS | Flask, gunicorn, waitress, requests, bs4, groq, dotenv |
| `railway.json` | ✅ EXISTS | Nixpacks, `python wsgi.py`, restart on failure |
| `vercel.json` | ✅ EXISTS | (Serverless — NOT suitable for persistent SQLite) |
| `Dockerfile` | ❌ MISSING | Not present |
| `Caddyfile` / `nginx.conf` | ❌ MISSING | Not needed (Cloudflare handles TLS) |

**Canonical production path: Render.com** (render.yaml already configured with Gunicorn)

---

## PHASE 9 — PROVIDER FAILURE ISOLATION

- `generate_ai_overview`: has extractive zero-token fallback ✅
- `search_with_hybrid_ranking`: falls back to local FTS5 when external providers fail ✅
- Tavily 432/400 errors: caught and logged, not propagated ✅
- DuckDuckGo failures: caught ✅
- Local-only search verified: 10 results from `local_index` provider ✅

---

## PHASE 19 — AUTO-RESTART

- `railway.json`: `"restartPolicyType": "ON_FAILURE"` ✅
- Render: has health check and auto-restart built-in ✅
- Local (current): daemon process, no auto-restart unless scripted

---

## FINDINGS SUMMARY — ITEMS TO FIX

### Critical
1. **CORS wildcard** → Restrict to allowed origins
2. **CSP header missing** → Add Content-Security-Policy
3. **HSTS missing** → Add (only behind HTTPS, with Cloudflare check)
4. **Retry-After header** missing on 429 responses
5. **No permanent domain** → Deploy to Render.com for permanent `*.onrender.com` URL

### Important
6. **`Retry-After` header** on rate limit 429
7. **`SECRET_KEY`** hardcoded default fallback in server.py line 48 → Move to env var
8. **STAUNT browser config** → Update to support env-var production URL (already done via `STAUNT_SEARCH_URL`, but must add Render URL fallback)
9. **Per-endpoint rate limits** → `/api/suggest` and `/api/overview` should have separate, tighter limits

### Informational
10. **Local index is sparse** (89 docs) → Seed crawl on startup handles this
11. **Latency p95 = 2.5s** → Acceptable for free-tier external providers; local cache hits = 43ms
12. **Market data in `/api/trending`** is static hardcoded → acceptable for Phase 5.8

---

## PHASE 0 — BASELINE VERIFICATION

| Test Suite | Tests | Result |
|---|---|---|
| Phase 5.3 | 25 | ✅ 25/25 |
| Phase 5.4 | 25 | ✅ 25/25 |
| Phase 5.6 | 33 | ✅ 33/33 |
| Phase 5.7 | 20 | ✅ 20/20 |
| Step 31 regression | 13 | ✅ 13/13 |
| **Total** | **116** | **✅ 116/116** |
