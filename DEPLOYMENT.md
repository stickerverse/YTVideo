# 4K Video Reaper - Deployment Guide

This guide provides detailed instructions for deploying 4K Video Reaper in various environments, from development to production.

## Table of Contents
- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Deployment Options](#deployment-options)
  - [Option 1: Direct Server Installation](#option-1-direct-server-installation)
  - [Option 2: Docker Deployment](#option-2-docker-deployment)
  - [Option 3: Cloud Deployment](#option-3-cloud-deployment)
- [Configuration](#configuration)
- [SSL/TLS Setup](#ssltls-setup)
- [Performance Optimization](#performance-optimization)
- [SEO Optimization](#seo-optimization)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Scaling Strategies](#scaling-strategies)
- [Troubleshooting](#troubleshooting)

## Quick Start

For those who want to get up and running quickly:

```bash
# Clone the repository
git clone https://github.com/yourusername/4KVideoReaper.git
cd 4KVideoReaper

# Use the deployment script for automatic setup
sudo ./deploy.sh

# Or use Docker Compose
docker-compose up -d
```

## Prerequisites

### System Requirements
- **OS**: Ubuntu 20.04 LTS or newer / Debian 11 or newer
- **CPU**: 2+ cores recommended
- **RAM**: 2GB minimum, 4GB+ recommended
- **Storage**: 20GB+ for the application and downloads
- **Network**: High-speed internet connection

### Required Software
- Python 3.9+
- Aria2 (for multi-threaded downloads)
- FFmpeg (for video/audio processing)
- Nginx (for production deployment)
- Let's Encrypt Certbot (for SSL/TLS)

## Deployment Options

### Option 1: Direct Server Installation

#### Step 1: Install System Dependencies

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3 python3-pip python3-venv aria2 ffmpeg nginx certbot python3-certbot-nginx supervisor git
```

#### Step 2: Set Up Application

```bash
# Create application directory
sudo mkdir -p /var/www/4KVideoReaper
sudo chown $USER:$USER /var/www/4KVideoReaper

# Clone repository
git clone https://github.com/yourusername/4KVideoReaper.git /var/www/4KVideoReaper
cd /var/www/4KVideoReaper

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .

# Create necessary directories
mkdir -p /var/www/4KVideoReaper/downloads
mkdir -p /var/log/4kvideoreaper
sudo chown -R www-data:www-data /var/www/4KVideoReaper/downloads
sudo chown -R www-data:www-data /var/log/4kvideoreaper
```

#### Step 3: Configure the Application

```bash
# Create configuration from example
cp .env.example .env

# Edit configuration with your settings
nano .env
```

#### Step 4: Set Up Systemd Service

```bash
# Copy the service file to systemd directory
sudo cp 4kvideoreaper.service /etc/systemd/system/

# Enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable 4kvideoreaper
sudo systemctl start 4kvideoreaper
```

#### Step 5: Configure Nginx

```bash
# Copy Nginx configuration
sudo cp 4kvideoreaper.conf /etc/nginx/sites-available/

# Create symbolic link
sudo ln -s /etc/nginx/sites-available/4kvideoreaper.conf /etc/nginx/sites-enabled/

# Test and restart Nginx
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 6: Set Up SSL with Let's Encrypt

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Option 2: Docker Deployment

Docker provides a more isolated and reproducible deployment.

#### Step 1: Install Docker and Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### Step 2: Prepare Docker Environment

```bash
# Clone repository
git clone https://github.com/yourusername/4KVideoReaper.git
cd 4KVideoReaper

# Create .env file
cp .env.example .env
nano .env  # Edit with your settings
```

#### Step 3: Launch with Docker Compose

```bash
# Start containers
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Option 3: Cloud Deployment

#### Render.com Deployment

Render provides a simple platform for deploying web services.

1. Fork the repository on GitHub
2. Connect your Render account to GitHub
3. Create a new Web Service on Render
4. Select your forked repository
5. Render will detect the `render.yaml` file and configure accordingly
6. Click "Create Web Service"

See [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md) for more details.

## Configuration

### Environment Variables

Key configuration options in the `.env` file:

| Variable | Description | Default |
|----------|-------------|---------|
| `DOWNLOAD_DIR` | Directory for downloaded files | `/var/www/4KVideoReaper/downloads` |
| `LOG_DIR` | Directory for log files | `/var/log/4kvideoreaper` |
| `ARIA2_ENABLED` | Enable Aria2 for multi-threaded downloads | `true` |
| `ARIA2_MAX_CONNECTIONS` | Maximum connections per server | `8` |
| `YTDLP_FORMAT` | Default video format | `bestvideo+bestaudio/best` |
| `BATCH_MAX_CONCURRENT` | Maximum concurrent downloads | `5` |
| `WEB_PORT` | Web server port | `8000` |
| `SECRET_KEY` | Secret key for security | Generate a random key |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `yourdomain.com,www.yourdomain.com` |

### Nginx Configuration

The provided `4kvideoreaper.conf` includes optimized settings for:

- SSL/TLS configuration
- HTTP/2 support
- Security headers
- Caching rules
- Rate limiting
- DDoS protection

Review and adjust settings in `/etc/nginx/sites-available/4kvideoreaper.conf` based on your needs.

## SSL/TLS Setup

### Let's Encrypt (Recommended)

```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### Manual SSL Configuration

If using your own SSL certificates:

1. Place certificates in `/etc/nginx/ssl/`
2. Update Nginx configuration to point to your certificate files
3. Restart Nginx: `sudo systemctl restart nginx`

## Performance Optimization

### Backend Optimization

1. **Gunicorn Workers**:
   - Set worker count to `(2 × CPU cores) + 1`
   - Edit `WEB_WORKERS` in `.env` or gunicorn command

2. **Aria2 Tuning**:
   - Increase `ARIA2_MAX_CONNECTIONS` (8-16 recommended)
   - Increase `ARIA2_SPLIT` for faster downloads

3. **Batch Processing**:
   - Adjust `BATCH_MAX_CONCURRENT` based on server resources

### Frontend Optimization

1. **Static File Compression**:
   - Enable Gzip in Nginx (already configured)

2. **Browser Caching**:
   - Set appropriate Cache-Control headers (already configured)

3. **Minification**:
   - Minify JavaScript and CSS files:
   ```bash
   npm install -g minify
   minify web/public/styles.css > web/public/styles.min.css
   minify web/public/script.js > web/public/script.min.js
   ```
   - Update HTML to reference minified files

## SEO Optimization

1. **Update Meta Tags**: Edit `web/public/index.html` to include:
   - Title tags: `<title>4K Video Reaper - Download YouTube Videos in High Quality</title>`
   - Meta description: `<meta name="description" content="Download YouTube videos in 4K quality with advanced features like proxy support, CAPTCHA solving, and batch downloads.">`
   - Open Graph tags

2. **Implement Structured Data**:
   ```html
   <script type="application/ld+json">
   {
     "@context": "https://schema.org",
     "@type": "WebApplication",
     "name": "4K Video Reaper",
     "description": "Advanced YouTube video downloader with multi-threading, proxy support, and batch processing.",
     "operatingSystem": "All",
     "applicationCategory": "UtilitiesApplication",
     "offers": {
       "@type": "Offer",
       "price": "0",
       "priceCurrency": "USD"
     }
   }
   </script>
   ```

3. **Sitemap and Robots.txt**:
   - Create `web/public/sitemap.xml`
   - Create `web/public/robots.txt`

4. **Performance Optimizations**:
   - Improve page load speed through optimizations mentioned above

## Monitoring and Maintenance

### Log Rotation

The application uses logrotate to manage log files. Configuration is in `/etc/logrotate.d/4kvideoreaper`.

### Monitoring with Supervisor

Supervisor helps keep the application running:

```bash
sudo cp supervisor.conf /etc/supervisor/conf.d/4kvideoreaper.conf
sudo supervisorctl reread
sudo supervisorctl update
```

### Regular Maintenance

1. **Regular Updates**:
   ```bash
   cd /var/www/4KVideoReaper
   git pull
   source venv/bin/activate
   pip install -r requirements.txt
   sudo systemctl restart 4kvideoreaper
   ```

2. **SSL Certificate Renewal**:
   Certbot installs a cron job for automatic renewal, but you can test it:
   ```bash
   sudo certbot renew --dry-run
   ```

3. **Storage Management**:
   The application automatically cleans old downloads, but verify it's working:
   ```bash
   sudo python /var/www/4KVideoReaper/cleanup.py --dir="/var/www/4KVideoReaper/downloads" --max-age=24
   ```

## Scaling Strategies

### Horizontal Scaling

1. **Load Balancer Setup**:
   - Deploy multiple application instances
   - Set up Nginx as a load balancer
   - Use shared storage for downloads

2. **Database Scaling** (for future features):
   - Implement a database like PostgreSQL
   - Use connection pooling

### Vertical Scaling

1. **Increase Resources**:
   - Upgrade CPU, RAM, and disk space
   - Adjust configuration accordingly

## Troubleshooting

### Common Issues

1. **Application Won't Start**:
   - Check logs: `sudo journalctl -u 4kvideoreaper`
   - Verify permissions: `sudo chown -R www-data:www-data /var/www/4KVideoReaper/downloads`

2. **Downloads Fail**:
   - Check if Aria2 is installed: `aria2c --version`
   - Check if FFmpeg is installed: `ffmpeg -version`
   - Check network connectivity: `curl -I https://www.youtube.com`

3. **Nginx Errors**:
   - Check configuration: `sudo nginx -t`
   - Check logs: `sudo tail -f /var/log/nginx/error.log`

4. **SSL/TLS Issues**:
   - Verify certificates: `sudo certbot certificates`
   - Check Nginx SSL configuration

### Getting Help

If you encounter issues not covered in this guide:

1. Check the [GitHub Issues](https://github.com/yourusername/4KVideoReaper/issues)
2. Create a new issue with detailed information about your problem
3. Include logs and system information

---

## License

4K Video Reaper is licensed under the MIT License. See the LICENSE file for details.

---

*Last updated: March 19, 2025*
