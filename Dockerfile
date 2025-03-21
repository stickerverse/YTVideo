FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt ./
COPY web/requirements.txt ./web/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r web/requirements.txt \
    && pip install gunicorn

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /tmp/downloads /tmp/logs

# Set environment variables
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/tmp/downloads \
    LOG_DIR=/tmp/logs

# Expose port
EXPOSE 10000

# Default command
CMD ["gunicorn", "--workers=2", "--bind=0.0.0.0:$PORT", "--log-level=info", "--timeout=120", "web.wsgi:app"]
