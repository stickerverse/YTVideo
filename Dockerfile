FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies including aria2 and ffmpeg
RUN apt-get update && apt-get install -y \
    aria2 \
    ffmpeg \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -r web/requirements.txt \
    && pip install -e .

# Create necessary directories
RUN mkdir -p /app/downloads /app/config /app/logs

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOWNLOAD_DIR=/app/downloads \
    LOG_DIR=/app/logs \
    CONFIG_DIR=/app/config

# Create a non-root user and set proper permissions
RUN useradd -m appuser \
    && chown -R appuser:appuser /app
USER appuser

# Expose port for the web service
EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "--workers=3", "--bind=0.0.0.0:8000", "--log-level=info", "--log-file=/app/logs/gunicorn.log", "web.wsgi:app"]
