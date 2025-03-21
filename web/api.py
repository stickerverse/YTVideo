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
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta

import yt_dlp
import requests
import flask
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

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
    DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/tmp/youtube_downloads')
    MAX_CONCURRENT_DOWNLOADS = int(os.environ.get('MAX_CONCURRENT_DOWNLOADS', 5))
    RATE_LIMIT_REQUESTS = int(os.environ.get('RATE_LIMIT_REQUESTS', 10))
    RATE_LIMIT_PERIOD = int(os.environ.get('RATE_LIMIT_PERIOD', 60))  # seconds
    
    # Security Settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'development_secret_key')
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
CORS(app)

# Rate Limiting and Download Tracking
class RateLimiter:
    """Simple in-memory rate limiting implementation"""
    _request_counts: Dict[str, Dict[str, Any]] = {}
    
    @classmethod
    def is_allowed(cls, ip: str) -> bool:
        """Check if the IP is allowed to make a request"""
        now = time.time()
        ip_data = cls._request_counts.get(ip, {})
        
        # Clean up old request counts
        ip_data = {
            timestamp: count 
            for timestamp, count in ip_data.items() 
            if now - timestamp < Config.RATE_LIMIT_PERIOD
        }
        
        # Count requests in the current period
        total_requests = sum(ip_data.values())
        
        # Add current request
        ip_data[now] = ip_data.get(now, 0) + 1
        cls._request_counts[ip] = ip_data
        
        return total_requests < Config.RATE_LIMIT_REQUESTS

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
        }
        
        # Add proxy if configured
        if Config.DEFAULT_PROXY:
            ydl_opts['proxy'] = Config.DEFAULT_PROXY
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Prepare file path
            filename = ydl.prepare_filename(info)
            
            # Update download with file information
            DownloadManager.update_download(
                download_id, 
                status='completed', 
                file_path=filename,
                progress=100
            )
    
    except Exception as e:
        # Handle and log download errors
        logger.error(f"Download error for {download_id}: {e}")
        DownloadManager.update_download(
            download_id, 
            status='failed', 
            error=str(e),
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
            total_bytes=total_bytes
        )

@app.route('/api/video-info', methods=['GET'])
def video_info_endpoint():
    """
    API endpoint to retrieve YouTube video information
    """
    # Rate limiting
    client_ip = request.remote_addr
    if not RateLimiter.is_allowed(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'status': 'error'
        }), 429
    
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
    
    try:
        video_data = get_video_info(url, use_proxy)
        return jsonify({
            'status': 'success',
            'data': video_data
        })
    
    except ValueError as ve:
        return jsonify({
            'error': str(ve),
            'status': 'error'
        }), 400
    except Exception as e:
        logger.error(f"Unexpected error retrieving video info: {e}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'status': 'error'
        }), 500

@app.route('/api/download', methods=['POST'])
def download_endpoint():
    """
    API endpoint to initiate a video download
    """
    # Rate limiting
    client_ip = request.remote_addr
    if not RateLimiter.is_allowed(client_ip):
        return jsonify({
            'error': 'Rate limit exceeded. Please try again later.',
            'status': 'error'
        }), 429
    
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
    
    try:
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
    
    except Exception as e:
        logger.error(f"Download initiation error: {e}")
        return jsonify({
            'error': 'Failed to start download',
            'status': 'error'
        }), 500

@app.route('/api/download-status', methods=['GET'])
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
def download_file_endpoint(download_id):
    """
    API endpoint to serve downloaded file
    
    Args:
        download_id: Unique identifier for the download
    
    Returns:
        File download or error response
    """
    try:
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
            
            # Send file with proper headers
            return send_file(
                file_path, 
                as_attachment=True, 
                download_name=sanitized_filename,
                mimetype='application/octet-stream'
            )
        except Exception as send_error:
            logger.error(f"Error sending file: {send_error}")
            return jsonify({
                'error': 'Error preparing file for download',
                'status': 'error'
            }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in file download: {e}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'status': 'error'
        }), 500

# Periodic cleanup of old downloads
def cleanup_old_downloads():
    """
    Remove old downloaded files and clean up download tracking
    """
    try:
        current_time = time.time()
        max_age = 24 * 60 * 60  # 24 hours
        
        # Cleanup downloaded files
        with DownloadManager._lock:
            for download_id, download_info in list(DownloadManager._downloads.items()):
                # Remove downloads older than 24 hours
                if current_time - download_info.get('started_at', 0) > max_age:
                    file_path = download_info.get('file_path')
                    
                    # Remove file if it exists
                    if file_path and os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            logger.info(f"Removed old download file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error removing file {file_path}: {e}")
                    
                    # Remove download tracking entry
                    del DownloadManager._downloads[download_id]
    
    except Exception as e:
        logger.error(f"Error during download cleanup: {e}")

# Start cleanup thread
def start_cleanup_thread():
    """
    Start a background thread for periodic download cleanup
    """
    def run_cleanup():
        while True:
            try:
                cleanup_old_downloads()
                # Sleep for 1 hour
                time.sleep(60 * 60)
            except Exception as e:
                logger.error(f"Cleanup thread error: {e}")
                # Sleep for a shorter period if an error occurs
                time.sleep(10 * 60)
    
    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

# API Status endpoint
@app.route('/api/status', methods=['GET'])
def api_status_endpoint():
    """
    Provide API service status information
    """
    try:
        # Collect system information
        downloads_count = len(DownloadManager._downloads)
        active_downloads = sum(1 for d in DownloadManager._downloads.values() if d['status'] == 'downloading')
        
        return jsonify({
            'status': 'ok',
            'version': '1.0.0',
            'downloads': {
                'total': downloads_count,
                'active': active_downloads
            },
            'configuration': {
                'max_concurrent_downloads': Config.MAX_CONCURRENT_DOWNLOADS,
                'max_video_size_mb': Config.MAX_VIDEO_SIZE_MB,
                'max_video_duration_seconds': Config.MAX_DOWNLOAD_DURATION_SECONDS
            },
            'server_time': int(time.time())
        })
    
    except Exception as e:
        logger.error(f"Error in API status endpoint: {e}")
        return jsonify({
            'error': 'Unable to retrieve server status',
            'status': 'error'
        }), 500

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
