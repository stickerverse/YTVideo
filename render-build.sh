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

# Print versions for debugging
echo "Python version: $(python --version)"
if command -v aria2c > /dev/null; then
  echo "Aria2 version: $(aria2c --version | head -n 1)"
else
  echo "Aria2 not installed"
fi

echo "Build completed successfully!"
