#!/bin/bash
# Production launch script for 4K Video Reaper
# This script prepares and starts the application in production mode with all optimizations

set -e  # Exit on error

# Colors for console output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration variables
APP_DIR=${APP_DIR:-"$(pwd)"}
VENV_DIR=${VENV_DIR:-"${APP_DIR}/venv"}
LOG_DIR=${LOG_DIR:-"/var/log/4kvideoreaper"}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-"/var/www/4KVideoReaper/downloads"}
CONFIG_DIR=${CONFIG_DIR:-"${APP_DIR}/config"}
WEB_HOST=${WEB_HOST:-"0.0.0.0"}
WEB_PORT=${WEB_PORT:-"8000"}

# Calculate optimal number of workers based on CPU cores
CPU_CORES=$(grep -c ^processor /proc/cpuinfo)
WORKERS=$((CPU_CORES * 2 + 1))
log_info "Detected ${CPU_CORES} CPU cores, using ${WORKERS} Gunicorn workers"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    log_warn "This script should ideally be run as root for proper file permissions"
    log_warn "Continuing as non-root user, but some operations may fail"
fi

# Create required directories
ensure_dirs() {
    log_info "Creating required directories..."
    mkdir -p "${LOG_DIR}"
    mkdir -p "${DOWNLOAD_DIR}"
    mkdir -p "${CONFIG_DIR}"
    
    # Set proper permissions
    if [ "$(id -u)" -eq 0 ]; then
        chown -R www-data:www-data "${LOG_DIR}"
        chown -R www-data:www-data "${DOWNLOAD_DIR}"
        chmod 755 "${LOG_DIR}"
        chmod 755 "${DOWNLOAD_DIR}"
    else
        log_warn "Not running as root, skipping permission changes"
    fi
}

# Install dependencies if needed
check_deps() {
    log_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed. Please install Python 3.7 or later."
        exit 1
    fi
    
    # Check virtual environment
    if [ ! -d "${VENV_DIR}" ]; then
        log_info "Virtual environment not found. Creating..."
        python3 -m venv "${VENV_DIR}"
    fi
    
    # Check Aria2
    if command -v aria2c &> /dev/null; then
        ARIA2_VERSION=$(aria2c --version | head -n1)
        log_info "Found ${ARIA2_VERSION}"
        export ARIA2_ENABLED=true
    else
        log_warn "Aria2 is not installed. Multi-threaded downloads will be disabled."
        export ARIA2_ENABLED=false
    fi
    
    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n1)
        log_info "Found ${FFMPEG_VERSION}"
    else
        log_warn "FFmpeg is not installed. Some features may not work correctly."
        log_warn "Installing FFmpeg is strongly recommended"
    fi
    
    # Install Python dependencies
    log_info "Installing/updating Python dependencies..."
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r web/requirements.txt
    pip install gunicorn psutil
    pip install -e .
}

# Optimize app for production
optimize_app() {
    log_info "Optimizing application for production..."
    
    # Run minification script if it exists
    if [ -f "${APP_DIR}/minify-assets.sh" ]; then
        log_info "Minifying web assets..."
        bash "${APP_DIR}/minify-assets.sh"
    else
        log_warn "Minification script not found. Consider adding it for better performance."
    fi
    
    # Check for supervisor configuration
    if [ -f "${APP_DIR}/supervisor.conf" ]; then
        if [ "$(id -u)" -eq 0 ] && command -v supervisorctl &> /dev/null; then
            log_info "Installing supervisor configuration..."
            cp "${APP_DIR}/supervisor.conf" /etc/supervisor/conf.d/4kvideoreaper.conf
            supervisorctl reread
            supervisorctl update
            log_info "Supervisor configuration installed"
        else
            log_warn "Supervisor configuration exists but cannot be installed (requires root)"
        fi
    fi
    
    # Check and update nginx configuration
    if [ -f "${APP_DIR}/4kvideoreaper.conf" ]; then
        if [ "$(id -u)" -eq 0 ] && command -v nginx &> /dev/null; then
            log_info "Installing nginx configuration..."
            cp "${APP_DIR}/4kvideoreaper.conf" /etc/nginx/sites-available/
            if [ ! -f "/etc/nginx/sites-enabled/4kvideoreaper.conf" ]; then
                ln -sf /etc/nginx/sites-available/4kvideoreaper.conf /etc/nginx/sites-enabled/
            fi
            nginx -t && systemctl reload nginx
            log_info "Nginx configuration installed and reloaded"
        else
            log_warn "Nginx configuration exists but cannot be installed (requires root)"
        fi
    fi
    
    # Create or update systemd service if running as root
    if [ "$(id -u)" -eq 0 ] && [ -f "${APP_DIR}/4kvideoreaper.service" ]; then
        log_info "Installing systemd service..."
        cp "${APP_DIR}/4kvideoreaper.service" /etc/systemd/system/
        systemctl daemon-reload
        systemctl enable 4kvideoreaper
        log_info "Systemd service installed and enabled"
    fi
}

# Start the application with Gunicorn
start_app() {
    log_info "Starting 4K Video Reaper in production mode..."
    source "${VENV_DIR}/bin/activate"
    
    # Set environment variables
    export DOWNLOAD_DIR="${DOWNLOAD_DIR}"
    export LOG_DIR="${LOG_DIR}"
    export PYTHONPATH="${APP_DIR}:${PYTHONPATH}"
    export ENVIRONMENT="production"
    
    # If running as root, create a cleanup task
    if [ "$(id -u)" -eq 0 ]; then
        log_info "Setting up cleanup cron job..."
        (crontab -l 2>/dev/null; echo "0 */6 * * * ${VENV_DIR}/bin/python ${APP_DIR}/cleanup.py --dir=\"${DOWNLOAD_DIR}\" --max-age=24") | crontab -
    fi
    
    # Check if we should run through systemd
    if [ "$(id -u)" -eq 0 ] && systemctl is-enabled 4kvideoreaper &>/dev/null; then
        log_info "Starting service through systemd..."
        systemctl restart 4kvideoreaper
        systemctl status 4kvideoreaper
    else
        # Start with Gunicorn directly
        log_info "Starting with Gunicorn directly..."
        
        # Create a PID file
        PID_FILE="${APP_DIR}/4kvideoreaper.pid"
        
        # Start Gunicorn in the background
        gunicorn \
            --bind "${WEB_HOST}:${WEB_PORT}" \
            --workers "${WORKERS}" \
            --threads 2 \
            --access-logfile "${LOG_DIR}/access.log" \
            --error-logfile "${LOG_DIR}/error.log" \
            --log-level info \
            --timeout 120 \
            --worker-tmp-dir /dev/shm \
            --pid "${PID_FILE}" \
            --daemon \
            "web.wsgi:app"
            
        log_info "Application started with PID file: ${PID_FILE}"
        log_info "Monitor logs with: tail -f ${LOG_DIR}/error.log"
    fi
}

# Main execution
main() {
    log_info "Launching 4K Video Reaper in production mode..."
    
    # Run initialization steps
    ensure_dirs
    check_deps
    optimize_app
    start_app
    
    log_info "Launch completed successfully!"
    log_info "Your application should now be running at http://${WEB_HOST}:${WEB_PORT}/"
    
    if [ "$(id -u)" -eq 0 ] && command -v nginx &> /dev/null; then
        log_info "Nginx should be proxying requests to your application"
        log_info "Make sure your domain is properly configured to point to this server"
    fi
    
    log_info "For troubleshooting, check logs in: ${LOG_DIR}"
}

# Run main function
main "$@"
