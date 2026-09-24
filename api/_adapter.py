"""
STAUNT — Vercel Serverless Endpoint Factory
Wraps the canonical Flask app for specific API routes without mutating global state.
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


def get_endpoint_app(route_path):
    """Returns a standalone WSGI handler routing to route_path."""
    class WSGIEndpoint:
        def __init__(self, target):
            self.target = target

        def __call__(self, environ, start_response):
            environ["SCRIPT_NAME"] = ""
            environ["PATH_INFO"] = self.target
            return flask_app(environ, start_response)

        def __getattr__(self, name):
            return getattr(flask_app, name)

    return WSGIEndpoint(route_path)
