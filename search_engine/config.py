"""
STAUNT — Configuration Module (Backend)
Provides centralized, safe environment variable retrieval with production fallbacks.
"""
import os
import hashlib
import logging

logger = logging.getLogger("STAUNT_Config")


def get_secret_key(root_dir=None):
    """
    Safely retrieves SECRET_KEY from environment.
    Falls back to a secure key for dev, or logs a clear error and uses
    a stable fallback in production to prevent multi-worker session mismatches.
    """
    raw_key = os.environ.get("SECRET_KEY", "").strip()
    if raw_key:
        return raw_key

    is_prod = (
        os.getenv("FLASK_ENV", "production").lower() in ("production", "prod")
        or bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("VERCEL") or os.getenv("RENDER"))
    )

    if not is_prod:
        logger.warning("[SECURITY] SECRET_KEY not set. Using local development fallback secret.")
        return "staunt-dev-secret-key-32-bytes-long-padding"

    logger.error(
        "[SECURITY] SECRET_KEY environment variable is not set in production! "
        "Set SECRET_KEY in your deployment environment variables (Railway / Render / Vercel) "
        "for persistent, cryptographically secure session state."
    )
    # Generate a deterministic fallback based on deployment location to prevent worker session mismatches
    seed = f"staunt-sovereign-production-key-{root_dir or os.path.dirname(os.path.abspath(__file__))}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()
