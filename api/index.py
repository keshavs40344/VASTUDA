import os
import sys

# Ensure root directory is on Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from search_engine.server import app

class VercelPathFixer:
    """
    WSGI middleware for Vercel Serverless deployment.
    Vercel edge router passes the original request path in HTTP_X_MATCHED_PATH
    (or HTTP_X_VERCEL_MATCHED_PATH / HTTP_X_FORWARDED_URI), while PATH_INFO
    is rewritten to /api/index. This middleware restores the true PATH_INFO
    and QUERY_STRING so Flask route matching works identically to local & container environments.
    """
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        matched_path = (
            environ.get("HTTP_X_MATCHED_PATH")
            or environ.get("HTTP_X_VERCEL_MATCHED_PATH")
            or environ.get("HTTP_X_FORWARDED_URI")
            or environ.get("REQUEST_URI")
            or environ.get("RAW_URI")
        )
        if matched_path:
            # Strip query string if present and assign to QUERY_STRING
            if "?" in matched_path:
                path_part, query_part = matched_path.split("?", 1)
                environ["PATH_INFO"] = path_part
                if not environ.get("QUERY_STRING"):
                    environ["QUERY_STRING"] = query_part
            else:
                environ["PATH_INFO"] = matched_path

        # If PATH_INFO is /api/index or /api/index.py, map to /
        if environ.get("PATH_INFO") in ("/api/index", "/api/index.py"):
            environ["PATH_INFO"] = "/"

        return self.wsgi_app(environ, start_response)

app.wsgi_app = VercelPathFixer(app.wsgi_app)

# For local testing and Vercel WSGI entry
if __name__ == "__main__":
    app.run()
