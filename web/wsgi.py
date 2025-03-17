"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

from api import app

if __name__ == "__main__":
    app.run()