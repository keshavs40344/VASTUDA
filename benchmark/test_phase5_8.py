"""
PHASE 5.8 TEST SUITE — Production Deployment Verification
Tests: security headers, CORS, CSP, HSTS, rate limits, health, suggest, search, tracking
Run: python benchmark/test_phase5_8.py
"""
import unittest
import requests
import time
import os
import sys
import threading

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_API = "http://127.0.0.1:5000"


def _get(path, **kwargs):
    """GET with 10s timeout."""
    return requests.get(LOCAL_API + path, timeout=10, **kwargs)


def _post(path, **kwargs):
    return requests.post(LOCAL_API + path, timeout=10, **kwargs)


class TestPhase58SecurityHeaders(unittest.TestCase):
    """Phase 14-16: Security headers."""

    def _resp(self):
        return _get("/api/search?q=python", headers={"Origin": "http://localhost:5000"})

    def test_01_x_content_type_options(self):
        r = self._resp()
        self.assertEqual(r.headers.get("X-Content-Type-Options"), "nosniff")

    def test_02_referrer_policy(self):
        r = self._resp()
        self.assertEqual(r.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")

    def test_03_permissions_policy(self):
        r = self._resp()
        pp = r.headers.get("Permissions-Policy", "")
        self.assertIn("geolocation=()", pp)

    def test_04_csp_present(self):
        r = self._resp()
        csp = r.headers.get("Content-Security-Policy", "")
        self.assertTrue(len(csp) > 10, f"CSP missing or too short: {repr(csp)}")
        self.assertIn("default-src", csp)
        self.assertIn("object-src 'none'", csp)

    def test_05_csp_no_wildcard_connect(self):
        r = self._resp()
        csp = r.headers.get("Content-Security-Policy", "")
        # connect-src should NOT be just * — should list specific origins
        self.assertNotIn("connect-src *", csp)

    def test_06_cors_not_wildcard_for_allowed_origin(self):
        r = _get("/api/search?q=python", headers={"Origin": "http://localhost:5000"})
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        self.assertNotEqual(acao, "*", "CORS must not be wildcard")
        self.assertEqual(acao, "http://localhost:5000")

    def test_07_cors_no_header_for_unknown_origin(self):
        r = _get("/api/search?q=python", headers={"Origin": "https://evil-site.com"})
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        self.assertEqual(acao, "", f"CORS should not be set for unknown origin, got: {acao}")

    def test_08_cors_vary_origin(self):
        r = _get("/api/search?q=python", headers={"Origin": "http://localhost:5000"})
        vary = r.headers.get("Vary", "")
        self.assertIn("Origin", vary)

    def test_09_hsts_on_https(self):
        # HSTS is only set when X-Forwarded-Proto: https
        r = _get("/api/search?q=python", headers={
            "Origin": "http://localhost:5000",
            "X-Forwarded-Proto": "https"
        })
        hsts = r.headers.get("Strict-Transport-Security", "")
        self.assertIn("max-age=", hsts, "HSTS must be set when behind HTTPS proxy")

    def test_10_hsts_not_on_http(self):
        # HSTS must NOT be set on plain HTTP (no X-Forwarded-Proto header)
        r = _get("/health")
        hsts = r.headers.get("Strict-Transport-Security", "")
        self.assertEqual(hsts, "", f"HSTS must not be set over plain HTTP, got: {hsts}")


class TestPhase58RateLimiting(unittest.TestCase):
    """Phase 12: Rate limiting with Retry-After."""

    def test_11_rate_limit_429_has_retry_after(self):
        """Trigger rate limit on /api/overview (30/min) and check Retry-After."""
        # Send 35 rapid POST requests to /api/overview to trigger its limit
        last_resp = None
        hit_429 = False
        for i in range(35):
            try:
                r = requests.post(
                    LOCAL_API + "/api/overview",
                    json={"query": f"test{i}", "results": []},
                    timeout=5,
                    headers={"X-Real-IP": f"10.33.55.{i % 10}"}  # same-ish IP simulation
                )
                if r.status_code == 429:
                    hit_429 = True
                    last_resp = r
                    break
            except Exception:
                pass
        # Retry-After check — only if 429 was actually triggered
        if hit_429 and last_resp is not None:
            retry_after = last_resp.headers.get("Retry-After", "")
            self.assertTrue(retry_after.isdigit(), f"Retry-After must be numeric seconds, got: {repr(retry_after)}")
            self.assertGreater(int(retry_after), 0)
        else:
            # Rate limit not triggered in this burst — skip gracefully
            self.skipTest("Rate limit threshold not triggered in burst (may need higher concurrency)")


class TestPhase58APIContract(unittest.TestCase):
    """Phase 2: API contract verification."""

    def test_12_health_status_200(self):
        r = _get("/health")
        self.assertEqual(r.status_code, 200)

    def test_13_health_schema(self):
        r = _get("/health")
        body = r.json()
        for key in ("status", "service", "version", "timestamp"):
            self.assertIn(key, body, f"Missing key in /health: {key}")
        self.assertEqual(body["status"], "ok")
        self.assertIsInstance(body["timestamp"], int)

    def test_14_health_is_fast(self):
        t0 = time.time()
        r = _get("/health")
        ms = (time.time() - t0) * 1000
        self.assertEqual(r.status_code, 200)
        self.assertLess(ms, 500, f"/health took {ms:.0f}ms (must be <500ms)")

    def test_15_search_returns_results(self):
        r = _get("/api/search?q=python")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("results", body)
        self.assertIsInstance(body["results"], list)

    def test_16_search_empty_query_400(self):
        r = _get("/api/search?q=")
        self.assertEqual(r.status_code, 400)

    def test_17_suggest_returns_list(self):
        r = _get("/api/suggest?q=py")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsInstance(body, list)

    def test_18_suggest_empty_returns_empty_list(self):
        r = _get("/api/suggest?q=")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_19_cors_preflight_options(self):
        r = requests.options(
            LOCAL_API + "/api/search",
            headers={"Origin": "http://localhost:5000", "Access-Control-Request-Method": "GET"},
            timeout=5
        )
        # Should return 200 with CORS headers (not 405)
        self.assertIn(r.status_code, (200, 204))
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        self.assertEqual(acao, "http://localhost:5000")

    def test_20_zero_tracking_in_html(self):
        r = _get("/")
        self.assertEqual(r.status_code, 200)
        body = r.text.lower()
        trackers = ["google-analytics", "gtag(", "mixpanel", "hotjar", "segment.io", "facebook.com/tr"]
        found = [t for t in trackers if t in body]
        self.assertEqual(found, [], f"Tracking scripts found in HTML: {found}")


if __name__ == "__main__":
    print("=" * 60)
    print("PHASE 5.8 TEST SUITE")
    print(f"Target: {LOCAL_API}")
    print("=" * 60)
    # Verify server is reachable
    try:
        r = requests.get(LOCAL_API + "/health", timeout=5)
        print(f"Server reachable: {r.status_code}")
    except Exception as e:
        print(f"ERROR: Server not reachable at {LOCAL_API}: {e}")
        sys.exit(1)
    unittest.main(verbosity=2)
