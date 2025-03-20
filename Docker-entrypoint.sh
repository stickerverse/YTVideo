#!/bin/bash
set -e

# Create necessary directories
mkdir -p "${DOWNLOAD_DIR:-/tmp/downloads}"
mkdir -p "${LOG_DIR:-/app/logs}"

# Setup a cleanup cron job if running in production
if [ "$ENVIRONMENT" = "production" ]; then
    # Run cleanup script every hour in the background
    echo "Setting up hourly cleanup job..."
    (while true; do 
        python /app/cleanup.py --dir="${DOWNLOAD_DIR:-/tmp/downloads}" --max-age=24
        sleep 3600
    done) &
fi

# Run health check in the background
echo "Setting up health check..."
(while true; do 
    python /app/healthcheck.py --api-url="http://localhost:${PORT:-10000}/api/status" --downloads-dir="${DOWNLOAD_DIR:-/tmp/downloads}"
    sleep 300
done) &

# Print environment information
echo "Environment: ${ENVIRONMENT:-development}"
echo "Download directory: ${DOWNLOAD_DIR:-/tmp/downloads}"
echo "Log directory: ${LOG_DIR:-/app/logs}"
echo "Port: ${PORT:-10000}"

# Check for required executables
echo "Checking for required executables..."
which ffmpeg && echo "ffmpeg found" || echo "ffmpeg NOT found"
which aria2c && echo "aria2c found" || echo "aria2c NOT found"

# Run the command
echo "Starting 4K Video Reaper..."
exec "$@"
