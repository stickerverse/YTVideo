#!/bin/bash
set -e

# Print environment information
echo "Starting 4K Video Reaper in ${ENVIRONMENT:-production} mode"
echo "Download directory: ${DOWNLOAD_DIR:-/app/downloads}"
echo "Log directory: ${LOG_DIR:-/app/logs}"
echo "Port: ${PORT:-8000}"

# Create necessary directories
mkdir -p "${DOWNLOAD_DIR:-/app/downloads}"
mkdir -p "${LOG_DIR:-/app/logs}"

# Set correct permissions
chown -R app:app "${DOWNLOAD_DIR:-/app/downloads}"
chown -R app:app "${LOG_DIR:-/app/logs}"

# Run database migrations if applicable (placeholder)
# python manage.py db upgrade

# Run initial setup scripts
python create_init_files.py

# Optional: Setup periodic cleanup cron job
if [ "$ENVIRONMENT" = "production" ]; then
    # Run cleanup script every hour
    (
        while true; do 
            python cleanup.py --dir="${DOWNLOAD_DIR:-/app/downloads}" --max-age=24
            sleep 3600
        done
    ) &
fi

# Optional: Health monitoring
(
    while true; do 
        python healthcheck.py \
            --api-url="http://localhost:${PORT}/api/status" \
            --downloads-dir="${DOWNLOAD_DIR:-/app/downloads}"
        sleep 300
    done
) &

# Check for required executables
echo "Checking system dependencies..."
which ffmpeg && echo "FFmpeg found" || echo "FFmpeg NOT found"
which aria2c && echo "Aria2c found" || echo "Aria2c NOT found"
which python && echo "Python found" || echo "Python NOT found"

# Generate a unique machine ID for tracking (optional)
if [ ! -f /app/.machine-id ]; then
    cat /proc/sys/kernel/random/uuid > /app/.machine-id
fi

# Final startup message
echo "4K Video Reaper is ready to serve downloads!"

# Execute the main command
exec "$@"
