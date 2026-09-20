import os
import sys

# Add project directory to Python path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from search_engine.server import app
from search_engine import db

# Ensure database is initialized with WAL mode on server startup
try:
    db.init_db()
    with db.get_db() as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
except Exception as e:
    print(f"[WSGI Startup] DB initialization note: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
