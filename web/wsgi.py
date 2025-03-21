"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.environ.get('LOG_DIR', '/tmp/logs') + '/wsgi.log')
    ]
)
logger = logging.getLogger(__name__)

# Print environment information for debugging
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Environment variables: DOWNLOAD_DIR={os.environ.get('DOWNLOAD_DIR')}, PYTHONPATH={os.environ.get('PYTHONPATH')}")

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
logger.info(f"Added to Python path: {parent_dir}")

# Add current directory to Python path
sys.path.insert(0, current_dir)
logger.info(f"Added to Python path: {current_dir}")

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

# Log that app is ready
logger.info("WSGI app is ready")

if __name__ == "__main__":
    # Run the Flask application directly
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port)
