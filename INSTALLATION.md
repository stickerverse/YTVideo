# 4K Video Reaper - Installation Guide

This guide provides detailed instructions for installing and deploying the 4K Video Reaper application in various environments.

## Table of Contents
- [System Requirements](#system-requirements)
- [Quick Start with Docker](#quick-start-with-docker)
- [Manual Installation](#manual-installation)
- [Production Deployment](#production-deployment)
- [Configuration Options](#configuration-options)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Operating System**: Ubuntu 20.04 LTS / Debian 11 or higher
- **CPU**: 2 cores
- **RAM**: 2GB
- **Disk Space**: 10GB
- **Network**: Reliable internet connection

### Recommended Requirements
- **Operating System**: Ubuntu 22.04 LTS / Debian 12
- **CPU**: 4 cores
- **RAM**: 4GB
- **Disk Space**: 50GB SSD
- **Network**: High-speed internet connection

### Required Software
- Python 3.9 or higher
- Aria2 (for multi-threaded downloads)
- FFmpeg (for audio extraction and format conversion)
- Nginx (for production deployment)
- Docker (optional, for containerized deployment)

## Quick Start with Docker

Docker provides the easiest way to get started with 4K Video Reaper.

### Prerequisites
- Docker and Docker Compose installed on your system
- [Docker Installation Guide](https://docs.docker.com/get-docker/)

### Deploy with Docker Compose

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/4KVideoReaper.git
   cd 4KVideoReaper
   ```

2. Create a `.env` file with your configuration:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application at http://localhost:80

### Docker Compose Configuration Options

You can modify the `docker-compose.yml` file to customize your deployment:

```yaml
version: '3.8'
services:
  web:
    build: .
    restart: always
    ports:
      - "8000:8000"  # Change the first port to modify the host port
    volumes:
      - ./downloads:/app/downloads  # Change to store downloads in a different location
      - ./config:/app/config
    environment:
      - DOWNLOAD_DIR=/app/downloads
      - ARIA2_MAX_CONNECTIONS=8  # Modify for network conditions
```

## Manual Installation

This section covers a step-by-step manual installation process.

### 1. Install System Dependencies

#### Ubuntu/Debian
```bash
# Update package lists
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv aria2 ffmpeg nginx supervisor
```

#### CentOS/RHEL
```bash
# Update package lists
sudo dnf update -y

# Install EPEL repository (if not already installed)
sudo dnf install -y epel-release

# Install required packages
sudo dnf install -y python39 python39-pip aria2 ffmpeg nginx supervisor
```

### 2. Create Application Directory

```bash
# Create directory structure
sudo mkdir -p /var/www/4KVideoReaper
sudo mkdir -p /var/log/4kvideoreaper
sudo mkdir -p /var/www/4KVideoReaper/downloads

# Set permissions
sudo chown -R $(whoami):$(whoami) /var/www/4KVideoReaper
sudo chown -R $(whoami):$(whoami) /var/log/4kvideoreaper
```

### 3. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/yourusername/4KVideoReaper.git /var/www/4KVideoReaper
cd /var/www/4KVideoReaper
```

### 4. Create Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .
```

### 5. Configure the Application

```bash
# Create configuration file
cp config.example.json config.json

# Edit configuration
nano config.json
```

Example configuration:

```json
{
    "download_dir": "/var/www/4KVideoReaper/downloads",
    "log_dir": "/var/log/4kvideoreaper",
    "aria2": {
        "path": "aria2c",
        "max_connections": 8,
        "split": 8,
        "enabled": true
    },
    "ytdlp": {
        "format": "bestvideo+bestaudio/best",
        "preferred_codec": "mp4"
    },
    "batch": {
        "max_concurrent": 5
    }
}
```

### 6. Test the Application

```bash
# Test the application
source venv/bin/activate
cd /var/www/4KVideoReaper
python web/api.py --host 127.0.0.1 --port 8000 --debug
```

Visit http://127.0.0.1:8000 in your browser to verify the application is working.

## Production Deployment

For a robust production deployment, follow these steps:

### 1. Set Up System Service

```bash
# Copy service file
sudo cp /var/www/4KVideoReaper/4kvideoreaper.service /etc/systemd/system/

# Start and enable the service
sudo systemctl daemon-reload
sudo systemctl enable 4kvideoreaper
sudo systemctl start 4kvideoreaper

# Check the status
sudo systemctl status 4kvideoreaper
```

### 2. Configure Nginx

```bash
# Copy Nginx configuration
sudo cp /var/www/4KVideoReaper/4kvideoreaper.conf /etc/nginx/sites-available/

# Create symlink
sudo ln -s /etc/nginx/sites-available/4kvideoreaper.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 3. Set Up SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test automatic renewal
sudo certbot renew --dry-run
```

### 4. Set Up Monitoring

```bash
# Copy monitoring script
sudo cp /var/www/4KVideoReaper/monitor.py /usr/local/bin/4kvideoreaper-monitor
sudo chmod +x /usr/local/bin/4kvideoreaper-monitor

# Set up cron job for regular monitoring
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/4kvideoreaper-monitor --check-only || systemctl restart 4kvideoreaper") | crontab -
```

### 5. Set Up Log Rotation

```bash
# Create log rotation configuration
sudo nano /etc/logrotate.d/4kvideoreaper
```

Add the following content:

```
/var/log/4kvideoreaper/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload 4kvideoreaper >/dev/null 2>&1 || true
    endscript
}
```

## Configuration Options

The 4K Video Reaper application can be configured through various methods:

### Configuration File (config.json)

The main configuration file supports the following options:

| Option | Description | Default Value |
|--------|-------------|---------------|
| `download_dir` | Directory to store downloaded files | `~/Downloads/youtube` |
| `default_proxy` | Default proxy URL to use | `null` |
| `captcha_api_key` | API key for CAPTCHA solving service | `null` |
| `aria2.path` | Path to aria2c executable | `aria2c` |
| `aria2.max_connections` | Maximum connections per server | `4` |
| `aria2.split` | Number of splits for downloads | `4` |
| `aria2.enabled` | Whether to use aria2 for downloads | `true` |
| `ytdlp.format` | Default video format | `bestvideo+bestaudio/best` |
| `ytdlp.preferred_codec` | Preferred video codec | `mp4` |
| `batch.max_concurrent` | Maximum concurrent downloads | `3` |

### Environment Variables

Environment variables can override configuration file settings:

| Variable | Description |
|----------|-------------|
| `DOWNLOAD_DIR` | Directory to store downloaded files |
| `DEFAULT_PROXY` | Default proxy URL to use |
| `CAPTCHA_API_KEY` | API key for CAPTCHA solving service |
| `ARIA2_PATH` | Path to aria2c executable |
| `ARIA2_MAX_CONNECTIONS` | Maximum connections per server |
| `ARIA2_SPLIT` | Number of splits for downloads |
| `ARIA2_ENABLED` | Whether to use aria2 for downloads |
| `YTDLP_FORMAT` | Default video format |
| `YTDLP_PREFERRED_CODEC` | Preferred video codec |
| `BATCH_MAX_CONCURRENT` | Maximum concurrent downloads |

## Security Considerations

### File Permissions

Ensure proper file permissions:

```bash
# Set restrictive permissions on configuration files
sudo chmod 640 /var/www/4KVideoReaper/config.json
sudo chmod 640 /var/www/4KVideoReaper/.env

# Set proper ownership
sudo chown -R www-data:www-data /var/www/4KVideoReaper
sudo chown -R www-data:www-data /var/log/4kvideoreaper
```

### Firewall Configuration

Configure your firewall to allow only necessary traffic:

```bash
# Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### Rate Limiting

The Nginx configuration includes rate limiting to prevent abuse.

### Regular Updates

Keep the system and application updated:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Update application code
cd /var/www/4KVideoReaper
git pull
source venv/bin/activate
pip install -r requirements.txt
pip install -r web/requirements.txt
sudo systemctl restart 4kvideoreaper
```

## Troubleshooting

### Common Issues and Solutions

#### Application Won't Start

Check the logs:
```bash
sudo journalctl -u 4kvideoreaper -f
```

Possible solutions:
- Ensure all dependencies are installed
- Check file permissions
- Verify the configuration file is valid JSON

#### Downloads Fail

Possible solutions:
- Check if aria2 is installed: `which aria2c`
- Verify internet connectivity
- Try with a different proxy if region-restricted
- Check disk space: `df -h`

#### Slow Downloads

Possible solutions:
- Increase aria2 connections: Edit `config.json` to increase `aria2.max_connections`
- Try a different proxy
- Check network bandwidth

#### Web Interface Not Loading

Possible solutions:
- Check Nginx status: `sudo systemctl status nginx`
- Verify Nginx configuration: `sudo nginx -t`
- Check if the application is running: `sudo systemctl status 4kvideoreaper`

### Viewing Logs

```bash
# Application logs
tail -f /var/log/4kvideoreaper/app.log

# Download logs
tail -f /var/log/4kvideoreaper/download.log

# API logs
tail -f /var/log/4kvideoreaper/api.log

# Nginx access logs
tail -f /var/log/nginx/4kvideoreaper.access.log

# Nginx error logs
tail -f /var/log/nginx/4kvideoreaper.error.log
```

### Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/yourusername/4KVideoReaper/issues) for similar problems
2. Create a new issue with detailed information:
   - Error messages from logs
   - System information
   - Steps to reproduce
   - Expected vs. actual behavior

---

## Additional Resources

- [Aria2 Documentation](https://aria2.github.io/)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [Gunicorn Documentation](https://docs.gunicorn.org/en/stable/)
