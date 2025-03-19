#!/usr/bin/env bash
# Build script for Render

set -o errexit

# Create necessary directories
mkdir -p /tmp/downloads
mkdir -p /tmp/logs

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .

# Print versions for debugging
echo "Python version: $(python --version)"
echo "Aria2 version: $(aria2c --version | head -n 1)"
echo "FFmpeg version: $(ffmpeg -version | head -n 1)"

echo "Build completed successfully!"
