#!/bin/bash
# 4K Video Reaper Startup Script
# This script handles starting the application with proper environment setup

# Exit on error
set -e

# Configuration variables - can be overridden by environment variables
APP_DIR=${APP_DIR:-"$(pwd)"}
VENV_DIR=${VENV_DIR:-"${APP_DIR}/venv"}
LOG_DIR=${LOG_DIR:-"${APP_DIR}/logs"}
CONFIG_DIR=${CONFIG_DIR:-"${APP_DIR}/config"}
DOWNLOAD_DIR=${DOWNLOAD_DIR:-"${APP_DIR}/downloads"}
ENV_FILE=${ENV_FILE:-"${APP_DIR}/.env"}
WEB_HOST=${WEB_HOST:-"0.0.0.0"}
WEB_PORT=${WEB_PORT:-"8000"}
WEB_WORKERS=${WEB_WORKERS:-"4"}
MODE=${MODE:-"production"}  # 'development' or 'production'

# Colors for console output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Create required directories
ensure_dirs() {
    log_info "Creating required directories..."
    mkdir -p "${LOG_DIR}"
    mkdir -p "${DOWNLOAD_DIR}"
    mkdir -p "${CONFIG_DIR}"
}

# Check prerequisites
check_prereqs() {
    log_info "Checking prerequisites..."
    
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
        log_warn "Aria2 is not installed. Multi-threaded downloads will not be available."
        export ARIA2_ENABLED=false
    fi
    
    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n1)
        log_info "Found ${FFMPEG_VERSION}"
    else
        log_warn "FFmpeg is not installed. Some features may not work correctly."
    fi
}

# Load environment variables
load_env() {
    log_info "Loading environment variables..."
    if [ -f "${ENV_FILE}" ]; then
        source "${ENV_FILE}"
        log_info "Loaded environment from ${ENV_FILE}"
    else
        log_warn "No .env file found at ${ENV_FILE}"
    fi
    
    # Set required environment variables
    export DOWNLOAD_DIR="${DOWNLOAD_DIR}"
    export LOG_DIR="${LOG_DIR}"
    export PYTHONPATH="${APP_DIR}:${PYTHONPATH}"
}

# Install dependencies
install_deps() {
    log_info "Installing dependencies..."
    source "${VENV_DIR}/bin/activate"
    pip install --upgrade pip
    
    if [ -f "${APP_DIR}/requirements.txt" ]; then
        pip install -r "${APP_DIR}/requirements.txt"
    fi
    
    if [ -f "${APP_DIR}/web/requirements.txt" ]; then
        pip install -r "${APP_DIR}/web/requirements.txt"
    fi
    
    # Install the package in development mode
    pip install -e "${APP_DIR}"
    
    log_info "Dependencies installed successfully"
}

# Configure the application
configure_app() {
    log_info "Configuring application..."
    
    # Check if config.json exists, if not, create from example
    if [ ! -f "${CONFIG_DIR}/config.json" ]; then
        if [ -f "${APP_DIR}/config.example.json" ]; then
            cp "${APP_DIR}/config.example.json" "${CONFIG_DIR}/config.json"
            log_info "Created config.json from example"
            
            # Update config with environment-specific settings
            sed -i "s|\"download_dir\": \".*\"|\"download_dir\": \"${DOWNLOAD_DIR}\"|g" "${CONFIG_DIR}/config.json"
            sed -i "s|\"log_dir\": \".*\"|\"log_dir\": \"${LOG_DIR}\"|g" "${CONFIG_DIR}/config.json"
        else
            log_warn "config.example.json not found, skipping configuration"
        fi
    else
        log_info "Using existing config.json"
    fi
}

# Start the application in development mode
start_dev() {
    log_info "Starting in development mode..."
    source "${VENV_DIR}/bin/activate"
    
    # Set development environment variables
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    
    # Start the Flask development server
    python "${APP_DIR}/web/api.py" --host "${WEB_HOST}" --port "${WEB_PORT}" --debug
}

# Start the application in production mode
start_prod() {
    log_info "Starting in production mode..."
    source "${VENV_DIR}/bin/activate"
    
    # Check if gunicorn is installed
    if ! pip show gunicorn > /dev/null; then
        log_warn "Gunicorn not found. Installing..."
        pip install gunicorn
    fi
    
    # Start with Gunicorn
    exec gunicorn \
        --bind "${WEB_HOST}:${WEB_PORT}" \
        --workers "${WEB_WORKERS}" \
        --access-logfile "${LOG_DIR}/access.log" \
        --error-logfile "${LOG_DIR}/error.log" \
        --log-level info \
        --timeout 120 \
        --worker-tmp-dir /dev/shm \
        "web.wsgi:app"
}

# Clean temporary files
clean() {
    log_info "Cleaning temporary files..."
    find "${APP_DIR}" -name "*.pyc" -delete
    find "${APP_DIR}" -name "__pycache__" -type d -exec rm -rf {} +
    find "${APP_DIR}" -name "*.log.?" -delete
}

# Display help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev                Start in development mode"
    echo "  --prod               Start in production mode (default)"
    echo "  --install            Install dependencies only"
    echo "  --clean              Clean temporary files"
    echo "  --help               Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  APP_DIR              Application directory (default: current directory)"
    echo "  VENV_DIR             Virtual environment directory (default: APP_DIR/venv)"
    echo "  LOG_DIR              Log directory (default: APP_DIR/logs)"
    echo "  CONFIG_DIR           Config directory (default: APP_DIR/config)"
    echo "  DOWNLOAD_DIR         Download directory (default: APP_DIR/downloads)"
    echo "  ENV_FILE             Environment file (default: APP_DIR/.env)"
    echo "  WEB_HOST             Web server host (default: 0.0.0.0)"
    echo "  WEB_PORT             Web server port (default: 8000)"
    echo "  WEB_WORKERS          Number of web server workers (default: 4)"
    echo "  MODE                 Application mode: 'development' or 'production' (default: production)"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dev)
                MODE="development"
                shift
                ;;
            --prod)
                MODE="production"
                shift
                ;;
            --install)
                ensure_dirs
                check_prereqs
                load_env
                install_deps
                configure_app
                exit 0
                ;;
            --clean)
                clean
                exit 0
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Run required initialization steps
    ensure_dirs
    check_prereqs
    load_env
    install_deps
    configure_app
    
    # Start the application based on mode
    if [ "${MODE}" = "development" ]; then
        start_dev
    else
        start_prod
    fi
}

# Call main with all arguments
main "$@"
