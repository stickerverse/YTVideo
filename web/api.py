"""
4K Video Reaper - Minimal API
-----------------------------

This is a minimal version of the API with just the essential endpoints
to ensure the service can start and respond to health checks.
"""

import os
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Basic configuration
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/tmp/downloads')
LOG_DIR = os.environ.get('LOG_DIR', '/tmp/logs')

# Create necessary directories
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

@app.route('/')
def home():
    """Home page redirect to status"""
    return jsonify({
        'message': 'Welcome to 4K Video Reaper API',
        'status': 'ok',
        'endpoints': ['/api/status', '/api/video-info', '/api/download']
    })

@app.route('/api/status', methods=['GET'])
def api_status():
    """API status endpoint for health checks"""
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'environment': os.environ.get('ENVIRONMENT', 'development'),
        'download_dir': DOWNLOAD_DIR,
        'log_dir': LOG_DIR
    })

@app.route('/api/video-info', methods=['GET'])
def video_info():
    """Get video information from URL"""
    url = request.args.get('url')
    
    if not url:
        return jsonify({
            'error': 'URL parameter is required',
            'status': 'error'
        }), 400
    
    # Return mock data for now
    return jsonify({
        'status': 'success',
        'data': {
            'title': 'Sample Video',
            'duration': 120,
            'formats': [
                {
                    'format_id': 'best',
                    'resolution': '1080p',
                    'ext': 'mp4'
                }
            ]
        }
    })

@app.route('/api/download', methods=['POST'])
def download():
    """Download a video"""
    data = request.json
    
    if not data or 'url' not in data:
        return jsonify({
            'error': 'URL is required',
            'status': 'error'
        }), 400
    
    # Return mock download ID
    return jsonify({
        'status': 'success',
        'downloadId': 'mock-123456',
        'message': 'Download started'
    })

@app.route('/api/download-status', methods=['GET'])
def download_status():
    """Check download status"""
    download_id = request.args.get('id')
    
    if not download_id:
        return jsonify({
            'error': 'Download ID is required',
            'status': 'error'
        }), 400
    
    # Return mock status
    return jsonify({
        'status': 'success',
        'data': {
            'id': download_id,
            'status': 'completed',
            'progress': 100,
            'file_path': os.path.join(DOWNLOAD_DIR, 'sample.mp4')
        }
    })

# Error handlers
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    logger.error(f"Server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500

# Run the app
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
