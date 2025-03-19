"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

import os
import sys

# Add the parent directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Flask app from the web/api.py module
from web.api import app

if __name__ == "__main__":
    app.run()
