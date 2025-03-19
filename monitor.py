#!/usr/bin/env python3
"""
4K Video Reaper Monitoring Script
---------------------------------

This script monitors the health of the 4K Video Reaper application,
checks system resources, and can restart the service if needed.
"""

import os
import sys
import time
import json
import argparse
import subprocess
import requests
import psutil
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('monitor.log')
    ]
)
logger = logging.getLogger('monitor')

# Default configuration
DEFAULT_CONFIG = {
    'api_url': 'http://localhost:8000/api/status',
    'service_name': '4kvideoreaper',
    'check_interval': 60,  # seconds
    'restart_threshold': 3,  # consecutive failures before restart
    'notify_threshold': 5,  # consecutive failures before notification
    'resource_limits': {
        'cpu_percent': 90,
        'memory_percent': 85,
        'disk_percent': 90,
        'downloads_dir_size': 10 * 1024 * 1024 * 1024  # 10 GB
    },
    'downloads_dir': '/var/www/4KVideoReaper/downloads',
    'log_dir': '/var/log/4kvideoreaper',
    'email': {
        'enabled': False,
        'from': 'monitor@4kvideoreaper.com',
        'to': 'admin@example.com',
        'smtp_host': 'smtp.example.com',
        'smtp_port': 587,
        'smtp_user': 'username',
        'smtp_pass': 'password'
    }
}

