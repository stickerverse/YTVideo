"""
WSGI entry point for running the 4K Video Reaper web application in production.
This file includes enhanced error handling to diagnose startup issues.
"""

import os
import sys
import logging
import traceback

# Configure logging to capture any startup errors
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more verbose logging
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger('wsgi')

# Debug information
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Files in current directory: {os.listdir('.')}")
logger.info(f"Environment variables: PYTHONPATH={os.environ.get('PYTHONPATH')}, DOWNLOAD_DIR={os.environ.get('DOWNLOAD_DIR')}")

# Make sure parent directory and current directory are in Python path
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"Current directory: {current_dir}")
    
    parent_dir = os.path.dirname(current_dir)
    logger.info(f"Parent directory: {parent_dir}")
    
    # Add directories to path if they're not already there
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
        logger.info(f"Added to Python path: {parent_dir}")
    
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
        logger.info(f"Added to Python path: {current_dir}")
    
    # Log all directories in sys.path
    logger.info(f"Full Python path: {sys.path}")
    
    # Check if we can see the web module
    if os.path.exists(os.path.join(parent_dir, 'web')):
        logger.info("Found web module in parent directory")
    else:
        logger.warning("Cannot find web module in parent directory")
        logger.info(f"Contents of parent directory: {os.listdir(parent_dir)}")
except Exception as e:
    logger.error(f"Error setting up Python path: {e}")
    logger.error(traceback.format_exc())

# Create required directories if they don't exist
try:
    download_dir = os.environ.get('DOWNLOAD_DIR', '/tmp/downloads')
    log_dir = os.environ.get('LOG_DIR', '/tmp/logs')
    
    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)
    
    logger.info(f"Created directories: {download_dir}, {log_dir}")
except Exception as e:
    logger.error(f"Error creating directories: {e}")
    logger.error(traceback.format_exc())

# Global variable for the application
app = None

# Import Flask app from the web/api.py module
try:
    logger.info("Attempting to import app from web.api")
    # Try different import approaches
    try:
        from web.api import app
        logger.info("Successfully imported app using relative import")
    except ImportError:
        logger.warning("Relative import failed, trying absolute import")
        try:
            import web.api
            app = web.api.app
            logger.info("Successfully imported app using absolute import")
        except ImportError:
            logger.warning("Absolute import failed, trying alternative approach")
            # If the above fails, try a more direct approach
            import importlib.util
            spec = importlib.util.spec_from_file_location("api", os.path.join(current_dir, "api.py"))
            api_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_module)
            app = api_module.app
            logger.info("Successfully imported app using importlib")
except Exception as e:
    logger.error(f"Failed to import app: {str(e)}")
    logger.error(traceback.format_exc())
    raise

# Check if app was successfully imported
if app is None:
    logger.error("App could not be imported!")
    raise ImportError("Failed to import Flask app from web.api")
else:
    logger.info("WSGI app successfully imported and ready")

if __name__ == "__main__":
    # Run the Flask application directly
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting Flask application on port {port}")
    app.run(host='0.0.0.0', port=port)
