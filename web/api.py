import os
import sys
import threading
import time
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import traceback
import logging

from flask import Flask, request, jsonify, send_file, render_template, abort, g, Response
from flask_cors import CORS
import yt_dlp

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('4kvideoreaper')

# Create the Flask app
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # Enable Cross-Origin Resource Sharing

# Configure download directory
DOWNLOAD_DIR = os.environ.get('DOWNLOAD_DIR', '/tmp/downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
logger.info(f"Download directory set to {DOWNLOAD_DIR}")

# Initialize download trackers
active_downloads = {}
download_files = {}

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

# Serve the main page
@app.route('/')
def index():
    return app.send_static_file('index.html')

# API status endpoint
@app.route('/api/status')
def status():
    try:
        # Check if yt-dlp is working
        version_dict = yt_dlp.version.__version_info__
        ytdlp_version = f"{version_dict['version']}.{version_dict['release']}.{version_dict['micro']}"
        
        data = {
            'status': 'ok',
            'version': '1.0.0',
            'ytdlp_version': ytdlp_version,
            'server_time': int(time.time()),
            'active_downloads': len(active_downloads),
            'download_dir': DOWNLOAD_DIR
        }
        return api_response(data)
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return api_response(error=f"Service error: {str(e)}", status=500)

# Get video information
@app.route('/api/video-info')
def video_info():
    url = request.args.get('url')
    use_proxy = request.args.get('proxy', 'false').lower() == 'true'
    
    if not url:
        return api_response(error='URL is required', status=400)
    
    # Validate URL is from YouTube
    if not is_youtube_url(url):
        return api_response(error='Invalid YouTube URL', status=400)
    
    try:
        logger.info(f"Getting video info for: {url}")
        
        # yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # Don't download the video
            'nocheckcertificate': True,
            'ignoreerrors': False,
        }
        
        # Get video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
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
            
            return api_response(data)
    
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
        
        # Initialize download tracking
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
            
            # Initialize download tracking
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

# Perform the actual download
def do_download(download_id, url, format_id, download_subtitles):
    try:
        # Update tracking data
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
                
                # Update tracking data
                if download_id in active_downloads:
                    active_downloads[download_id].update({
                        'progress': progress,
                        'speed': d.get('speed', 0),
                        'eta': d.get('eta', 0),
                        'title': d.get('info_dict', {}).get('title', active_downloads[download_id].get('title', ''))
                    })
            
            elif d['status'] == 'finished':
                # Set progress to 100% when finished
                if download_id in active_downloads:
                    active_downloads[download_id]['progress'] = 100.0
        
        # yt-dlp options
        ydl_opts = {
            'format': format_id,
            'outtmpl': f"{output_path}.%(ext)s",
            'progress_hooks': [progress_hook],
            'noplaylist': True,  # Only download the video, not the playlist
            'nocheckcertificate': True,
            'ignoreerrors': False,
        }
        
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
        
        # Download with yt-dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first to get title
            info = ydl.extract_info(url, download=False)
            
            if info:
                # Update title
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
                    # Update tracking data
                    active_downloads[download_id].update({
                        'status': 'completed',
                        'progress': 100.0,
                    })
                    
                    # Store the output file for download
                    download_files[download_id] = output_file
                    
                    logger.info(f"Download completed for ID: {download_id}, file: {output_file}")
                else:
                    # Handle case where file wasn't found
                    active_downloads[download_id].update({
                        'status': 'failed',
                        'error': 'Output file not found'
                    })
                    logger.error(f"Output file not found for download ID: {download_id}")
            else:
                # Handle case where info couldn't be retrieved
                active_downloads[download_id].update({
                    'status': 'failed',
                    'error': 'Could not retrieve video information'
                })
                logger.error(f"Could not retrieve video info for download ID: {download_id}")
    
    except Exception as e:
        # Update tracking data with error
        if download_id in active_downloads:
            active_downloads[download_id].update({
                'status': 'failed',
                'error': str(e)
            })
        
        logger.error(f"Download error for ID: {download_id}: {str(e)}\n{traceback.format_exc()}")

# Helper function to validate YouTube URL
def is_youtube_url(url: str) -> bool:
    """Check if a URL is a valid YouTube URL."""
    import re
    yt_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    return bool(re.match(yt_regex, url))

# Run the application
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting 4K Video Reaper API on port {port}")
    app.run(debug=True, host='0.0.0.0', port=port)
