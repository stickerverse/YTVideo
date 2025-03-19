#!/bin/bash
# 4K Video Reaper Deployment Script
# This script automates the deployment of the 4K Video Reaper application

# Exit on error
set -e

# Configuration
APP_NAME="4KVideoReaper"
APP_DIR="/var/www/${APP_NAME}"
VENV_DIR="${APP_DIR}/venv"
REPO_URL="https://github.com/yourusername/4KVideoReaper.git"
DOMAIN_NAME="4kvideoreaper.com" # Change to your actual domain
NGINX_CONF="/etc/nginx/sites-available/4kvideoreaper.conf"
SERVICE_FILE="/etc/systemd/system/4kvideoreaper.service"
LOG_DIR="/var/log/4kvideoreaper"

# Color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function for printing status messages
print_status() {
  echo -e "${YELLOW}[*]${NC} $1"
}

print_success() {
  echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
  echo -e "${RED}[!]${NC} $1"
}

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    print_error "This script must be run as root"
    exit 1
fi

# Create deployment directory
print_status "Creating deployment directory..."
mkdir -p ${APP_DIR}
mkdir -p ${LOG_DIR}

# Update system packages
print_status "Updating system packages..."
apt update
apt upgrade -y

# Install dependencies
print_status "Installing required system packages..."
apt install -y python3-pip python3-venv nginx aria2 ffmpeg git certbot python3-certbot-nginx supervisor

# Clone or update repository
if [ -d "${APP_DIR}/.git" ]; then
    print_status "Repository exists, updating..."
    cd ${APP_DIR}
    git pull
else
    print_status "Cloning repository..."
    git clone ${REPO_URL} ${APP_DIR}
    cd ${APP_DIR}
fi

# Set proper permissions
print_status "Setting permissions..."
chown -R www-data:www-data ${APP_DIR}
chmod -R 755 ${APP_DIR}
chown -R www-data:www-data ${LOG_DIR}

# Create virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv ${VENV_DIR}
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source ${VENV_DIR}/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .

# Create configuration
print_status "Setting up configuration..."
if [ ! -f "${APP_DIR}/config.json" ]; then
    cp ${APP_DIR}/config.example.json ${APP_DIR}/config.json
    # Update configuration with secure values
    # This is a basic example - in production, use environment-specific configs
    sed -i 's|"download_dir": "~/Downloads/youtube"|"download_dir": "'${APP_DIR}'/downloads"|g' ${APP_DIR}/config.json
    sed -i 's|"max_concurrent": 3|"max_concurrent": 5|g' ${APP_DIR}/config.json
    
    # Create downloads directory
    mkdir -p ${APP_DIR}/downloads
    chown -R www-data:www-data ${APP_DIR}/downloads
    chmod 755 ${APP_DIR}/downloads
fi

# Copy systemd service file
print_status "Setting up systemd service..."
cp ${APP_DIR}/4kvideoreaper.service ${SERVICE_FILE}

# Update the service file with the correct paths
sed -i "s|/var/www/4KVideoReaper|${APP_DIR}|g" ${SERVICE_FILE}

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable 4kvideoreaper
systemctl start 4kvideoreaper

# Configure Nginx
print_status "Setting up Nginx configuration..."
cp ${APP_DIR}/4kvideoreaper.conf ${NGINX_CONF}

# Update Nginx configuration with correct domain and path
sed -i "s|server_name .*;|server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};|g" ${NGINX_CONF}
sed -i "s|/var/www/4KVideoReaper|${APP_DIR}|g" ${NGINX_CONF}

# Enable and reload Nginx
ln -sf ${NGINX_CONF} /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Set up HTTPS with Let's Encrypt
print_status "Setting up HTTPS with Let's Encrypt..."
certbot --nginx -d ${DOMAIN_NAME} -d www.${DOMAIN_NAME} --non-interactive --agree-tos --email admin@${DOMAIN_NAME} --redirect

# Configure log rotation
print_status "Setting up log rotation..."
cat > /etc/logrotate.d/4kvideoreaper <<EOF
${LOG_DIR}/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create
    sharedscripts
    postrotate
        systemctl reload 4kvideoreaper
    endscript
}
EOF

# Check service status
print_status "Checking service status..."
if systemctl is-active --quiet 4kvideoreaper; then
    print_success "4K Video Reaper service is active and running!"
else
    print_error "Service is not running. Check logs with: journalctl -u 4kvideoreaper"
fi

print_success "Deployment completed! 4K Video Reaper should be accessible at: https://${DOMAIN_NAME}"
print_status "Run the following command to check for errors: systemctl status 4kvideoreaper"
print_status "To view logs: tail -f ${LOG_DIR}/app.log"
