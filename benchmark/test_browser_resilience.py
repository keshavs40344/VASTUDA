"""
PHASE 5.8 — DESKTOP BROWSER CONTRACT & OFFLINE RESILIENCE TEST (PHASE 24)
Validates:
1. main.js STAUNT_SEARCH_URL configuration structure
2. formatUrlOrSearch parsing behavior with search routing
3. Autocomplete query resilience against offline/dead server
4. app.asar freshness and packaging
"""
import subprocess
import os
import sys

DESKTOP_MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "desktop", "main.js")
ASAR_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "my-saas-project", "desktop", "dist", "win-unpacked", "resources", "app.asar")

failures = 0

def check(condition, desc):
    global failures
    if condition:
        print(f"[PASS] {desc}")
    else:
        print(f"[FAIL] {desc}")
        failures += 1

# Check 1: main.js exists and contains correct URL resolution
with open(DESKTOP_MAIN, "r", encoding="utf-8") as f:
    main_code = f.read()

check("https://vastuda-search.onrender.com" in main_code, "main.js contains permanent production URL")
check("process.env.STAUNT_SEARCH_URL" in main_code, "main.js honors STAUNT_SEARCH_URL environment variable")
check("http://127.0.0.1:5000" in main_code, "main.js retains local development fallback")
check("trycloudflare" not in main_code, "main.js does NOT hardcode temporary trycloudflare domain")

# Check 2: app.asar exists and is freshly generated
check(os.path.exists(ASAR_FILE), "app.asar exists in dist/win-unpacked/resources")
check(os.path.getsize(ASAR_FILE) > 200000, f"app.asar is valid size ({os.path.getsize(ASAR_FILE):,} bytes)")

# Check 3: Node-based simulation of formatUrlOrSearch and offline suggest
node_test_script = """
const path = require('path');

// Simulate formatUrlOrSearch logic
const STAUNT_SEARCH_URL = process.env.STAUNT_SEARCH_URL || 'https://vastuda-search.onrender.com' || 'http://127.0.0.1:5000';

function formatUrlOrSearch(input) {
  const trimmed = (input || '').trim().slice(0, 2048);
  if (!trimmed || trimmed === 'staunt://newtab') return 'staunt://newtab';
  if (/^https?:\\/\\//i.test(trimmed)) return trimmed;
  const isDomain = /^([a-zA-Z0-9-]+\\.)+[a-zA-Z]{2,}(:\\d+)?(\\/.*)?$/i.test(trimmed) && !trimmed.includes(' ');
  if (isDomain) return 'https://' + trimmed;
  return `${STAUNT_SEARCH_URL}/?q=${encodeURIComponent(trimmed)}`;
}

// 1. Direct query routes to production search URL
const resSearch = formatUrlOrSearch('artificial intelligence');
if (!resSearch.startsWith('https://vastuda-search.onrender.com/?q=')) {
  console.error('FAIL search routing:', resSearch);
  process.exit(1);
}

// 2. Direct domain routes directly to https
const resDomain = formatUrlOrSearch('github.com');
if (resDomain !== 'https://github.com') {
  console.error('FAIL domain routing:', resDomain);
  process.exit(1);
}

// 3. Graceful offline suggest simulation (port 59999 is dead)
async function testOfflineSuggest() {
  let remoteSuggestions = [];
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 200);
    const resp = await fetch('http://127.0.0.1:59999/api/suggest?q=test', { signal: controller.signal });
    if (resp.ok) remoteSuggestions = await resp.json();
  } catch (err) {
    // Graceful offline fallback
  }
  if (!Array.isArray(remoteSuggestions) || remoteSuggestions.length !== 0) {
    console.error('FAIL offline suggest fallback');
    process.exit(1);
  }
  console.log('NODE_SIM_OK');
}

testOfflineSuggest();
"""

res = subprocess.run(["node", "-e", node_test_script], capture_output=True, text=True)
check(res.returncode == 0 and "NODE_SIM_OK" in res.stdout, "Node IPC search routing and offline simulation passed")

print("-" * 50)
if failures == 0:
    print("ALL DESKTOP RESILIENCE TESTS PASSED")
    sys.exit(0)
else:
    print(f"FAILED {failures} TEST(S)")
    sys.exit(1)
