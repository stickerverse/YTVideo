#!/usr/bin/env bash
# Build script for Render

set -o errexit

echo "Starting build process..."

# Create necessary directories
mkdir -p /tmp/downloads
mkdir -p /tmp/logs
echo "Created temporary directories"

# Create __init__.py files
echo "Creating __init__.py files..."
touch __init__.py
mkdir -p youtube_downloader
touch youtube_downloader/__init__.py
for dir in $(find youtube_downloader -type d); do
  touch "$dir/__init__.py"
  echo "Created $dir/__init__.py"
done
mkdir -p web
touch web/__init__.py
echo "Created web/__init__.py"

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app
echo "PYTHONPATH: $PYTHONPATH"

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r web/requirements.txt

# Install the package in development mode with verbose output
echo "Installing the package in development mode..."
pip install -e . -v

# Print debug info
echo "Current directory: $(pwd)"
echo "Directory listing:"
ls -la
echo "Python modules:"
python -c "import sys; print('Python path:'); print('\n'.join(sys.path))"
echo "Testing imports..."
python -c "
import os
import sys
sys.path.insert(0, os.path.abspath('.')); 
try:
  import youtube_downloader
  print('Successfully imported youtube_downloader')
  print('youtube_downloader location:', youtube_downloader.__file__)
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
if command -v ffmpeg > /dev/null; then
  echo "FFmpeg version: $(ffmpeg -version | head -n 1)"
else
  echo "FFmpeg not installed"
fi

echo "Build completed successfully!"
