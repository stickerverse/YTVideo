import os
import threading
import time
import uuid
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import traceback

from flask import Flask, request, jsonify, send_file, render_template, abort, g, Response
from flask_cors import CORS
import yt_dlp
from functools import wraps

# Add the parent directory to the Python path to import the YouTube downloader modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules from your YouTube downloader
from youtube_downloader.config import config
from youtube_downloader.downloaders import YtdlpDownloader, Aria2Downloader
from youtube_downloader.services import ProxyManager, CaptchaSolver, BatchManager
from youtube_downloader.utils import ensure_dir, is_youtube_url
from youtube_downloader.utils.security import SecurityMiddleware, rate_limit, validate_youtube_url, sanitize_filename
from youtube_downloader.utils.logger import (
    app_logger, download_logger, api_logger, 
    log_exception, log_download_start, log_download_complete, log_download_error,
    log_api_request
)

# Initialize Flask app
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # Enable Cross-Origin Resource Sharing

# Apply security middleware
SecurityMiddleware(app)

# Configure download directory
DOWNLOAD_DIR = config.get('download_dir', os.path.join(tempfile.gettempdir(), 'youtube_downloads'))
ensure_dir(DOWNLOAD_DIR)

# Initialize download trackers
active_downloads = {}
download_files = {}

# Initialize services
try:
    proxy_manager = ProxyManager()
    app_logger.info("Proxy manager initialized")
except Exception as e:
    app_logger.error(f"Failed to initialize proxy manager: {str(e)}")
    proxy_manager = None

try:
    captcha_solver = CaptchaSolver()
    app_logger.info("CAPTCHA solver initialized")
except Exception as e:
    app_logger.error(f"Failed to initialize CAPTCHA solver: {str(e)}")
    captcha_solver = None

try:
    batch_manager = BatchManager(
        download_dir=DOWNLOAD_DIR,
        proxy_manager=proxy_manager
    )
    app_logger.info("Batch manager initialized")
except Exception as e:
    app_logger.error(f"Failed to initialize batch manager: {str(e)}")
    batch_manager = None

# Initialize downloaders
ytdlp_downloader = YtdlpDownloader(download_dir=DOWNLOAD_DIR)
aria2_downloader = None
try:
    aria2_downloader = Aria2Downloader(download_dir=DOWNLOAD_DIR)
    app_logger.info("Aria2 downloader initialized")
except RuntimeError as e:
    app_logger.warning(f"Aria2 is not installed or not found. Multi-threaded downloads will not be available: {str(e)}")

# Middleware to log request timing
@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request(response):
    if not request.path.startswith('/static'):
        duration = (time.time() - g.start_time) * 1000
        log_api_request(
            endpoint=request.path,
            method=request.method,
            ip=request.remote_addr,
            status_code=response.status_code,
            duration_ms=duration
        )
    return response

