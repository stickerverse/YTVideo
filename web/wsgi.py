"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to Python path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
logger.info(f"Added to Python path: {parent_dir}")
logger.info(f"Current Python path: {sys.path}")

try:
    # Import Flask app from the web/api.py module
    logger.info("Attempting to import app from web.api")
    from web.api import app
    logger.info("Successfully imported app")
except Exception as e:
    logger.error(f"Failed to import app: {str(e)}")
    logger.error(f"Error details: {repr(e)}")
    raise

if __name__ == "__main__":
    app.run()
