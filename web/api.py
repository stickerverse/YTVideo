"""
Simplified API for testing deployment on Render.
"""

import os
import sys
import logging
from flask import Flask, jsonify

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask app
app = Flask(__name__, static_folder='public', static_url_path='')

@app.route('/')
def index():
    """Serve the main page or a simple message."""
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logger.error(f"Error serving index.html: {str(e)}")
        return "4K Video Reaper API - Simplified version for testing"

@app.route('/api/status')
def status():
    """Simple status endpoint for health checks."""
    logger.info("Status endpoint called")
    
    # Print environment and sys.path for debugging
    logger.info(f"Python path: {sys.path}")
    
    return jsonify({
        'success': True,
        'status': 'ok',
        'message': 'API is operational',
        'version': '0.1.0'
    })

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting simplified API on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