# Error handling
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def server_error(error):
    app_logger.error(f"Server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def too_many_requests(error):
    return jsonify({'error': 'Too many requests, please try again later'}), 429

# Helper function for API responses
def api_response(data: Any = None, error: Optional[str] = None, status: int = 200) -> Response:
    """Create a standardized API response"""
    response = {
        'success': error is None,
        'timestamp': int(time.time())
    }
    
    if data is not None:
        response['data'] = data
    
    if error:
        response['error'] = error
    
    return jsonify(response), status

# Serve the main page
@app.route('/')
def index():
    return app.send_static_file('index.html')

# API status endpoint
@app.route('/api/status')
@rate_limit(60, 60)  # 60 requests per minute
def status():
    data = {
        'status': 'ok',
        'version': '1.0.0',
        'aria2_available': aria2_downloader is not None,
        'server_time': int(time.time()),
        'features': {
            'proxy_support': proxy_manager is not None,
            'captcha_solver': captcha_solver is not None and captcha_solver.api_key is not None,
            'batch_download': batch_manager is not None
        }
    }
    return api_response(data)

# Get video information
@app.route('/api/video-info')
@rate_limit(20, 60)  # 20 requests per minute
def video_info():
    url = request.args.get('url')
    use_proxy = request.args.get('proxy', 'false').lower() == 'true'
    
    if not url:
        return api_response(error='URL is required', status=400)
    
    if not validate_youtube_url(url):
        return api_response(error='Invalid YouTube URL', status=400)
    
    try:
        # Get proxy if needed
        proxy = None
        if use_proxy and proxy_manager:
            proxy = proxy_manager.get_proxy()
        
        app_logger.info(f"Getting video info for: {url}")
        
        # Get video info
        info = ytdlp_downloader.get_info(url, proxy=proxy)
        
        # Extract relevant information
        formats = []
        
        # Process available formats
        if 'formats' in info:
            for fmt in info.get('formats', []):
                if fmt.get('acodec') != 'none' or fmt.get('vcodec') != 'none':  # Skip formats with no audio or video
                    format_id = fmt.get('format_id')
                    ext = fmt.get('ext', '')
                    resolution = ''
                    
                    if fmt.get('height'):
                        resolution = f"{fmt.get('width', '')}x{fmt.get('height', '')}"
                    
                    quality = fmt.get('format_note', '')
                    if not quality and fmt.get('height'):
                        quality = f"{fmt.get('height')}p"
                    
                    # Estimate file size if available
                    size = fmt.get('filesize') or fmt.get('filesize_approx')
                    
                    # Create a readable name
                    if fmt.get('vcodec') == 'none':
                        name = f"Audio {quality} ({ext.upper()})"
                    else:
                        name = f"Video {quality} ({ext.upper()})"
                    
                    formats.append({
                        'format_id': format_id,
                        'format': fmt.get('format', ''),
                        'ext': ext,
                        'resolution': resolution,
                        'quality': quality,
                        'size': size,
                        'name': name
                    })
            
            # Add some standard format combinations
            formats.append({
                'format_id': 'best',
                'name': 'Best Quality (Video + Audio)',
                'resolution': 'Best',
                'quality': 'Best',
                'ext': 'mp4'
            })
            
            formats.append({
                'format_id': 'bestaudio',
                'name': 'Best Audio Only (MP3)',
                'resolution': 'Audio only',
                'quality': 'Best audio',
                'ext': 'mp3'
            })
        
        data = {
            'id': info.get('id', ''),
            'title': info.get('title', ''),
            'channel': info.get('uploader', ''),
            'duration': info.get('duration', 0),
            'views': info.get('view_count', 0),
            'thumbnail': info.get('thumbnail', ''),
            'formats': formats
        }
        
        return api_response(data)
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        app_logger.error(f"yt-dlp download error: {error_msg}")
        return api_response(error=f"Error fetching video info: {error_msg}", status=400)
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Start a download
@app.route('/api/download', methods=['POST'])
@rate_limit(10, 60)  # 10 requests per minute
def download():
    try:
        data = request.json
        
        url = data.get('url')
        format_id = data.get('formatId')
        use_aria2 = data.get('useAria2', True)
        use_proxy = data.get('useProxy', False)
        download_subtitles = data.get('downloadSubtitles', False)
        
        if not url:
            return api_response(error='URL is required', status=400)
        
        if not validate_youtube_url(url):
            return api_response(error='Invalid YouTube URL', status=400)
        
        if not format_id:
            return api_response(error='Format ID is required', status=400)
        
        # Generate a unique download ID
        download_id = str(uuid.uuid4())
        
        # Get proxy if needed
        proxy = None
        if use_proxy and proxy_manager:
            proxy = proxy_manager.get_proxy()
        
        # Log download start
        log_download_start(url, download_id, format_id)
        
        # Start the download in a separate thread
        thread = threading.Thread(
            target=do_download,
            args=(download_id, url, format_id, use_aria2, proxy, download_subtitles)
        )
        thread.daemon = True
        thread.start()
        
        # Return the download ID
        return api_response({'downloadId': download_id})
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Get download status
@app.route('/api/download-status')
@rate_limit(60, 60)  # 60 requests per minute
def download_status():
    download_id = request.args.get('id')
    
    if not download_id:
        return api_response(error='Download ID is required', status=400)
    
    # Check if download is in batch manager
    batch_download = batch_manager.get_download(download_id) if batch_manager else None
    if batch_download:
        data = {
            'status': batch_download['status'],
            'progress': batch_download['progress'],
            'title': batch_download.get('title', ''),
            'error': batch_download.get('error', None),
            'fileUrl': f'/api/download-file/{download_id}' if batch_download['status'] == 'completed' else None
        }
        return api_response(data)
    
    # Check if download is in active downloads
    if download_id in active_downloads:
        download_data = active_downloads[download_id]
        data = {
            'status': download_data.get('status', 'unknown'),
            'progress': download_data.get('progress', 0),
            'speed': download_data.get('speed', 0),
            'eta': download_data.get('eta', 0),
            'title': download_data.get('title', ''),
            'error': download_data.get('error', None),
            'fileUrl': f'/api/download-file/{download_id}' if download_data.get('status') == 'completed' else None
        }
        return api_response(data)
    
    return api_response(error='Download not found', status=404)

# Cancel a download
@app.route('/api/cancel-download', methods=['POST'])
@rate_limit(20, 60)  # 20 requests per minute
def cancel_download():
    try:
        data = request.json
        download_id = data.get('downloadId')
        
        if not download_id:
            return api_response(error='Download ID is required', status=400)
        
        # Check if download is in batch manager
        if batch_manager and batch_manager.cancel_download(download_id):
            app_logger.info(f"Cancelled batch download: {download_id}")
            return api_response({'success': True})
        
        # Check if download is in active downloads
        if download_id in active_downloads:
            active_downloads[download_id]['status'] = 'cancelled'
            app_logger.info(f"Cancelled download: {download_id}")
            return api_response({'success': True})
        
        return api_response(error='Download not found', status=404)
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Start a batch download
@app.route('/api/batch-download', methods=['POST'])
@rate_limit(5, 60)  # 5 requests per minute
def batch_download():
    try:
        data = request.json
        
        urls = data.get('urls', [])
        format_str = data.get('format', 'best')
        max_concurrent = data.get('maxConcurrent', 3)
        use_aria2 = data.get('useAria2', True)
        use_proxy = data.get('useProxy', False)
        download_subtitles = data.get('downloadSubtitles', False)
        
        if not urls or not isinstance(urls, list) or len(urls) == 0:
            return api_response(error='URLs are required', status=400)
        
        # Validate URLs
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            if validate_youtube_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if not valid_urls:
            return api_response(error='No valid YouTube URLs provided', status=400)
        
        # Check if batch manager is available
        if not batch_manager:
            return api_response(error='Batch downloading is not available', status=503)
        
        # Get proxy if needed
        proxy = None
        if use_proxy and proxy_manager:
            proxy = proxy_manager.get_proxy()
        
        # Add URLs to batch manager
        download_ids = batch_manager.add_urls(
            urls=valid_urls,
            use_aria2=use_aria2 and aria2_downloader is not None,
            format_str=format_str,
            proxy=proxy,
            subtitles=download_subtitles
        )
        
        app_logger.info(f"Started batch download with {len(valid_urls)} URLs")
        
        return api_response({
            'downloadIds': download_ids,
            'invalidUrls': invalid_urls,
            'message': f"Started {len(valid_urls)} downloads. {len(invalid_urls)} URLs were invalid."
        })
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Download a file
@app.route('/api/download-file/<download_id>')
def download_file(download_id):
    try:
        # Check if the file exists in download files
        if download_id in download_files and os.path.exists(download_files[download_id]):
            filename = os.path.basename(download_files[download_id])
            app_logger.info(f"Serving file: {filename} for download ID: {download_id}")
            return send_file(
                download_files[download_id],
                as_attachment=True,
                download_name=filename,
                mimetype='application/octet-stream'
            )
        
        # Check if the file exists in batch manager
        if batch_manager:
            batch_download = batch_manager.get_download(download_id)
            if batch_download and batch_download['status'] == 'completed' and batch_download.get('output_file'):
                if os.path.exists(batch_download['output_file']):
                    filename = os.path.basename(batch_download['output_file'])
                    app_logger.info(f"Serving file: {filename} for batch download ID: {download_id}")
                    return send_file(
                        batch_download['output_file'],
                        as_attachment=True,
                        download_name=filename,
                        mimetype='application/octet-stream'
                    )
        
        # File not found
        return api_response(error='File not found', status=404)
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error serving file: {str(e)}", status=500)

# System information for authenticated admin users
@app.route('/api/admin/system-info')
@rate_limit(10, 60)  # 10 requests per minute
def system_info():
    # In a real app, add authentication for admin endpoints
    # Here for demo/development purposes only
    
    import platform
    import psutil
    
    try:
        # Get system information
        system_data = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available,
            'disk_total': psutil.disk_usage('/').total,
            'disk_free': psutil.disk_usage('/').free,
            'aria2_available': aria2_downloader is not None,
            'aria2_version': os.popen('aria2c --version').read().strip() if aria2_downloader else None,
            'active_downloads': len(active_downloads),
            'batch_downloads': len(batch_manager.get_all_downloads()) if batch_manager else 0
        }
        
        return api_response(system_data)
    
    except Exception as e:
        log_exception(e)
        return api_response(error=f"Error fetching system information: {str(e)}", status=500)

