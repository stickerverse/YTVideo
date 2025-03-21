"""
4K Video Reaper - Production-Ready YouTube Downloader API
--------------------------------------------------------

This module provides a robust, secure, and performant API for downloading 
YouTube videos with advanced features and comprehensive error handling.
"""

import os
import re
import uuid
import time
import json
import logging
import threading
import traceback
import shutil
import secrets
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps

import yt_dlp
import requests
import flask
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_talisman import Talisman

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('youtube_downloader.log')
    ]
)
logger = logging.getLogger(__name__)

# Configuration and Security
class Config:
    """Application configuration management"""
    
    # Core Configuration
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/tmp/downloads')
    MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', 3))
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 10))
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD', 60))  # seconds
    
    # Security Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    ALLOWED_DOMAINS = os.environ.get('ALLOWED_DOMAINS', 'youtube.com,youtu.be').split(',')
    
    # Proxy and External Service Configuration
    DEFAULT_PROXY = os.environ.get('DEFAULT_PROXY')
    CAPTCHA_API_KEY = os.environ.get('CAPTCHA_API_KEY')
    
    # Download Restrictions
    MAX_VIDEO_SIZE_MB = int(os.environ.get('MAX_VIDEO_SIZE_MB', 1024))  # 1GB max
    MAX_DOWNLOAD_DURATION_SECONDS = int(os.environ.get('MAX_DOWNLOAD_DURATION_SECONDS', 3600))  # 1 hour max

# Create download directory if it doesn't exist
os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)

# Flask Application Setup
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = Config.MAX_VIDEO_SIZE_MB * 1024 * 1024
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Apply proxy fix for proper IP detection behind proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Enable CORS for all origins
CORS(app)

# Enable Talisman for security headers in production
if os.environ.get('ENVIRONMENT') == 'production':
    talisman = Talisman(
        app,
        content_security_policy={
            'default-src': "'self'",
            'img-src': "'self' data: https:",
            'script-src': "'self' https://cdnjs.cloudflare.com",
            'style-src': "'self' https://cdnjs.cloudflare.com https://fonts.googleapis.com 'unsafe-inline'",
            'font-src': "'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            'connect-src': "'self'"
        },
        force_https=False,  # Set to True if you're using HTTPS directly (not behind proxy)
        strict_transport_security=True,
        strict_transport_security_preload=True,
        session_cookie_secure=True,
        referrer_policy='no-referrer-when-downgrade'
    )

# Rate Limiting and Download Tracking
class RateLimiter:
    """Improved in-memory rate limiting implementation with IP tracking"""
    _request_counts = {}
    _cleanup_time = time.time()
    _lock = threading.Lock()
    
    @classmethod
    def is_allowed(cls, ip: str) -> bool:
        """Check if the IP is allowed to make a request"""
        now = time.time()
        
        # Clean up old entries every 10 minutes
        with cls._lock:
            if now - cls._cleanup_time > 600:  # 10 minutes
                cls._cleanup()
                cls._cleanup_time = now
            
            # Initialize if IP not seen before
            if ip not in cls._request_counts:
                cls._request_counts[ip] = {
                    'count': 0,
                    'reset_time': now + Config.RATE_LIMIT_PERIOD
                }
            
            ip_data = cls._request_counts[ip]
            
            # Reset if period has passed
            if now > ip_data['reset_time']:
                ip_data['count'] = 0
                ip_data['reset_time'] = now + Config.RATE_LIMIT_PERIOD
            
            # Increment and check
            ip_data['count'] += 1
            
            return ip_data['count'] <= Config.RATE_LIMIT_REQUESTS
    
    @classmethod
    def _cleanup(cls):
        """Remove expired entries"""
        now = time.time()
        for ip in list(cls._request_counts.keys()):
            if now > cls._request_counts[ip]['reset_time']:
                del cls._request_counts[ip]