class ServiceMonitor:
    """Monitor for the 4K Video Reaper service"""
    
    def __init__(self, config=None):
        """Initialize the monitor with configuration"""
        self.config = DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        self.failures = 0
        self.last_notification = None
        self.service_running = False
        self.last_status = None
    
    def check_api_health(self):
        """Check if the API is healthy by making a request to the status endpoint"""
        try:
            response = requests.get(
                self.config['api_url'],
                timeout=10
            )
            
            if response.status_code == 200:
                self.last_status = response.json()
                logger.info(f"API health check successful: {response.status_code}")
                return True
            else:
                logger.error(f"API health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"API health check error: {str(e)}")
            return False
    
    def check_service_status(self):
        """Check if the service is running using systemctl"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', self.config['service_name']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.service_running = result.stdout.strip() == 'active'
            logger.info(f"Service status: {'Running' if self.service_running else 'Not running'}")
            return self.service_running
        except subprocess.SubprocessError as e:
            logger.error(f"Error checking service status: {str(e)}")
            return False
    
    def check_resources(self):
        """Check system resources"""
        issues = []
        
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > self.config['resource_limits']['cpu_percent']:
            issues.append(f"High CPU usage: {cpu_percent}%")
        
        # Check memory usage
        memory = psutil.virtual_memory()
        if memory.percent > self.config['resource_limits']['memory_percent']:
            issues.append(f"High memory usage: {memory.percent}%")
        
        # Check disk usage
        disk = psutil.disk_usage('/')
        if disk.percent > self.config['resource_limits']['disk_percent']:
            issues.append(f"High disk usage: {disk.percent}%")
        
        # Check downloads directory size
        downloads_dir = self.config['downloads_dir']
        if os.path.exists(downloads_dir):
            dir_size = get_dir_size(downloads_dir)
            if dir_size > self.config['resource_limits']['downloads_dir_size']:
                size_gb = dir_size / (1024 * 1024 * 1024)
                issues.append(f"Downloads directory too large: {size_gb:.2f} GB")
        
        # Log results
        if issues:
            logger.warning(f"Resource issues found: {', '.join(issues)}")
        else:
            logger.info("Resource check passed")
        
        return issues
    
    def restart_service(self):
        """Restart the service"""
        try:
            logger.warning(f"Restarting service: {self.config['service_name']}")
            subprocess.run(
                ['systemctl', 'restart', self.config['service_name']],
                check=True
            )
            logger.info("Service restart initiated")
            return True
        except subprocess.SubprocessError as e:
            logger.error(f"Error restarting service: {str(e)}")
            return False
    
    def clean_old_logs(self, days=7):
        """Clean log files older than the specified days"""
        log_dir = self.config['log_dir']
        if not os.path.exists(log_dir):
            logger.warning(f"Log directory not found: {log_dir}")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Cleaning logs older than {days} days")
        
        for file_path in Path(log_dir).glob("*.log.*"):
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            if file_time < cutoff_date:
                try:
                    os.remove(file_path)
                    logger.info(f"Removed old log file: {file_path}")
                except OSError as e:
                    logger.error(f"Error removing log file {file_path}: {str(e)}")
    
    def clean_old_downloads(self, days=30):
        """Clean downloads older than the specified days"""
        downloads_dir = self.config['downloads_dir']
        if not os.path.exists(downloads_dir):
            logger.warning(f"Downloads directory not found: {downloads_dir}")
            return
        
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Cleaning downloads older than {days} days")
        
        for file_path in Path(downloads_dir).glob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_time < cutoff_date:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed old download: {file_path}")
                    except OSError as e:
                        logger.error(f"Error removing download {file_path}: {str(e)}")
    
    def send_notification(self, subject, message):
        """Send an email notification"""
        if not self.config['email']['enabled']:
            logger.info("Email notifications are disabled")
            return False
        
        # Check if we've sent a notification recently
        now = datetime.now()
        if self.last_notification and now - self.last_notification < timedelta(hours=1):
            logger.info("Skipping notification, already sent one within the last hour")
            return False
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = subject
            msg['From'] = self.config['email']['from']
            msg['To'] = self.config['email']['to']
            
            smtp = smtplib.SMTP(self.config['email']['smtp_host'], self.config['email']['smtp_port'])
            smtp.starttls()
            smtp.login(self.config['email']['smtp_user'], self.config['email']['smtp_pass'])
            smtp.send_message(msg)
            smtp.quit()
            
            self.last_notification = now
            logger.info(f"Notification sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            return False
    
    def run(self):
        """Run the monitoring loop"""
        logger.info("Starting 4K Video Reaper monitoring")
        
        while True:
            try:
                # Check service status
                service_ok = self.check_service_status()
                
                # Check API health if service is running
                api_ok = False
                if service_ok:
                    api_ok = self.check_api_health()
                
                # Perform resource checks
                resource_issues = self.check_resources()
                
                # Handle failures
                if service_ok and api_ok and not resource_issues:
                    self.failures = 0
                    logger.info("All checks passed")
                else:
                    self.failures += 1
                    logger.warning(f"Check failed (attempt {self.failures})")
                    
                    # Restart service after threshold reached
                    if self.failures >= self.config['restart_threshold']:
                        self.restart_service()
                        # Reset failure count to give the service time to recover
                        self.failures = 0
                    
                    # Send notification after threshold reached
                    if self.failures >= self.config['notify_threshold']:
                        subject = "4K Video Reaper Monitor Alert"
                        message = f"""
                        The 4K Video Reaper service is experiencing issues:
                        
                        Service Running: {'Yes' if service_ok else 'No'}
                        API Healthy: {'Yes' if api_ok else 'No'}
                        Resource Issues: {', '.join(resource_issues) if resource_issues else 'None'}
                        
                        Failures: {self.failures}
                        
                        Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                        """
                        self.send_notification(subject, message)
                
                # Perform maintenance tasks periodically (every 6 hours)
                if datetime.now().hour % 6 == 0 and datetime.now().minute < 5:
                    self.clean_old_logs()
                    self.clean_old_downloads()
                
                # Wait for the next check
                time.sleep(self.config['check_interval'])
            
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                time.sleep(60)  # Wait a minute before retrying

def get_dir_size(path):
    """Get the total size of a directory in bytes"""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if os.path.exists(fp) and not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def load_config(config_file):
    """Load configuration from a JSON file"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return None

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='4K Video Reaper Service Monitor')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--check-only', action='store_true', help='Perform a single check and exit')
    args = parser.parse_args()
    
    # Load configuration
    config = None
    if args.config:
        config = load_config(args.config)
    
    # Create monitor
    monitor = ServiceMonitor(config)
    
    # Run monitor
    if args.check_only:
        service_ok = monitor.check_service_status()
        api_ok = monitor.check_api_health()
        resource_issues = monitor.check_resources()
        
        print(f"Service Running: {'Yes' if service_ok else 'No'}")
        print(f"API Healthy: {'Yes' if api_ok else 'No'}")
        print(f"Resource Issues: {', '.join(resource_issues) if resource_issues else 'None'}")
        
        sys.exit(0 if service_ok and api_ok and not resource_issues else 1)
    else:
        monitor.run()

if __name__ == '__main__':
    main()
