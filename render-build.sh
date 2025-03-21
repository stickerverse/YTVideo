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
pip install --no-cache-dir yt-dlp requests flask flask-cors psutil flask-talisman

# Remove mock code from JavaScript files
echo "Removing mock code from frontend files..."
sed -i '/\/\/ For demo purposes only/,/}/d' web/public/script.js
sed -i '/\/\/ For demo purposes only/,/}/d' web/public/app.js
sed -i '/getMockVideoInfo/,/}/d' web/public/script.js
sed -i '/getMockVideoInfo/,/}/d' web/public/app.js
sed -i '/startMockDownload/,/}/d' web/public/script.js
sed -i '/startMockDownload/,/}/d' web/public/app.js
sed -i '/startMockBatchDownload/,/}/d' web/public/script.js
sed -i '/startMockBatchDownload/,/}/d' web/public/app.js
sed -i '/mockDownloads/d' web/public/script.js
sed -i '/mockDownloads/d' web/public/app.js
sed -i '/showApiUnavailableMessage/,/}/d' web/public/script.js
sed -i '/showApiUnavailableMessage/,/}/d' web/public/app.js
sed -i '/checkApiStatus/,/}/d' web/public/script.js
sed -i '/checkApiStatus/,/}/d' web/public/app.js

# Optimize frontend assets
echo "Optimizing frontend assets..."
mkdir -p web/public/build

# Minify CSS (basic minification)
cat web/public/styles.css | \
  sed 's/\/\*.*\*\///g' | \
  sed 's/^\s*//g' | \
  sed 's/\s*$//g' | \
  sed 's/\s*{\s*/\{/g' | \
  sed 's/\s*}\s*/\}/g' | \
  sed 's/\s*:\s*/:/g' | \
  sed 's/\s*;\s*/;/g' | \
  sed 's/,\s*/,/g' | \
  tr -d '\n' > web/public/styles.min.css

# Copy JS (basic minification not included to avoid breaking code)
cp web/public/script.js web/public/script.min.js

# Update index.html to use minified files
TIMESTAMP=$(date +%s)
sed -e "s/styles\.css/styles.min.css?v=${TIMESTAMP}/g" \
    -e "s/script\.js/script.min.js?v=${TIMESTAMP}/g" \
    web/public/index.html > web/public/index.html.new
mv web/public/index.html.new web/public/index.html

# Set up auto-cleanup for /tmp/downloads
echo "Setting up cleanup job..."
cat > /tmp/cleanup.sh << 'EOF'
#!/bin/bash
find /tmp/downloads -type f -mtime +1 -delete
EOF
chmod +x /tmp/cleanup.sh
(crontab -l 2>/dev/null; echo "0 * * * * /tmp/cleanup.sh") | crontab -

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
