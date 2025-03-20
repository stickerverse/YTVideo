#!/usr/bin/env bash
# Build script for Render

set -o errexit

echo "Starting build process..."

# Create necessary directories
mkdir -p /tmp/downloads
mkdir -p /tmp/logs
echo "Created temporary directories"

# Create __init__.py files
echo "Creating Python package structure..."
python create_init_files.py

# Install required system dependencies
echo "Installing system dependencies..."
apt-get update
apt-get install -y --no-install-recommends ffmpeg aria2
apt-get clean
rm -rf /var/lib/apt/lists/*

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app
echo "PYTHONPATH: $PYTHONPATH"

# Print current directory structure
echo "Directory structure:"
find . -type d -not -path "*/\.*" | sort

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .

# Install additional packages specifically needed for video processing
pip install --no-cache-dir yt-dlp requests flask flask-cors psutil

# Print debug info
echo "Current directory: $(pwd)"
echo "Python modules:"
python -c "import sys; print('Python path:'); print('\n'.join(sys.path))"
echo "Testing imports..."
python -c "
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
try:
  import youtube_downloader
  print('Successfully imported youtube_downloader')
except ImportError as e:
  print('Failed to import youtube_downloader:', str(e))
"

# Check for necessary executables
echo "Checking for required executables..."
which ffmpeg && echo "ffmpeg found" || echo "ffmpeg NOT found"
which aria2c && echo "aria2c found" || echo "aria2c NOT found"

# Print versions for debugging
echo "Python version: $(python --version)"
if command -v aria2c > /dev/null; then
  echo "Aria2 version: $(aria2c --version | head -n 1)"
else
  echo "Aria2 not installed"
fi
if command -v ffmpeg > /dev/null; then
  echo "FFmpeg version: $(ffmpeg -version | head -n 1)"
else
  echo "FFmpeg not installed"
fi

# Copy the production API code to the right location
echo "Setting up production API..."
cp -f web/api.py web/api.py.bak || true
echo "API backup created"

# Test the API import
echo "Testing API import..."
python -c "
try:
  from web.api import app
  print('Successfully imported app from web.api')
except Exception as e:
  print('Error importing app:', str(e))
"

echo "Build completed successfully!"
