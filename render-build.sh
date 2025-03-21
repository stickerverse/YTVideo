#!/usr/bin/env bash
# Build script with fixed versions for Render

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

# Install Python dependencies with pinned versions for compatibility
echo "Installing dependencies..."
pip install --upgrade pip

# First install Werkzeug with the correct version
echo "Installing Werkzeug 2.2.3 (compatible with Flask 2.2.3)..."
pip install Werkzeug==2.2.3

# Then install other dependencies with pinned versions
echo "Installing other dependencies with compatible versions..."
pip install --no-cache-dir \
    Flask==2.2.3 \
    gunicorn==20.1.0 \
    flask-cors==3.0.10 \
    yt-dlp==2023.7.6 \
    requests==2.28.2 \
    flask-talisman==0.8.0 \
    python-dotenv==1.0.0 \
    psutil==5.9.5 \
    python-json-logger==2.0.7 \
    Flask-Limiter==3.3.1

# Create a requirements.txt file with these pinned versions
echo "Creating pinned-requirements.txt..."
cat > pinned-requirements.txt << EOF
Werkzeug==2.2.3
Flask==2.2.3
gunicorn==20.1.0
flask-cors==3.0.10
yt-dlp==2023.7.6
requests==2.28.2
flask-talisman==0.8.0
python-dotenv==1.0.0
psutil==5.9.5
python-json-logger==2.0.7
Flask-Limiter==3.3.1
EOF

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

# Check installed package versions
echo "Installed Python packages:"
pip freeze | grep -E 'Flask|Werkzeug|gunicorn|flask-cors|yt-dlp'

# Final test to ensure the application can be imported
echo "Final import test..."
python -c "
import os, sys
sys.path.insert(0, os.getcwd())
try:
    import werkzeug
    print(f'Werkzeug version: {werkzeug.__version__}')
    import flask
    print(f'Flask version: {flask.__version__}')
    print('Attempting to import web.wsgi...')
    from web.wsgi import app
    print('SUCCESS: WSGI application successfully imported')
except Exception as e:
    print('ERROR: Failed to import WSGI application:', e)
    import traceback
    traceback.print_exc()
"

echo "Build completed successfully!"