class DownloadManager:
    """Manages download tracking and processing"""
    _downloads: Dict[str, Dict[str, Any]] = {}
    _lock = threading.Lock()
    
    @classmethod
    def create_download(cls, url: str, format_id: str) -> str:
        """Create a new download entry"""
        download_id = str(uuid.uuid4())
        
        with cls._lock:
            cls._downloads[download_id] = {
                'id': download_id,
                'url': url,
                'format_id': format_id,
                'status': 'queued',
                'progress': 0,
                'started_at': time.time(),
                'file_path': None,
                'error': None
            }
        
        return download_id
    
    @classmethod
    def update_download(cls, download_id: str, **kwargs):
        """Update download status"""
        with cls._lock:
            if download_id in cls._downloads:
                cls._downloads[download_id].update(kwargs)
    
    @classmethod
    def get_download(cls, download_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve download information"""
        return cls._downloads.get(download_id)

    @classmethod
    def cleanup_old_downloads(cls, max_age_hours: int = 24):
        """Remove old download entries"""
        with cls._lock:
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            
            for download_id in list(cls._downloads.keys()):
                download = cls._downloads[download_id]
                age = current_time - download.get('started_at', 0)
                
                if age > max_age_seconds:
                    # Try to remove the file if it exists
                    file_path = download.get('file_path')
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed old download file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error removing file {file_path}: {e}")
                    
                    # Remove the download entry
                    del cls._downloads[download_id]
                    logger.info(f"Removed old download entry: {download_id}")


def api_error_handler(f):
    """Error handling decorator for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Client error: {str(e)}")
            return jsonify({
                'error': str(e),
                'status': 'error'
            }), 400
        except RuntimeError as e:
            logger.error(f"Service error: {str(e)}")
            return jsonify({
                'error': "Service temporarily unavailable. Please try again later.",
                'status': 'error'
            }), 503
        except Exception as e:
            logger.critical(f"Unexpected error: {str(e)}", exc_info=True)
            return jsonify({
                'error': "An unexpected error occurred",
                'status': 'error'
            }), 500
    return decorated_function


def validate_youtube_url(url: str) -> bool:
    """
    Validate if the URL is a legitimate YouTube URL
    
    Args:
        url: URL to validate
    
    Returns:
        Boolean indicating URL validity
    """
    youtube_patterns = [
        r'^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+',
        r'^(https?://)?(www\.)?youtu\.be/[\w-]+',
        r'^(https?://)?(www\.)?youtube\.com/embed/[\w-]+',
        r'^(https?://)?(www\.)?youtube\.com/v/[\w-]+'
    ]
    return any(re.match(pattern, url) for pattern in youtube_patterns)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially dangerous characters
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove or replace potentially problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit filename length
    filename = filename[:255]
    return filename


def check_disk_space():
    """
    Check available disk space and perform aggressive cleanup if needed
    """
    try:
        # Get disk stats
        stats = shutil.disk_usage(Config.DOWNLOAD_DIR)
        free_space_mb = stats.free / (1024 * 1024)
        total_space_mb = stats.total / (1024 * 1024)
        used_percent = (stats.used / stats.total) * 100
        
        logger.info(f"Disk space: {free_space_mb:.2f}MB free out of {total_space_mb:.2f}MB total ({used_percent:.1f}% used)")
        
        # If less than 500MB free or more than 80% used, perform aggressive cleanup
        if free_space_mb < 500 or used_percent > 80:
            logger.warning(f"Low disk space: {free_space_mb:.2f}MB free, {used_percent:.1f}% used. Performing aggressive cleanup.")
            # Clean up downloads older than 1 hour
            cleanup_old_files(Config.DOWNLOAD_DIR, max_age_hours=1)
            
            # If still critical (less than 100MB), remove all files
            stats = shutil.disk_usage(Config.DOWNLOAD_DIR)
            free_space_mb = stats.free / (1024 * 1024)
            if free_space_mb < 100:
                logger.critical(f"Critical disk space: {free_space_mb:.2f}MB free. Removing all downloads.")
                cleanup_old_files(Config.DOWNLOAD_DIR, max_age_hours=0)
                
        return free_space_mb
        
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return 0


def cleanup_old_files(directory: str, max_age_hours: int = 24):
    """
    Clean up old files in a directory
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files in hours before deletion
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return
    
    try:
        current_time = time.time()
        # Convert hours to seconds
        max_age_seconds = max_age_hours * 3600
        
        # If max_age_hours is 0, delete all files
        if max_age_hours == 0:
            logger.warning(f"Removing ALL files from {directory}")
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {e}")
            return
        
        # Otherwise delete files older than max_age_hours
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_age_seconds:
                    try:
                        os.remove(file_path)
                        logger.info(f"Removed old file: {file_path} (age: {file_age/3600:.1f} hours)")
                    except Exception as e:
                        logger.error(f"Error removing file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


def get_video_info(url: str, use_proxy: bool = False) -> Dict[str, Any]:
    """
    Retrieve comprehensive video information
    
    Args:
        url: YouTube video URL
        use_proxy: Whether to use a proxy
    
    Returns:
        Dictionary with video metadata
    """
    try:
        # Configurable yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'nooverwrites': True,
            'no_color': True,
            'socket_timeout': 30,  # 30 second timeout
            'retries': 3,          # Retry 3 times on failure
        }
        
        # Add proxy if requested and available
        if use_proxy and Config.DEFAULT_PROXY:
            ydl_opts['proxy'] = Config.DEFAULT_PROXY
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Validate download duration
            duration = info.get('duration', 0)
            if duration > Config.MAX_DOWNLOAD_DURATION_SECONDS:
                raise ValueError(f"Video too long. Max duration: {Config.MAX_DOWNLOAD_DURATION_SECONDS} seconds")
            
            # Process formats
            formats = []
            for fmt in info.get('formats', []):
                # Filter out audio-only and video-only streams
                if fmt.get('vcodec', 'none') != 'none' and fmt.get('acodec', 'none') != 'none':
                    formats.append({
                        'format_id': fmt.get('format_id', ''),
                        'ext': fmt.get('ext', ''),
                        'resolution': f"{fmt.get('width', 'N/A')}x{fmt.get('height', 'N/A')}",
                        'filesize': fmt.get('filesize', 0),
                        'tbr': fmt.get('tbr', 0),  # True bit rate
                        'quality': f"{fmt.get('height', 0)}p"
                    })
            
            return {
                'id': info.get('id', ''),
                'title': info.get('title', 'Unknown Title'),
                'uploader': info.get('uploader', 'Unknown Channel'),
                'duration': duration,
                'view_count': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            }
    
    except Exception as e:
        logger.error(f"Video info retrieval error: {e}")
        raise ValueError(f"Could not retrieve video information: {str(e)}")


def serve_and_delete(file_path, filename):
    """
    Serve a file for download and schedule it for deletion after a short delay
    
    Args:
        file_path: Path to the file
        filename: Desired filename for download
    
    Returns:
        Flask response for file download
    """
    if not os.path.exists(file_path):
        return jsonify({
            'error': 'File not found',
            'status': 'error'
        }), 404
    
    # Schedule file for deletion after a delay (30 seconds)
    def delete_after_delay(path, delay=30):
        def delayed_delete():
            time.sleep(delay)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Deleted file after serving: {path}")
            except Exception as e:
                logger.error(f"Error deleting file {path}: {e}")
        
        # Start a thread to delete the file
        thread = threading.Thread(target=delayed_delete, daemon=True)
        thread.start()
    
    # Schedule deletion
    delete_after_delay(file_path)
    
    # Serve the file
    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype='application/octet-stream'
    )


def download_video(download_id: str, url: str, format_id: str, subtitles: bool = False):
    """
    Download a YouTube video
    
    Args:
        download_id: Unique download identifier
        url: YouTube video URL
        format_id: Selected video format
        subtitles: Whether to download subtitles
    """
    try:
        # Update download status to processing
        DownloadManager.update_download(download_id, status='downloading')
        
        # Check disk space
        free_space_mb = check_disk_space()
        if free_space_mb < 100:
            raise RuntimeError(f"Insufficient disk space: {free_space_mb:.2f}MB free")
        
        # Prepare download options
        ydl_opts = {
            'format': format_id,
            'outtmpl': os.path.join(Config.DOWNLOAD_DIR, f'{download_id}_%(title)s.%(ext)s'),
            'nooverwrites': True,
            'no_color': True,
            'progress_hooks': [lambda d: progress_hook(download_id, d)],
            'noplaylist': True,
            'writesubtitles': subtitles,
            'subtitleslangs': ['en'] if subtitles else [],
            # Add request timeout
            'socket_timeout': 30,
            # Add retry settings
            'retries': 3,
            'fragment_retries': 3,
            # Add format sorting
            'format_sort': ['res:1080', 'ext:mp4:m4a', 'size'],
            # Add postprocessor options for better format conversions
            'postprocessor_args': {
                'ffmpeg': ['-threads', '2', '-cpu-used', '0', '-b:v', '0', '-crf', '22']
            }
        }
        
        # Add proxy if configured
        if Config.DEFAULT_PROXY:
            ydl_opts['proxy'] = Config.DEFAULT_PROXY
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Start download with timeout
            download_thread = threading.Thread(
                target=lambda: ydl.extract_info(url, download=True)
            )
            download_thread.start()
            
            # Wait for download to complete or timeout
            download_thread.join(timeout=Config.MAX_DOWNLOAD_DURATION_SECONDS)
            
            if download_thread.is_alive():
                # Download is taking too long, cancel it
                DownloadManager.update_download(
                    download_id, 
                    status='failed', 
                    error='Download timeout exceeded',
                    progress=0
                )
                logger.warning(f"Download timeout for {download_id}")
                return
            
            # Find the downloaded file
            for filename in os.listdir(Config.DOWNLOAD_DIR):
                if filename.startswith(f"{download_id}_"):
                    file_path = os.path.join(Config.DOWNLOAD_DIR, filename)
                    
                    # Update download with file information
                    DownloadManager.update_download(
                        download_id, 
                        status='completed', 
                        file_path=file_path,
                        progress=100
                    )
                    
                    logger.info(f"Download completed: {file_path}")
                    return file_path
            
            # If we get here, no file was found
            raise RuntimeError("Download completed but no file was found")
    
    except yt_dlp.utils.DownloadError as e:
        # Handle download errors
        logger.error(f"Download error for {download_id}: {e}")
        DownloadManager.update_download(
            download_id, 
            status='failed', 
            error=str(e),
            progress=0
        )
    except Exception as e:
        # Handle all other errors
        logger.error(f"Unexpected error for {download_id}: {e}")
        DownloadManager.update_download(
            download_id, 
            status='failed', 
            error="An unexpected error occurred",
            progress=0
        )


def progress_hook(download_id: str, d: Dict[str, Any]):
    """
    Track download progress
    
    Args:
        download_id: Unique download identifier
        d: Progress dictionary from yt-dlp
    """
    if d['status'] == 'downloading':
        downloaded_bytes = d.get('downloaded_bytes', 0)
        total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
        
        # Calculate percentage
        progress = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
        
        # Update download progress
        DownloadManager.update_download(
            download_id, 
            progress=progress,
            downloaded_bytes=downloaded_bytes,
            total_bytes=total_bytes,
            speed=d.get('speed', 0),
            eta=d.get('eta', 0)
        )


@app.route('/api/video-info', methods=['GET'])
@api_error_handler
def video_info_endpoint():
    """
    API endpoint to retrieve YouTube video information
    """
    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not RateLimiter.is_allowed(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'status': 'error'
        }), 429
    
    # Log request
    logger.info(f"Video info request from {client_ip}")
    
    url = request.args.get('url')
    use_proxy = request.args.get('proxy', 'false').lower() == 'true'
    
    if not url:
        return jsonify({
            'error': 'YouTube video URL is required',
            'status': 'error'
        }), 400
    
    if not validate_youtube_url(url):
        return jsonify({
            'error': 'Invalid YouTube URL',
            'status': 'error'
        }), 400
    
    video_data = get_video_info(url, use_proxy)
    return jsonify({
        'status': 'success',
        'data': video_data
    })


@app.route('/api/download', methods=['POST'])
@api_error_handler
def download_endpoint():
    """
    API endpoint to initiate a video download
    """
    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not RateLimiter.is_allowed(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'status': 'error'
        }), 429
    
    # Log request
    logger.info(f"Download request from {client_ip}")
    
    data = request.json
    
    url = data.get('url')
    format_id = data.get('formatId', 'best')
    download_subtitles = data.get('downloadSubtitles', False)
    
    if not url:
        return jsonify({
            'error': 'YouTube video URL is required',
            'status': 'error'
        }), 400
    
    if not validate_youtube_url(url):
        return jsonify({
            'error': 'Invalid YouTube URL',
            'status': 'error'
        }), 400
    
    # Check disk space
    free_space_mb = check_disk_space()
    if free_space_mb < 100:
        return jsonify({
            'error': f'Insufficient disk space: {free_space_mb:.2f}MB free',
            'status': 'error'
        }), 507  # Insufficient Storage
    
    # Create a download entry
    download_id = DownloadManager.create_download(url, format_id)
    
    # Start download in a separate thread
    download_thread = threading.Thread(
        target=download_video, 
        args=(download_id, url, format_id, download_subtitles),
        daemon=True
    )
    download_thread.start()
    
    return jsonify({
        'status': 'success',
        'downloadId': download_id
    })


@app.route('/api/download-status', methods=['GET'])
@api_error_handler
def download_status_endpoint():
    """
    API endpoint to check download status
    """
    download_id = request.args.get('id')
    
    if not download_id:
        return jsonify({
            'error': 'Download ID is required',
            'status': 'error'
        }), 400
    
    download_info = DownloadManager.get_download(download_id)
    
    if not download_info:
        return jsonify({
            'error': 'Download not found',
            'status': 'error'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': download_info
    })


@app.route('/api/download-file/<download_id>', methods=['GET'])
@api_error_handler
def download_file_endpoint(download_id):
    """
    API endpoint to serve downloaded file
    
    Args:
        download_id: Unique identifier for the download
    
    Returns:
        File download or error response
    """
    # Log request
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    logger.info(f"File download request from {client_ip} for {download_id}")
    
    # Retrieve download information
    download_info = DownloadManager.get_download(download_id)
    
    if not download_info:
        return jsonify({
            'error': 'Download not found',
            'status': 'error'
        }), 404
    
    # Check download status
    if download_info['status'] != 'completed':
        return jsonify({
            'error': 'Download not completed',
            'status': 'error'
        }), 400
    
    file_path = download_info.get('file_path')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({
            'error': 'File not found',
            'status': 'error'
        }), 404
    
    # Prepare file for download
    try:
        # Extract filename and sanitize
        filename = os.path.basename(file_path)
        sanitized_filename = secure_filename(filename)
        
        # Send file and schedule for deletion
        return serve_and_delete(file_path, sanitized_filename)
    except Exception as send_error:
        logger.error(f"Error sending file: {send_error}")
        return jsonify({
            'error': 'Error preparing file for download',
            'status': 'error'
        }), 500


@app.route('/api/batch-download', methods=['POST'])
@api_error_handler
def batch_download_endpoint():
    """
    API endpoint to initiate a batch download
    """
    # Rate limiting
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not RateLimiter.is_allowed(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'status': 'error'
        }), 429
    
    # Log request
    logger.info(f"Batch download request from {client_ip}")
    
    data = request.json
    
    urls = data.get('urls', [])
    format_id = data.get('format', 'best')
    download_subtitles = data.get('downloadSubtitles', False)
    max_concurrent = min(int(data.get('maxConcurrent', Config.MAX_CONCURRENT_DOWNLOADS)), 
                         Config.MAX_CONCURRENT_DOWNLOADS)
    
    if not urls or not isinstance(urls, list):
        return jsonify({
            'error': 'URLs list is required',
            'status': 'error'
        }), 400
    
    # Validate URLs
    invalid_urls = [url for url in urls if not validate_youtube_url(url)]
    if invalid_urls:
        return jsonify({
            'error': f'Found {len(invalid_urls)} invalid YouTube URLs',
            'status': 'error',
            'invalid_urls': invalid_urls
        }), 400
    
    # Check disk space
    free_space_mb = check_disk_space()
    estimated_space_needed = len(urls) * 50  # Rough estimate: 50MB per video
    if free_space_mb < estimated_space_needed:
        return jsonify({
            'error': f'Insufficient disk space for batch download. Available: {free_space_mb:.2f}MB, Estimated needed: {estimated_space_needed}MB',
            'status': 'error'
        }), 507  # Insufficient Storage
    
    # Create download entries and start downloads
    download_ids = []
    active_downloads = []
    
    for url in urls:
        # Create download entry
        download_id = DownloadManager.create_download(url, format_id)
        download_ids.append(download_id)
        
        # Start up to max_concurrent downloads immediately
        if len(active_downloads) < max_concurrent:
            download_thread = threading.Thread(
                target=download_video, 
                args=(download_id, url, format_id, download_subtitles),
                daemon=True
            )
            download_thread.start()
            active_downloads.append(download_thread)
        else:
            # Mark the rest as queued (they'll be started by the batch processor)
            logger.info(f"Queued download {download_id} for later processing")
    
    # Start a background thread to process the queue
    def batch_processor():
        """Process the batch download queue"""
        remaining_downloads = list(zip(download_ids[max_concurrent:], urls[max_concurrent:]))
        
        for download_id, url in remaining_downloads:
            # Wait for an active download to finish
            while True:
                active_downloads[:] = [t for t in active_downloads if t.is_alive()]
                if len(active_downloads) < max_concurrent:
                    break
                time.sleep(1)
            
            # Start the next download
            download_thread = threading.Thread(
                target=download_video, 
                args=(download_id, url, format_id, download_subtitles),
                daemon=True
            )
            download_thread.start()
            active_downloads.append(download_thread)
            
            # Brief pause to prevent overwhelming the system
            time.sleep(1)
    
    # Start the batch processor if there are more downloads than concurrent limit
    if len(urls) > max_concurrent:
        processor_thread = threading.Thread(target=batch_processor, daemon=True)
        processor_thread.start()
    
    return jsonify({
        'status': 'success',
        'message': f'Started batch download with {len(urls)} videos',
        'downloadIds': download_ids
    })


@app.route('/api/cancel-download', methods=['POST'])
@api_error_handler
def cancel_download_endpoint():
    """
    API endpoint to cancel a download
    """
    data = request.json
    download_id = data.get('downloadId')
    
    if not download_id:
        return jsonify({
            'error': 'Download ID is required',
            'status': 'error'
        }), 400
    
    download_info = DownloadManager.get_download(download_id)
    
    if not download_info:
        return jsonify({
            'error': 'Download not found',
            'status': 'error'
        }), 404
    
    # Update download status
    DownloadManager.update_download(download_id, status='cancelled')
    
    # If there's a file, try to remove it
    file_path = download_info.get('file_path')
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
            logger.info(f"Removed cancelled download file: {file_path}")
        except Exception as e:
            logger.error(f"Error removing file {file_path}: {e}")
    
    return jsonify({
        'status': 'success',
        'message': 'Download cancelled'
    })


@app.route('/api/status', methods=['GET'])
@api_error_handler
def api_status_endpoint():
    """
    Provide API service status information
    """
    # Get disk stats
    try:
        stats = shutil.disk_usage(Config.DOWNLOAD_DIR)
        free_space_mb = stats.free / (1024 * 1024)
        total_space_mb = stats.total / (1024 * 1024)
        used_percent = (stats.used / stats.total) * 100
    except:
        free_space_mb = 0
        total_space_mb = 0
        used_percent = 0
    
    # Collect system information
    downloads_count = len(DownloadManager._downloads)
    active_downloads = sum(1 for d in DownloadManager._downloads.values() 
                          if d['status'] in ('queued', 'downloading'))
    completed_downloads = sum(1 for d in DownloadManager._downloads.values() 
                             if d['status'] == 'completed')
    
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'downloads': {
            'total': downloads_count,
            'active': active_downloads,
            'completed': completed_downloads
        },
        'storage': {
            'free_mb': round(free_space_mb),
            'total_mb': round(total_space_mb),
            'used_percent': round(used_percent)
        },
        'configuration': {
            'max_concurrent_downloads': Config.MAX_CONCURRENT_DOWNLOADS,
            'max_video_size_mb': Config.MAX_VIDEO_SIZE_MB,
            'max_download_duration_seconds': Config.MAX_DOWNLOAD_DURATION_SECONDS
        },
        'server_time': int(time.time())
    })


# Cache control for static files
@app.after_request
def add_cache_headers(response):
    # Only add cache headers to successful responses
    if response.status_code == 200:
        # Check if the request is for a static file
        if request.path.startswith('/') and not request.path.startswith('/api/'):
            if any(request.path.endswith(ext) for ext in ['.css', '.js']):
                # Cache for 1 week
                response.headers['Cache-Control'] = 'public, max-age=604800'
            elif any(request.path.endswith(ext) for ext in ['.jpg', '.png', '.svg', '.ico']):
                # Cache for 2 weeks
                response.headers['Cache-Control'] = 'public, max-age=1209600'
            elif request.path.endswith(('.woff2', '.woff', '.ttf')):
                # Cache fonts for 1 month
                response.headers['Cache-Control'] = 'public, max-age=2592000'
    return response


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'status': 'error'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    logger.error(f"Unhandled exception: {error}")
    return jsonify({
        'error': 'Internal server error',
        'status': 'error'
    }), 500


# Start periodic cleanup thread
def start_cleanup_thread():
    """
    Start a background thread for periodic download cleanup
    """
    def run_cleanup():
        while True:
            try:
                # Clean up old downloads and files
                DownloadManager.cleanup_old_downloads(max_age_hours=24)
                cleanup_old_files(Config.DOWNLOAD_DIR, max_age_hours=24)
                
                # Check disk space and perform aggressive cleanup if needed
                check_disk_space()
                
                # Sleep for 1 hour
                time.sleep(60 * 60)
            except Exception as e:
                logger.error(f"Cleanup thread error: {e}")
                # Sleep for a shorter period if an error occurs
                time.sleep(10 * 60)
    
    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("Cleanup thread started")


# Initialize cleanup thread when the application starts
start_cleanup_thread()


if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run the Flask application
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0', 
        port=port, 
        debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    )
