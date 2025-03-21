"""
API Optimizations for 4K Video Reaper
-------------------------------------
"""

# Add these imports at the top of web/api.py
import os
import sys
import threading
import time
import uuid
import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
import traceback
import logging
from functools import wraps
import hashlib
from datetime import datetime, timedelta
import shutil

from flask import Flask, request, jsonify, send_file, render_template, abort, g, Response, make_response
from flask_cors import CORS
import yt_dlp

# Configure logging with rotation
from logging.handlers import RotatingFileHandler

# Create log directory
LOG_DIR = os.environ.get('LOG_DIR', './logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configure logger
logger = logging.getLogger('4kvideoreaper')
logger.setLevel(logging.INFO)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(console_formatter)

# File handler with rotation
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, 'app.log'),
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5
)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(file_formatter)

# Add handlers to logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Create the Flask app with configurations
app = Flask(__name__, static_folder='public', static_url_path='')
app.config['JSON_SORT_KEYS'] = False  # Preserve order in JSON responses
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # Limit request size to 10MB
CORS(app)  # Enable Cross-Origin Resource Sharing

# Configure download directory
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/tmp/downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
logger.info(f"Download directory set to {DOWNLOAD_DIR}")

# Thread pool for downloads
MAX_WORKERS = int(os.environ.get('MAX_WORKERS', '4'))
MAX_QUEUE_SIZE = int(os.environ.get('MAX_QUEUE_SIZE', '100'))

# Initialize download trackers with thread safety
downloads_lock = threading.RLock()
active_downloads = {}
download_files = {}

# In-memory cache for video info (lasts 1 hour)
video_info_cache = {}
VIDEO_INFO_CACHE_TTL = 3600  # 1 hour

# Cookie browser configuration - automatically use the browser's cookies
COOKIE_BROWSER = os.environ.get('COOKIE_BROWSER', 'firefox')  # Default to Firefox
COOKIE_BROWSER_PROFILE = os.environ.get('COOKIE_BROWSER_PROFILE', None)
COOKIE_FILE = os.environ.get('COOKIE_FILE', None)

# Middleware to log request timing
@app.before_request
def start_timer():
    g.start_time = time.time()

@app.after_request
def log_request(response):
    if not request.path.startswith('/static'):
        duration = (time.time() - g.start_time) * 1000
        logger.info(f"{request.method} {request.path} - {response.status_code} - {duration:.2f}ms")
    return response

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

# Helper function to validate YouTube URL
def is_youtube_url(url: str) -> bool:
    """Check if a URL is a valid YouTube URL."""
    yt_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    return bool(re.match(yt_regex, url))

