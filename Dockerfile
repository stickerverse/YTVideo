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

# Install Python dependencies with specific versions
RUN pip install --upgrade pip && \
    # Install with specific versions to ensure compatibility
    pip install Werkzeug==2.2.3 && \
    pip install Flask==2.2.3 && \
    pip install gunicorn==20.1.0 flask-cors==3.0.10 yt-dlp==2023.7.6 \
    requests==2.28.2 flask-talisman==0.8.0 python-dotenv==1.0.0 \
    psutil==5.9.5 python-json-logger==2.0.7 Flask-Limiter==3.3.1

# Run module creation script
RUN python create_init_files.py

# Expose port (Render will use the $PORT environment variable)
EXPOSE ${PORT:-10000}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-10000}/api/status || exit 1

# Command to run the application with additional debug output
CMD gunicorn --workers=1 --log-level=debug --bind=0.0.0.0:${PORT:-10000} --timeout=120 web.wsgi:app
