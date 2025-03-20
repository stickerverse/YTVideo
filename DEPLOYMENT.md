#!/bin/bash
# Development start script for 4K Video Reaper

set -e

# Configuration variables
export DOWNLOAD_DIR="${DOWNLOAD_DIR:-./downloads}"
export LOG_DIR="${LOG_DIR:-./logs}"
export PORT="${PORT:-5000}"
export PYTHONPATH="${PYTHONPATH:-$(pwd)}"
export ENVIRONMENT="development"

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
    mkdir -p "${DOWNLOAD_DIR}"
    mkdir -p "${LOG_DIR}"
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
    if [ ! -d "venv" ]; then
        log_info "Virtual environment not found. Creating..."
        python3 -m venv venv
    fi
    
    # Check Aria2
    if command -v aria2c &> /dev/null; then
        ARIA2_VERSION=$(aria2c --version | head -n1)
        log_info "Found ${ARIA2_VERSION}"
    else
        log_warn "Aria2 is not installed. Multi-threaded downloads will not be available."
    fi
    
    # Check FFmpeg
    if command -v ffmpeg &> /dev/null; then
        FFMPEG_VERSION=$(ffmpeg -version | head -n1)
        log_info "Found ${FFMPEG_VERSION}"
    else
        log_warn "FFmpeg is not installed. Some features may not work correctly."
    fi
}

# Install Python package and dependencies
install_deps() {
    log_info "Installing dependencies..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r web/requirements.txt
    pip install -e .
    log_info "Dependencies installed successfully"
}

# Run the package module creation script
setup_modules() {
    log_info "Setting up Python package structure..."
    python create_init_files.py
}

# Run the application in development mode
run_dev() {
    log_info "Starting 4K Video Reaper in development mode..."
    source venv/bin/activate
    
    # Set Flask environment variables
    export FLASK_APP=web.api
    export FLASK_ENV=development
    export FLASK_DEBUG=1
    
    # Run the application
    log_info "Starting Flask development server on port ${PORT}..."
    python -m flask run --host=0.0.0.0 --port=${PORT}
}

# Run the application in production mode
run_prod() {
    log_info "Starting 4K Video Reaper in production mode..."
    source venv/bin/activate
    
    # Check if gunicorn is installed
    if ! pip show gunicorn &> /dev/null; then
        log_warn "Gunicorn not found. Installing..."
        pip install gunicorn
    fi
    
    # Run the cleanup script in the background
    python cleanup.py --dir="${DOWNLOAD_DIR}" --max-age=24 &
    
    # Run the health check script in the background
    python healthcheck.py --api-url="http://localhost:${PORT}/api/status" --downloads-dir="${DOWNLOAD_DIR}" --continuous --interval=300 &
    
    # Start with Gunicorn
    log_info "Starting Gunicorn on port ${PORT}..."
    gunicorn --bind=0.0.0.0:${PORT} --workers=1 --log-level=info --timeout=120 web.wsgi:app
}

# Show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dev                Start in development mode (default)"
    echo "  --prod               Start in production mode with Gunicorn"
    echo "  --install            Install dependencies only"
    echo "  --help               Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  DOWNLOAD_DIR         Directory to store downloads (default: ./downloads)"
    echo "  LOG_DIR              Directory to store logs (default: ./logs)"
    echo "  PORT                 Port to listen on (default: 5000)"
    echo "  PYTHONPATH           Python path (default: current directory)"
}

# Main function
main() {
    # Parse command line arguments
    local MODE="development"
    local INSTALL_ONLY=false
    
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
                INSTALL_ONLY=true
                shift
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
    install_deps
    setup_modules
    
    # Exit if install only
    if [ "$INSTALL_ONLY" = true ]; then
        log_info "Installation completed successfully."
        exit 0
    fi
    
    # Run in the specified mode
    if [ "$MODE" = "development" ]; then
        run_dev
    else
        run_prod
    fi
}

# Call main function with all arguments
main "$@"