# ----- Cache Decorator -----
def cache_response(timeout=300):
    """Cache the response of a route for a specified time period"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Generate cache key based on route and query params
            cache_key = f"{request.path}?{request.query_string.decode('utf-8')}"
            cache_key = hashlib.md5(cache_key.encode()).hexdigest()
            
            # Check if we have a cached response
            if cache_key in app.config.get('RESPONSE_CACHE', {}):
                cached_data = app.config.get('RESPONSE_CACHE')[cache_key]
                # Check if the cache is still valid
                if cached_data['expiry'] > datetime.now():
                    return cached_data['response']
            
            # If no cache or expired, call the original function
            response = f(*args, **kwargs)
            
            # Initialize cache if doesn't exist
            if 'RESPONSE_CACHE' not in app.config:
                app.config['RESPONSE_CACHE'] = {}
                
            # Store the response in cache
            app.config['RESPONSE_CACHE'][cache_key] = {
                'response': response,
                'expiry': datetime.now() + timedelta(seconds=timeout)
            }
            
            return response
        return wrapper
    return decorator

# ----- Request Limiter -----
def limit_requests(limit=100, period=60):
    """Limit the number of requests from an IP address"""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Get client IP
            ip = request.remote_addr
            
            # Initialize rate limit storage if needed
            if 'RATE_LIMITS' not in app.config:
                app.config['RATE_LIMITS'] = {}
                
            # Initialize or get the rate limit data for this IP
            if ip not in app.config['RATE_LIMITS']:
                app.config['RATE_LIMITS'][ip] = {
                    'count': 0,
                    'reset_time': time.time() + period
                }
                
            # Reset count if period has passed
            if time.time() > app.config['RATE_LIMITS'][ip]['reset_time']:
                app.config['RATE_LIMITS'][ip] = {
                    'count': 0,
                    'reset_time': time.time() + period
                }
                
            # Increment count
            app.config['RATE_LIMITS'][ip]['count'] += 1
            
            # Check if limit exceeded
            if app.config['RATE_LIMITS'][ip]['count'] > limit:
                return jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'retry_after': int(app.config['RATE_LIMITS'][ip]['reset_time'] - time.time())
                }), 429
                
            # Call the original function
            return f(*args, **kwargs)
        return wrapper
    return decorator

# Serve the main page
@app.route('/')
def index():
    return app.send_static_file('index.html')

# ----- Optimized API Status Endpoint -----
@app.route('/api/status')
@cache_response(timeout=60)  # Cache for 1 minute
def status():
    try:
        # Get yt-dlp version in an optimized way
        try:
            version_dict = yt_dlp.version.__version_info__
            ytdlp_version = f"{version_dict['version']}.{version_dict['release']}.{version_dict['micro']}"
        except (AttributeError, KeyError):
            ytdlp_version = "unknown"
        
        # Get system information
        try:
            import psutil
            system_info = {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage(DOWNLOAD_DIR).percent
            }
            
            # Check download directory
            download_stats = {
                'total_files': len(os.listdir(DOWNLOAD_DIR)),
                'free_space_gb': psutil.disk_usage(DOWNLOAD_DIR).free / (1024 * 1024 * 1024)
            }
        except ImportError:
            system_info = {'error': 'psutil not installed'}
            download_stats = {'total_files': len(os.listdir(DOWNLOAD_DIR))}
        
        data = {
            'status': 'ok',
            'version': '1.0.0',
            'ytdlp_version': ytdlp_version,
            'server_time': int(time.time()),
            'active_downloads': len(active_downloads),
            'system': system_info,
            'downloads': download_stats
        }
        return api_response(data)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return api_response(error=f"Service error: {str(e)}", status=500)

# ----- Optimized Video Info Endpoint -----
@app.route('/api/video-info')
@limit_requests(limit=30, period=60)  # Limit to 30 requests per minute
def video_info():
    url = request.args.get('url')
    use_proxy = request.args.get('proxy', 'false').lower() == 'true'
    
    if not url:
        return api_response(error='URL is required', status=400)
    
    # Validate URL is from YouTube
    if not is_youtube_url(url):
        return api_response(error='Invalid YouTube URL', status=400)
    
    # Check cache first
    cache_key = f"{url}_{use_proxy}"
    if cache_key in video_info_cache:
        cache_entry = video_info_cache[cache_key]
        if time.time() < cache_entry['expiry']:
            logger.info(f"Cache hit for video info: {url}")
            return api_response(cache_entry['data'])
    
    try:
        logger.info(f"Getting video info for: {url}")
        
        # Create a thread pool for concurrent processing
        import concurrent.futures
        
        # Function to get video info
        def get_info():
            # yt-dlp options with cookie handling
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'nocheckcertificate': True,
                'ignoreerrors': False,
            }
            
            # Add cookie handling - prefer file over browser
            if COOKIE_FILE and os.path.exists(COOKIE_FILE):
                ydl_opts['cookiefile'] = COOKIE_FILE
                logger.info(f"Using cookie file: {COOKIE_FILE}")
            elif COOKIE_BROWSER:
                ydl_opts['cookiesfrombrowser'] = (COOKIE_BROWSER, COOKIE_BROWSER_PROFILE, None, None)
                logger.info(f"Using cookies from browser: {COOKIE_BROWSER}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        
        # Use thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(get_info)
            info = future.result(timeout=30)  # 30-second timeout
            
            if not info:
                return api_response(error="Could not retrieve video information", status=404)

            # Prepare formats
            formats = []
            
            # Add standard format options
            formats.append({
                'format_id': 'best',
                'name': 'Best Quality (Video + Audio)',
                'resolution': 'Best Available',
                'ext': 'mp4'
            })
            
            formats.append({
                'format_id': 'bestaudio',
                'name': 'Best Audio Only (MP3)',
                'resolution': 'Audio only',
                'ext': 'mp3'
            })
            
            # Add specific formats if available
            if 'formats' in info:
                added_resolutions = set()
                
                for fmt in info['formats']:
                    # Skip formats with no audio or video
                    if fmt.get('acodec') == 'none' and fmt.get('vcodec') == 'none':
                        continue
                        
                    # Process video formats with height (resolution)    
                    if fmt.get('height') and fmt.get('vcodec') != 'none':
                        resolution = f"{fmt.get('height')}p"
                        
                        # Only add unique resolutions
                        if resolution not in added_resolutions and fmt.get('height') >= 360:
                            added_resolutions.add(resolution)
                            formats.append({
                                'format_id': f"bestvideo[height<={fmt.get('height')}]+bestaudio/best[height<={fmt.get('height')}]",
                                'name': f"{resolution} MP4",
                                'resolution': f"{fmt.get('width')}x{fmt.get('height')}" if fmt.get('width') else resolution,
                                'ext': 'mp4'
                            })
            
            # Create response
            data = {
                'id': info.get('id', ''),
                'title': info.get('title', ''),
                'channel': info.get('uploader', ''),
                'duration': info.get('duration', 0),
                'views': info.get('view_count', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            }
            
            # Cache the result
            video_info_cache[cache_key] = {
                'data': data,
                'expiry': time.time() + VIDEO_INFO_CACHE_TTL
            }
            
            return api_response(data)
    
    except concurrent.futures.TimeoutError:
        logger.error(f"Timeout retrieving video info for {url}")
        return api_response(error="Request timed out while fetching video information", status=504)
    
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        logger.error(f"yt-dlp download error: {error_msg}")
        return api_response(error=f"Error fetching video info: {error_msg}", status=400)
    
    except Exception as e:
        logger.error(f"Error getting video info: {str(e)}\n{traceback.format_exc()}")
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Start a download
@app.route('/api/download', methods=['POST'])
def download():
    try:
        data = request.json
        
        url = data.get('url')
        format_id = data.get('formatId')
        download_subtitles = data.get('downloadSubtitles', False)
        
        if not url:
            return api_response(error='URL is required', status=400)
        
        if not is_youtube_url(url):
            return api_response(error='Invalid YouTube URL', status=400)
        
        if not format_id:
            format_id = 'best'  # Default format
        
        # Generate a unique download ID
        download_id = str(uuid.uuid4())
        
        # Initialize download tracking with thread safety
        with downloads_lock:
            active_downloads[download_id] = {
                'id': download_id,
                'url': url,
                'status': 'queued',
                'progress': 0.0,
                'started_at': time.time(),
                'title': '',
                'error': None
            }
        
        # Start the download in a separate thread
        thread = threading.Thread(
            target=do_download,
            args=(download_id, url, format_id, download_subtitles)
        )
        thread.daemon = True
        thread.start()
        
        # Return the download ID
        return api_response({'downloadId': download_id})
    
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}\n{traceback.format_exc()}")
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Get download status
@app.route('/api/download-status')
def download_status():
    download_id = request.args.get('id')
    
    if not download_id:
        return api_response(error='Download ID is required', status=400)
    
    # Check if download is in active downloads
    with downloads_lock:
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
def cancel_download():
    try:
        data = request.json
        download_id = data.get('downloadId')
        
        if not download_id:
            return api_response(error='Download ID is required', status=400)
        
        # Check if download is in active downloads
        with downloads_lock:
            if download_id in active_downloads:
                active_downloads[download_id]['status'] = 'cancelled'
                logger.info(f"Cancelled download: {download_id}")
                return api_response({'success': True})
        
        return api_response(error='Download not found', status=404)
    
    except Exception as e:
        logger.error(f"Error cancelling download: {str(e)}")
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Start a batch download
@app.route('/api/batch-download', methods=['POST'])
def batch_download():
    try:
        data = request.json
        
        urls = data.get('urls', [])
        format_str = data.get('format', 'best')
        download_subtitles = data.get('downloadSubtitles', False)
        
        if not urls or not isinstance(urls, list) or len(urls) == 0:
            return api_response(error='URLs are required', status=400)
        
        # Validate URLs
        valid_urls = []
        invalid_urls = []
        
        for url in urls:
            if is_youtube_url(url):
                valid_urls.append(url)
            else:
                invalid_urls.append(url)
        
        if not valid_urls:
            return api_response(error='No valid YouTube URLs provided', status=400)
        
        # Add URLs to batch download
        download_ids = []
        for url in valid_urls:
            # Generate a unique download ID
            download_id = str(uuid.uuid4())
            
            # Initialize download tracking with thread safety
            with downloads_lock:
                active_downloads[download_id] = {
                    'id': download_id,
                    'url': url,
                    'status': 'queued',
                    'progress': 0.0,
                    'started_at': time.time(),
                    'title': '',
                    'error': None
                }
            
            # Start the download in a separate thread
            thread = threading.Thread(
                target=do_download,
                args=(download_id, url, format_str, download_subtitles)
            )
            thread.daemon = True
            thread.start()
            
            download_ids.append(download_id)
        
        logger.info(f"Started batch download with {len(valid_urls)} URLs")
        
        return api_response({
            'downloadIds': download_ids,
            'invalidUrls': invalid_urls,
            'message': f"Started {len(valid_urls)} downloads. {len(invalid_urls)} URLs were invalid."
        })
    
    except Exception as e:
        logger.error(f"Error with batch download: {str(e)}\n{traceback.format_exc()}")
        return api_response(error=f"Error processing request: {str(e)}", status=500)

# Download a file
@app.route('/api/download-file/<download_id>')
def download_file(download_id):
    try:
        # Check if the file exists in download files
        with downloads_lock:
            if download_id in download_files and os.path.exists(download_files[download_id]):
                filename = os.path.basename(download_files[download_id])
                logger.info(f"Serving file: {filename} for download ID: {download_id}")
                return send_file(
                    download_files[download_id],
                    as_attachment=True,
                    download_name=filename,
                    mimetype='application/octet-stream'
                )
        
        # File not found
        return api_response(error='File not found', status=404)
    
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        return api_response(error=f"Error serving file: {str(e)}", status=500)

# Error handling
@app.errorhandler(404)
def not_found(error):
    return api_response(error='Resource not found', status=404)

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {str(error)}")
    return api_response(error='Internal server error', status=500)

# ----- Optimized Download Function -----
def do_download(download_id, url, format_id, download_subtitles):
    try:
        # Update tracking data with thread safety
        with downloads_lock:
            active_downloads[download_id]['status'] = 'downloading'
        
        # Get output file path
        sanitized_name = f"download_{download_id}"
        output_path = os.path.join(DOWNLOAD_DIR, sanitized_name)
        
        # Progress callback function
        def progress_hook(d):
            if d['status'] == 'downloading':
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                if total_bytes > 0:
                    progress = (downloaded_bytes / total_bytes) * 100
                else:
                    progress = 0
                
                # Update tracking data only for significant changes (reduces lock contention)
                with downloads_lock:
                    if download_id in active_downloads:
                        current_progress = active_downloads[download_id].get('progress', 0)
                        if abs(progress - current_progress) >= 0.5 or progress == 100:
                            active_downloads[download_id].update({
                                'progress': progress,
                                'speed': d.get('speed', 0),
                                'eta': d.get('eta', 0),
                                'title': d.get('info_dict', {}).get('title', active_downloads[download_id].get('title', ''))
                            })
            
            elif d['status'] == 'finished':
                # Set progress to 100% when finished
                with downloads_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]['progress'] = 100.0
        
        # Optimize yt-dlp options, including cookie support
        ydl_opts = {
            'format': format_id,
            'outtmpl': f"{output_path}.%(ext)s",
            'progress_hooks': [progress_hook],
            'noplaylist': True,  # Only download the video, not the playlist
            'nocheckcertificate': True,
            'ignoreerrors': False,
            # Performance options
            'concurrent_fragment_downloads': 5,  # Download fragments in parallel
        }
        
        # Add cookie handling - prefer file over browser
        if COOKIE_FILE and os.path.exists(COOKIE_FILE):
            ydl_opts['cookiefile'] = COOKIE_FILE
            logger.info(f"Using cookie file for download: {COOKIE_FILE}")
        elif COOKIE_BROWSER:
            ydl_opts['cookiesfrombrowser'] = (COOKIE_BROWSER, COOKIE_BROWSER_PROFILE, None, None)
            logger.info(f"Using cookies from browser for download: {COOKIE_BROWSER}")
        
        # Use aria2c if available
        if shutil.which('aria2c'):
            ydl_opts.update({
                'external_downloader': 'aria2c',
                'external_downloader_args': ['--max-concurrent-downloads=5', '--max-connection-per-server=5', '--split=5'],
            })
        
        # Add subtitle options if requested
        if download_subtitles:
            ydl_opts.update({
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['en'],  # Default to English
            })
        
        # Handle audio-only format
        if format_id == 'bestaudio':
            ydl_opts.update({
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        # Download with yt-dlp in a try-except block with timeout protection
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info first to get title
                info = ydl.extract_info(url, download=False)
                
                if info:
                    # Update title with thread safety
                    with downloads_lock:
                        if download_id in active_downloads:
                            active_downloads[download_id]['title'] = info.get('title', '')
                    
                    # Download the video
                    ydl.download([url])
                    
                    # Find the output file
                    output_file = None
                    
                    # Get the extension
                    ext = 'mp3' if format_id == 'bestaudio' else info.get('ext', 'mp4')
                    potential_file = f"{output_path}.{ext}"
                    
                    if os.path.exists(potential_file):
                        output_file = potential_file
                    else:
                        # Search for any file with the output_path prefix
                        for file in os.listdir(DOWNLOAD_DIR):
                            if file.startswith(os.path.basename(output_path)):
                                output_file = os.path.join(DOWNLOAD_DIR, file)
                                break
                    
                    if output_file and os.path.exists(output_file):
                        # Update tracking data with thread safety
                        with downloads_lock:
                            if download_id in active_downloads:
                                active_downloads[download_id].update({
                                    'status': 'completed',
                                    'progress': 100.0,
                                })
                            download_files[download_id] = output_file
                        
                        logger.info(f"Download completed for ID: {download_id}, file: {output_file}")
                    else:
                        # Handle case where file wasn't found
                        with downloads_lock:
                            if download_id in active_downloads:
                                active_downloads[download_id].update({
                                    'status': 'failed',
                                    'error': 'Output file not found'
                                })
                        logger.error(f"Output file not found for download ID: {download_id}")
                else:
                    # Handle case where info couldn't be retrieved
                    with downloads_lock:
                        if download_id in active_downloads:
                            active_downloads[download_id].update({
                                'status': 'failed',
                                'error': 'Could not retrieve video information'
                            })
                    logger.error(f"Could not retrieve video info for download ID: {download_id}")
        except Exception as e:
            # Update tracking data with error and thread safety
            with downloads_lock:
                if download_id in active_downloads:
                    active_downloads[download_id].update({
                        'status': 'failed',
                        'error': str(e)
                    })
            logger.error(f"Download error for ID: {download_id}: {str(e)}")
            raise
    
    except Exception as e:
        # Update tracking data with error and thread safety
        with downloads_lock:
            if download_id in active_downloads:
                active_downloads[download_id].update({
                    'status': 'failed',
                    'error': str(e)
                })
        
        logger.error(f"Download error for ID: {download_id}: {str(e)}\n{traceback.format_exc()}")

# Add a cleanup task that runs periodically
def cleanup_old_downloads():
    """Cleanup downloads older than 24 hours"""
    logger.info("Running cleanup task...")
    current_time = time.time()
    max_age = 24 * 60 * 60  # 24 hours
    
    # Clean up download files
    try:
        for filename in os.listdir(DOWNLOAD_DIR):
            file_path = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.isfile(file_path):
                file_stat = os.stat(file_path)
                file_age = current_time - file_stat.st_mtime
                
                if file_age > max_age:
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted old file: {filename}")
                    except Exception as e:
                        logger.error(f"Error deleting {filename}: {e}")
    except Exception as e:
        logger.error(f"Error during file cleanup: {e}")
    
    # Clean up download tracking data with thread safety
    with downloads_lock:
        for download_id in list(active_downloads.keys()):
            download = active_downloads[download_id]
            if 'started_at' in download:
                age = current_time - download['started_at']
                if age > max_age:
                    try:
                        del active_downloads[download_id]
                        if download_id in download_files:
                            del download_files[download_id]
                        logger.info(f"Cleaned up tracking data for download ID: {download_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up tracking data for {download_id}: {e}")

# Start cleanup thread
def start_cleanup_thread():
    def run_cleanup():
        while True:
            try:
                cleanup_old_downloads()
            except Exception as e:
                logger.error(f"Error in cleanup thread: {e}")
            
            # Sleep for 1 hour before next cleanup
            time.sleep(60 * 60)
    
    cleanup_thread = threading.Thread(target=run_cleanup, daemon=True)
    cleanup_thread.start()

# Use Flask's before_serving hook for Flask 2.0+ compatibility
# If using older Flask versions, uncomment the @app.before_first_request approach
def initialize_app():
    start_cleanup_thread()

# Modern approach for Flask initialization
with app.app_context():
    initialize_app()

# Run the application
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting 4K Video Reaper API on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
