import os
import sys

API_DIR = os.path.dirname(os.path.abspath(__file__))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from _adapter import get_endpoint_app

app = get_endpoint_app("/terms")
application = app
