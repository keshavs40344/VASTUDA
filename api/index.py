"""
STAUNT — Vercel Serverless WSGI Adapter
Serves root and UI routes, with middleware path restoration.
"""
import os
import sys

API_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(API_DIR)
SEARCH_ENGINE_DIR = os.path.join(ROOT_DIR, "search-engine")
BACKEND_DIR = os.path.join(SEARCH_ENGINE_DIR, "backend")

for p in (BACKEND_DIR, SEARCH_ENGINE_DIR, ROOT_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

os.environ.setdefault("VERCEL", "1")

from server import app as flask_app


class VercelPathRewriteMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = ""
        matched = (
            environ.get("HTTP_X_MATCHED_PATH") or
            environ.get("HTTP_X_VERCEL_MATCHED_PATH") or
            environ.get("HTTP_X_FORWARDED_URI") or
            environ.get("REQUEST_URI") or
            environ.get("RAW_URI")
        )
        if matched:
            clean = matched.split("?", 1)[0]
            if clean and clean not in ("/api/index", "/api/index.py"):
                environ["PATH_INFO"] = clean
            elif clean in ("/api/index", "/api/index.py"):
                environ["PATH_INFO"] = "/"
            if "?" in matched and not environ.get("QUERY_STRING"):
                environ["QUERY_STRING"] = matched.split("?", 1)[1]
        elif environ.get("PATH_INFO") in ("/api/index", "/api/index.py", ""):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)


flask_app.wsgi_app = VercelPathRewriteMiddleware(flask_app.wsgi_app)
application = flask_app
app = application