# Perform the actual download
def do_download(download_id, url, format_id, use_aria2, proxy, download_subtitles):
    try:
        # Initialize tracking data
        active_downloads[download_id] = {
            'status': 'downloading',
            'progress': 0,
            'speed': 0,
            'eta': 0,
            'title': '',
            'error': None
        }
        
        # Progress callback function
        def progress_callback(url, downloaded_bytes, total_bytes):
            if total_bytes > 0:
                progress = (downloaded_bytes / total_bytes) * 100
            else:
                progress = 0
            
            # Calculate speed (compare with last update)
            current_time = time.time()
            last_time = active_downloads[download_id].get('last_time', current_time)
            last_bytes = active_downloads[download_id].get('last_bytes', 0)
            
            time_diff = current_time - last_time
            if time_diff > 0:
                speed = (downloaded_bytes - last_bytes) / time_diff
                eta = (total_bytes - downloaded_bytes) / speed if speed > 0 else 0
            else:
                speed = 0
                eta = 0
            
            # Update tracking data
            active_downloads[download_id].update({
                'progress': progress,
                'speed': speed,
                'eta': eta,
                'last_time': current_time,
                'last_bytes': downloaded_bytes
            })
        
        # Get video info first to get title
        app_logger.info(f"Getting video info for download ID: {download_id}, URL: {url}")
        info = ytdlp_downloader.get_info(url, proxy=proxy)
        active_downloads[download_id]['title'] = info.get('title', '')
        
        # Determine which downloader to use
        output_file = None
        
        if format_id.startswith('bestaudio') or format_id.endswith('mp3'):
            # Audio-only download with yt-dlp
            app_logger.info(f"Starting audio download for ID: {download_id}, URL: {url}")
            output_file = ytdlp_downloader.download(
                url=url,
                format_str='bestaudio/best',
                proxy=proxy,
                subtitles=download_subtitles,
                on_progress=progress_callback
            )
        elif use_aria2 and aria2_downloader is not None and format_id.startswith('http'):
            # Direct URL download with Aria2
            app_logger.info(f"Starting direct URL download with Aria2 for ID: {download_id}")
            output_file = aria2_downloader.download(
                url=format_id,  # Direct URL to the format
                proxy=proxy,
                on_progress=progress_callback
            )
        else:
            # Video download with yt-dlp
            app_logger.info(f"Starting video download with yt-dlp for ID: {download_id}, format: {format_id}")
            output_file = ytdlp_downloader.download(
                url=url,
                format_str=format_id,
                proxy=proxy,
                subtitles=download_subtitles,
                on_progress=progress_callback
            )
        
        # Update tracking data
        active_downloads[download_id].update({
            'status': 'completed',
            'progress': 100,
            'output_file': output_file
        })
        
        # Store the output file for download
        download_files[download_id] = output_file
        
        # Log download completion
        log_download_complete(url, download_id, output_file)
        app_logger.info(f"Download completed for ID: {download_id}, file: {output_file}")
    
    except Exception as e:
        # Update tracking data with error
        active_downloads[download_id].update({
            'status': 'failed',
            'error': str(e)
        })
        
        # Log download error
        log_download_error(url, download_id, str(e))
        app_logger.error(f"Download error for ID: {download_id}: {str(e)}")
        log_exception(e)

# Main entry point
if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='4K Video Reaper Web API')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    # Start the Flask app
    app_logger.info(f"Starting 4K Video Reaper Web API on {args.host}:{args.port}")
    app.run(debug=args.debug, host=args.host, port=args.port)
