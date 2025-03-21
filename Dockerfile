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

# Copy requirements and install dependencies
COPY requirements.txt ./
COPY web/requirements.txt ./web/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r web/requirements.txt \
    && pip install gunicorn flask-talisman

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/downloads /tmp/logs

# Set permissions for tmp directories
RUN chmod 777 /tmp/downloads /tmp/logs

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/tmp/downloads \
    LOG_DIR=/tmp/logs \
    ENVIRONMENT=production

# Run module creation script
RUN python create_init_files.py

# Expose port (Render will use the $PORT environment variable)
EXPOSE ${PORT:-10000}

# Set up healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:${PORT:-10000}/api/status || exit 1

# Command to run the application
CMD gunicorn --workers=1 --bind=0.0.0.0:${PORT:-10000} --log-level=info --timeout=120 web.wsgi:app
