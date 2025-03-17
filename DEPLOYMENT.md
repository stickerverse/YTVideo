# Deploying 4K Video Reaper

This guide will help you deploy the 4K Video Reaper application to a web server so it's accessible at your domain (4kvideoreaper.com).

## Prerequisites

- A web server with Ubuntu/Debian (recommended)
- Python 3.7+ installed
- Nginx web server
- Domain name configured to point to your server

## Deployment Steps

### 1. Prepare the Server

```bash
# Update the system
sudo apt update
sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx aria2
```

### 2. Set Up the Application Directory

```bash
# Create application directory
sudo mkdir -p /var/www/4KVideoReaper
sudo chown -R $USER:$USER /var/www/4KVideoReaper

# Clone the repository (replace with your actual repository)
git clone https://github.com/stickerverse/4KVideoReaper.git /var/www/4KVideoReaper

# Navigate to the application directory
cd /var/www/4KVideoReaper
```

### 3. Create a Virtual Environment

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r web/requirements.txt
pip install -e .
```

### 4. Configure the Web Server

```bash
# Create Nginx site configuration
sudo cp 4kvideoreaper.conf /etc/nginx/sites-available/

# Create a symlink to enable the site
sudo ln -s /etc/nginx/sites-available/4kvideoreaper.conf /etc/nginx/sites-enabled/

# Test Nginx configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 5. Set Up the Application Service

```bash
# Copy the service file
sudo cp 4kvideoreaper.service /etc/systemd/system/

# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable 4kvideoreaper

# Start the service
sudo systemctl start 4kvideoreaper

# Check status
sudo systemctl status 4kvideoreaper
```

### 6. Set Up HTTPS with Let's Encrypt (Optional but Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d 4kvideoreaper.com -d www.4kvideoreaper.com

# Follow the prompts to complete the setup
```

### 7. Verify the Deployment

1. Open your web browser and navigate to your domain (e.g., https://4kvideoreaper.com)
2. Test downloading a YouTube video to ensure everything is working correctly

## Troubleshooting

### Check Logs

If you encounter issues, check the logs:

```bash
# View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# View application logs
sudo journalctl -u 4kvideoreaper.service -f
```

### Common Issues

1. **Permission Issues**: Make sure the web service has permission to access the download directory
   ```bash
   sudo chown -R www-data:www-data /var/www/4KVideoReaper/web/public
   ```

2. **Socket Connection Error**: Check if the socket file exists and has correct permissions
   ```bash
   sudo chown www-data:www-data /var/www/4KVideoReaper/web/4kvideoreaper.sock
   ```

3. **API Not Responding**: Check if the Flask application is running
   ```bash
   sudo systemctl restart 4kvideoreaper
   ```

## Updating the Application

To update the application with new changes:

```bash
# Navigate to the application directory
cd /var/www/4KVideoReaper

# Pull the latest changes
git pull

# Activate the virtual environment
source venv/bin/activate

# Install any new dependencies
pip install -r requirements.txt
pip install -r web/requirements.txt

# Restart the service
sudo systemctl restart 4kvideoreaper
```

## Production Optimization

For better performance in production:

1. **Increase Worker Count**: Edit the service file to increase Gunicorn workers (usually 2 * CPU cores + 1)
2. **Set Up Caching**: Configure Nginx caching for static assets
3. **Implement Rate Limiting**: Add rate limiting to prevent abuse

## Docker Deployment (Alternative)

If you prefer using Docker, you can containerize the application:

1. Create a `Dockerfile` in the project root
2. Build and deploy with Docker Compose

This approach simplifies deployment across different environments.