"""
STAUNT — Vercel Serverless WSGI Adapter
Imports the ONE canonical Flask application instance.
"""
import os
import sys
import urllib.parse

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(API_DIR)
SEARCH_ENGINE_DIR = os.path.join(ROOT_DIR, "search-engine")
BACKEND_DIR = os.path.join(SEARCH_ENGINE_DIR, "backend")

for p in (BACKEND_DIR, SEARCH_ENGINE_DIR, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("VERCEL", "1")

from server import app


class VercelPathRewriteMiddleware:
    """
    Ensures that when Vercel routes using internal rewrites to /api/index,
    Flask uses the actual original requested path from '__vercel_route__'
    or fallback headers.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = ""
        qs_raw = environ.get("QUERY_STRING", "")

        # 1. Primary path extraction: query parameter injected by vercel.json rewrite
        if "__vercel_route__=" in qs_raw:
            params = urllib.parse.parse_qs(qs_raw, keep_blank_values=True)
            if "__vercel_route__" in params:
                route = params["__vercel_route__"][0]
                if not route.startswith("/"):
                    route = "/" + route
                if route.startswith("//"):
                    route = "/" + route.lstrip("/")
                environ["PATH_INFO"] = route if route else "/"
                del params["__vercel_route__"]
                environ["QUERY_STRING"] = urllib.parse.urlencode(params, doseq=True)
        else:
            # 2. Fallback to proxy headers if present
            matched_path = (
                environ.get("HTTP_X_MATCHED_PATH") or
                environ.get("HTTP_X_VERCEL_MATCHED_PATH") or
                environ.get("HTTP_X_FORWARDED_URI") or
                environ.get("REQUEST_URI") or
                environ.get("RAW_URI")
            )
            if matched_path:
                clean_path = matched_path.split("?", 1)[0]
                if clean_path and clean_path not in ("/api/index", "/api/index.py"):
                    environ["PATH_INFO"] = clean_path
                elif clean_path in ("/api/index", "/api/index.py"):
                    environ["PATH_INFO"] = "/"
                if "?" in matched_path and not environ.get("QUERY_STRING"):
                    environ["QUERY_STRING"] = matched_path.split("?", 1)[1]
            elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py"):
                environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


# Wrap Flask's wsgi_app to preserve all Flask application attributes and methods
app.wsgi_app = VercelPathRewriteMiddleware(app.wsgi_app)

# Authoritative WSGI references
application = app
app = application
