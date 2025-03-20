#!/usr/bin/env python3
"""
Health Check Script for 4K Video Reaper
--------------------------------------

This script checks if the 4K Video Reaper service is healthy and
sends an alert if there are any issues.
"""

import os
import sys
import time
import argparse
import logging
import json
import subprocess
import requests
import psutil
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('healthcheck.log')
    ]
)
logger = logging.getLogger('healthcheck')

class HealthCheck:
    """Health check class for the 4K Video Reaper service."""
    
    def __init__(self, api_url="http://localhost:$PORT/api/status", max_failures=3):
        """
        Initialize the health check.
        
        Args:
            api_url: URL of the API status endpoint
            max_failures: Maximum number of consecutive failures before taking action
        """
        self.api_url = api_url.replace("$PORT", os.environ.get("PORT", "10000"))
        self.max_failures = max_failures
        self.failures = 0
        self.last_check_time = None
        self.last_status = None
    
    def check_api(self):
        """
        Check if the API is healthy by making a request to the status endpoint.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            self.last_check_time = datetime.now()
            
            if response.status_code == 200:
                data = response.json()
                self.last_status = data
                logger.info(f"API is healthy: {response.status_code}")
                return True
            else:
                logger.error(f"API health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logger.error(f"API health check error: {str(e)}")
            return False
    
    def check_system_resources(self):
        """
        Check system resources (CPU, memory, disk).
        
        Returns:
            Dict with resource usage and warnings
        """
        resources = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent,
            'warnings': []
        }
        
        # Check for resource issues
        if resources['cpu_percent'] > 90:
            resources['warnings'].append(f"High CPU usage: {resources['cpu_percent']}%")
            
        if resources['memory_percent'] > 90:
            resources['warnings'].append(f"High memory usage: {resources['memory_percent']}%")
            
        if resources['disk_percent'] > 95:
            resources['warnings'].append(f"High disk usage: {resources['disk_percent']}%")
        
        return resources
    
    def check_downloads_directory(self, downloads_dir="/tmp/downloads"):
        """
        Check the downloads directory.
        
        Args:
            downloads_dir: Path to the downloads directory
            
        Returns:
            Dict with directory info and warnings
        """
        info = {
            'exists': os.path.exists(downloads_dir),
            'is_writable': os.access(downloads_dir, os.W_OK) if os.path.exists(downloads_dir) else False,
            'file_count': 0,
            'total_size': 0,
            'warnings': []
        }
        
        if not info['exists']:
            info['warnings'].append(f"Downloads directory does not exist: {downloads_dir}")
            return info
        
        if not info['is_writable']:
            info['warnings'].append(f"Downloads directory is not writable: {downloads_dir}")
        
        # Count files and total size
        for filename in os.listdir(downloads_dir):
            file_path = os.path.join(downloads_dir, filename)
            if os.path.isfile(file_path):
                info['file_count'] += 1
                info['total_size'] += os.path.getsize(file_path)
        
        # Check for potential issues
        disk_usage = psutil.disk_usage(downloads_dir)
        if disk_usage.free < 100 * 1024 * 1024:  # Less than 100MB free
            info['warnings'].append(f"Very low disk space: {disk_usage.free / (1024 * 1024):.2f} MB free")
        elif disk_usage.free < 1 * 1024 * 1024 * 1024:  # Less than 1GB free
            info['warnings'].append(f"Low disk space: {disk_usage.free / (1024 * 1024 * 1024):.2f} GB free")
        
        if info['file_count'] > 100:
            info['warnings'].append(f"Large number of files in downloads directory: {info['file_count']}")
        
        return info
    
    def check_dependencies(self):
        """
        Check if required dependencies are installed.
        
        Returns:
            Dict with dependency status and warnings
        """
        dependencies = {
            'ffmpeg': self._check_command(['ffmpeg', '-version']),
            'aria2c': self._check_command(['aria2c', '--version']),
            'yt-dlp': self._check_python_import('yt_dlp'),
            'flask': self._check_python_import('flask'),
            'warnings': []
        }
        
        for dep, status in dependencies.items():
            if dep != 'warnings' and not status:
                dependencies['warnings'].append(f"Dependency not found: {dep}")
        
        return dependencies
    
    def _check_command(self, command):
        """Check if a command is available and can be executed."""
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _check_python_import(self, module_name):
        """Check if a Python module can be imported."""
        cmd = [
            sys.executable,
            '-c',
            f"import {module_name}; print('Module {module_name} found')"
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def run_health_check(self, downloads_dir="/tmp/downloads"):
        """
        Run a complete health check.
        
        Args:
            downloads_dir: Path to the downloads directory
            
        Returns:
            Dict with health check results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'api_healthy': self.check_api(),
            'system_resources': self.check_system_resources(),
            'downloads_directory': self.check_downloads_directory(downloads_dir),
            'dependencies': self.check_dependencies(),
            'overall_status': 'healthy',
            'warnings': []
        }
        
        # Collect all warnings
        for category in ['system_resources', 'downloads_directory', 'dependencies']:
            if category in results and 'warnings' in results[category]:
                results['warnings'].extend(results[category]['warnings'])
        
        # Determine overall status
        if not results['api_healthy']:
            results['overall_status'] = 'unhealthy'
            results['warnings'].append("API is not responding")
            self.failures += 1
        else:
            self.failures = 0
        
        if results['warnings']:
            if results['overall_status'] == 'healthy':
                results['overall_status'] = 'degraded'
        
        logger.info(f"Health check completed. Status: {results['overall_status']}")
        if results['warnings']:
            for warning in results['warnings']:
                logger.warning(warning)
        
        return results
    
    def take_action_if_needed(self):
        """
        Take action if the service is unhealthy for too many consecutive checks.
        
        Returns:
            True if action was taken, False otherwise
        """
        if self.failures >= self.max_failures:
            logger.error(f"Service has failed {self.failures} consecutive health checks, taking action")
            
            # Here you could implement remediation actions like:
            # 1. Sending an alert email/notification
            # 2. Attempting to restart the service
            # 3. Clearing temporary files
            
            # For now, just log the issue
            logger.error("CRITICAL: Service needs attention!")
            
            return True
        
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Health check for 4K Video Reaper')
    parser.add_argument('--api-url', type=str, default="http://localhost:$PORT/api/status",
                        help='URL of the API status endpoint')
    parser.add_argument('--downloads-dir', type=str, default=os.environ.get('DOWNLOAD_DIR', '/tmp/downloads'),
                        help='Path to the downloads directory')
    parser.add_argument('--max-failures', type=int, default=3,
                        help='Maximum number of consecutive failures before taking action')
    parser.add_argument('--output-json', type=str, default=None,
                        help='Path to write health check results as JSON')
    parser.add_argument('--continuous', action='store_true',
                        help='Run health checks continuously')
    parser.add_argument('--interval', type=int, default=300,
                        help='Interval between health checks in seconds (when using --continuous)')
    args = parser.parse_args()
    
    health_check = HealthCheck(
        api_url=args.api_url,
        max_failures=args.max_failures
    )
    
    try:
        if args.continuous:
            logger.info(f"Starting continuous health checks every {args.interval} seconds")
            
            while True:
                results = health_check.run_health_check(args.downloads_dir)
                
                if args.output_json:
                    with open(args.output_json, 'w') as f:
                        json.dump(results, f, indent=2)
                
                health_check.take_action_if_needed()
                
                time.sleep(args.interval)
        else:
            # Run a single health check
            results = health_check.run_health_check(args.downloads_dir)
            
            if args.output_json:
                with open(args.output_json, 'w') as f:
                    json.dump(results, f, indent=2)
            
            # Exit with non-zero status if health check failed
            if results['overall_status'] != 'healthy':
                return 1
    except KeyboardInterrupt:
        logger.info("Health check interrupted")
    except Exception as e:
        logger.error(f"Error during health check: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
