#!/bin/bash
# Script to minify CSS and JavaScript assets for production

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print status function
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check for required tools
if ! command -v npx &> /dev/null; then
    print_warning "npx not found. Installing required packages..."
    npm install -g terser clean-css-cli html-minifier-terser
fi

# Define source and destination paths
WEB_DIR="./web/public"
CSS_SOURCE="${WEB_DIR}/styles.css"
CSS_MIN="${WEB_DIR}/styles.min.css"
JS_SOURCE="${WEB_DIR}/script.js"
JS_MIN="${WEB_DIR}/script.min.js"
HTML_SOURCE="${WEB_DIR}/index.html"
HTML_MIN="${WEB_DIR}/index.min.html"

# Create backup directory
BACKUP_DIR="${WEB_DIR}/backup-$(date +%Y%m%d%H%M%S)"
mkdir -p "${BACKUP_DIR}"

# Backup original files
print_status "Backing up original files to ${BACKUP_DIR}"
cp "${CSS_SOURCE}" "${BACKUP_DIR}/"
cp "${JS_SOURCE}" "${BACKUP_DIR}/"
cp "${HTML_SOURCE}" "${BACKUP_DIR}/"

# Minify CSS
print_status "Minifying CSS..."
npx clean-css-cli -o "${CSS_MIN}" "${CSS_SOURCE}"
css_size_before=$(wc -c < "${CSS_SOURCE}")
css_size_after=$(wc -c < "${CSS_MIN}")
css_reduction=$((100 - (css_size_after * 100 / css_size_before)))
print_status "CSS minified: ${css_size_before} → ${css_size_after} bytes (${css_reduction}% reduction)"

# Minify JavaScript
print_status "Minifying JavaScript..."
npx terser "${JS_SOURCE}" --compress --mangle --output "${JS_MIN}"
js_size_before=$(wc -c < "${JS_SOURCE}")
js_size_after=$(wc -c < "${JS_MIN}")
js_reduction=$((100 - (js_size_after * 100 / js_size_before)))
print_status "JavaScript minified: ${js_size_before} → ${js_size_after} bytes (${js_reduction}% reduction)"

# Minify HTML (optional)
print_status "Minifying HTML..."
npx html-minifier-terser --collapse-whitespace --remove-comments --remove-optional-tags --remove-redundant-attributes --remove-script-type-attributes --remove-tag-whitespace --use-short-doctype --minify-css true --minify-js true --input-dir "${WEB_DIR}" --output-dir "${WEB_DIR}" --file-ext html --output "${HTML_MIN}" "${HTML_SOURCE}"
html_size_before=$(wc -c < "${HTML_SOURCE}")
html_size_after=$(wc -c < "${HTML_MIN}")
html_reduction=$((100 - (html_size_after * 100 / html_size_before)))
print_status "HTML minified: ${html_size_before} → ${html_size_after} bytes (${html_reduction}% reduction)"

# Update the HTML file to reference minified assets
print_status "Updating HTML to reference minified assets..."
# Make a copy of the minified HTML
cp "${HTML_MIN}" "${HTML_MIN}.tmp"

# Replace CSS and JS references
sed -i 's/styles\.css/styles.min.css/g' "${HTML_MIN}.tmp"
sed -i 's/script\.js/script.min.js/g' "${HTML_MIN}.tmp"

# Replace the original HTML with the updated minified version
mv "${HTML_MIN}.tmp" "${HTML_SOURCE}"

# Generate gzip versions for further compression
print_status "Generating gzip versions for static assets..."
gzip -9 -k "${CSS_MIN}"
gzip -9 -k "${JS_MIN}"
gzip -9 -k "${HTML_SOURCE}"

print_status "Asset minification complete!"
print_status "Total size reduction: CSS: ${css_reduction}%, JS: ${js_reduction}%, HTML: ${html_reduction}%"
print_status "Original files backed up to ${BACKUP_DIR}"

# Show summary of changes
print_status "Assets are now optimized for production use."
print_status "Note: Nginx must be configured to serve the .gz files when available (already configured in the optimized Nginx config)."
