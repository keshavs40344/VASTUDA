"""
VASTUDA Production WSGI Entry Point

Used by:
  - Gunicorn (Render.com): gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
  - Waitress (Railway/local): python wsgi.py

The `app` object is exported for Gunicorn to import directly.
Startup tasks (DB WAL mode, seed crawl) run exactly once during process init.
"""
import os
import sys
import logging

logger = logging.getLogger("VASTUDA_WSGI")

# Add project root to Python path so 'search_engine' package is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# Import Flask app — SECRET_KEY validation runs at import time
from search_engine.server import app
from search_engine import db

# Ensure database is initialized with WAL mode on server startup
try:
    db.init_db()
    with db.get_db() as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
    logger.info("[WSGI] Database initialized: WAL mode enabled.")
except Exception as e:
    logger.warning(f"[WSGI] DB initialization note: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    flask_env = os.environ.get("FLASK_ENV", "production").lower()

    try:
        from waitress import serve
        logger.info(f"[WSGI] Starting VASTUDA with Waitress on 0.0.0.0:{port} (8 threads)...")
        print(f"\n=======================================================")
        print(f"  VASTUDA SEARCH ENGINE — {'DEVELOPMENT' if flask_env != 'production' else 'PRODUCTION'} MODE")
        print(f"  Waitress server: http://0.0.0.0:{port}")
        print(f"  Environment: {flask_env}")
        print(f"=======================================================\n", flush=True)
        serve(app, host="0.0.0.0", port=port, threads=8)
    except ImportError:
        logger.warning("[WSGI] Waitress not installed; falling back to Flask dev server.")
        app.run(host="0.0.0.0", port=port, threaded=True, debug=False)
