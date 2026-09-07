"""
WSGI configuration for PythonAnywhere
File: /var/www/keshavs40344_pythonanywhere_com_wsgi.py or wsgi.py
"""

import sys
import os

# Add project root to sys.path
path = '/home/keshavs40344/VASTUDA'
if path not in sys.path:
    sys.path.insert(0, path)

from core.web_server import app as application
