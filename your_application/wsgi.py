"""
Fallback WSGI entry point for hosts configured with default 'gunicorn your_application.wsgi'.
Redirects directly to root wsgi application.
"""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from wsgi import app, application
