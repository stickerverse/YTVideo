FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including aria2 and ffmpeg
RUN apt-get update && apt-get install -y \
    aria2 \
    ffmpeg \
    gcc \
    python3-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files first for better caching
COPY requirements.txt /app/
COPY web/requirements.txt /app/web/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r web/requirements.txt

# Copy the rest of the application
COPY . /app/

# Install the package in development mode
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /var/data/downloads /app/config /app/logs

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/var/data/downloads \
    LOG_DIR=/app/logs \
    CONFIG_DIR=/app/config \
    PORT=10000 \
    PYTHONPATH=/app

# Create a non-root user and set proper permissions
RUN useradd -m appuser \
    && chown -R appuser:appuser /app /var/data/downloads /app/logs
USER appuser

# Expose port (Render will use the $PORT environment variable)
EXPOSE 10000

# Command to run the application
CMD gunicorn --workers=2 --bind=0.0.0.0:$PORT --log-level=info --timeout=120 web.wsgi:app
