"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
logger.info(f"Added to Python path: {parent_dir}")

# Add current directory to Python path
sys.path.insert(0, current_dir)
logger.info(f"Added to Python path: {current_dir}")

# Display the Python path for debugging
logger.info(f"Python path: {sys.path}")

try:
    # Import Flask app from the web/api.py module
    logger.info("Attempting to import app from web.api")
    from web.api import app
    logger.info("Successfully imported app")
except Exception as e:
    logger.error(f"Failed to import app: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    raise

if __name__ == "__main__":
    app.run()
