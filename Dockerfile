FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /tmp/downloads /tmp/logs && \
    chmod 777 /tmp/downloads /tmp/logs

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/tmp/downloads \
    LOG_DIR=/tmp/logs \
    ENVIRONMENT=production

# Copy application files
COPY . .

# Install base Python requirements
RUN pip install --upgrade pip && \
    pip install gunicorn==20.1.0 flask==2.2.3 flask-cors==3.0.10 yt-dlp==2023.7.6 requests==2.28.2

# Run module creation script
RUN python create_init_files.py

# Expose port (Render will use the $PORT environment variable)
EXPOSE ${PORT:-10000}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-10000}/api/status || exit 1

# Command to run the application with additional debug output
CMD python -c "import sys; print('Python version:', sys.version); print('Python path:', sys.path); print('Current directory:', __import__('os').getcwd())" && \
    ls -la /app && ls -la /app/web && \
    gunicorn --workers=1 --log-level=debug --bind=0.0.0.0:${PORT:-10000} --timeout=120 web.wsgi:app
