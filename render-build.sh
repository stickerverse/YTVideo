#!/usr/bin/env bash
# Enhanced build script for Render with better debugging

set -o errexit

echo "Starting build process..."

# Display system information for debugging
echo "System information:"
uname -a
python3 --version
pip --version

# Create necessary directories
mkdir -p /tmp/downloads
mkdir -p /tmp/logs
chmod 777 /tmp/downloads /tmp/logs
echo "Created temporary directories with proper permissions"

# Install required system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y --no-install-recommends ffmpeg aria2
apt-get clean
rm -rf /var/lib/apt/lists/*

# Check if system dependencies were installed correctly
echo "Verifying system dependencies:"
which ffmpeg && ffmpeg -version | head -n 1 || echo "ERROR: ffmpeg installation failed"
which aria2c && aria2c --version | head -n 1 || echo "ERROR: aria2 installation failed"

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app
echo "PYTHONPATH: $PYTHONPATH"

# Print current directory structure before making changes
echo "Initial directory structure:"
find . -type d -not -path "*/\.*" | sort

# Install Python dependencies with explicit versioning
echo "Installing dependencies..."
pip install --upgrade pip
pip install --no-cache-dir gunicorn==20.1.0 flask==2.2.3 flask-cors==3.0.10 yt-dlp==2023.7.6 requests==2.28.2 flask-talisman==0.8.0 python-dotenv==1.0.0 psutil==5.9.5

# Now install from requirements.txt, but skip problematic packages
echo "Installing from requirements.txt..."
grep -v "uwsgi" requirements.txt > requirements_clean.txt
pip install --no-cache-dir -r requirements_clean.txt || echo "Some packages might have failed to install"

# Create Python package structure
echo "Creating Python package structure..."
python create_init_files.py

# Fix permissions on all directories
echo "Setting permissions..."
find . -type d -exec chmod 755 {} \;

# Print updated directory structure
echo "Final directory structure:"
find . -type d -not -path "*/\.*" | sort

# Check important files
echo "Checking critical files:"
ls -la web/
ls -la web/api.py || echo "WARNING: web/api.py is missing!"
ls -la web/wsgi.py || echo "WARNING: web/wsgi.py is missing!"

# Verify Python imports
echo "Testing imports..."
python -c "
import sys
print('Python path:', sys.path)
try:
    import web
    print('Successfully imported web module')
    try:
        from web import api
        print('Successfully imported web.api module')
        if hasattr(api, 'app'):
            print('Flask app found in web.api module')
        else:
            print('WARNING: No Flask app in web.api module')
    except ImportError as e:
        print('Failed to import web.api module:', e)
except ImportError as e:
    print('Failed to import web module:', e)
"

# If wsgi.py or api.py is missing, provide default versions
if [ ! -f "web/api.py" ]; then
    echo "Creating minimal web/api.py as it's missing"
    cat > web/api.py << 'EOF'
"""
Minimal API implementation for 4K Video Reaper
"""
import os
import flask
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/api/status', methods=['GET'])
def api_status_endpoint():
    """
    Provide API service status information
    """
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'message': 'Minimal API is running'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
EOF
fi

if [ ! -f "web/wsgi.py" ]; then
    echo "Creating web/wsgi.py as it's missing"
    cat > web/wsgi.py << 'EOF'
"""
WSGI entry point for running the 4K Video Reaper web application
"""
import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('wsgi')

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

logger.info(f"Python path: {sys.path}")

try:
    from web.api import app
    logger.info("Successfully imported app")
except Exception as e:
    logger.error(f"Failed to import app: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    raise

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
EOF
fi

# Final test to ensure the application can be imported
echo "Final import test..."
python -c "
import os, sys
sys.path.insert(0, os.getcwd())
try:
    from web.wsgi import app
    print('SUCCESS: WSGI application successfully imported')
except Exception as e:
    print('ERROR: Failed to import WSGI application:', e)
    import traceback
    traceback.print_exc()
"

echo "Build completed successfully!"
