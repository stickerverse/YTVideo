from flask import Flask, request, jsonify, send_file, render_template, abort
from flask_cors import CORS
import os
import threading
import time
import uuid
import json
import sys
import tempfile
from pathlib import Path

# Add the parent directory to the Python path to import the YouTube downloader modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import modules from your YouTube downloader
from youtube_downloader.config import config
from youtube_downloader.downloaders import YtdlpDownloader, Aria2Downloader
from youtube_downloader.services import ProxyManager, CaptchaSolver, BatchManager
from youtube_downloader.utils import ensure_dir, is_youtube_url

# Initialize Flask app
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)  # Enable Cross-Origin Resource Sharing

# Initialize download trackers
active_downloads = {}
download_files = {}

# Configure download directory
DOWNLOAD_DIR = config.get('download_dir', os.path.join(tempfile.gettempdir(), 'youtube_downloads'))
ensure_dir(DOWNLOAD_DIR)

# Initialize services
proxy_manager = ProxyManager()
captcha_solver = CaptchaSolver()
batch_manager = BatchManager(
    download_dir=DOWNLOAD_DIR,
    proxy_manager=proxy_manager
)

# Initialize downloaders
ytdlp_downloader = YtdlpDownloader(download_dir=DOWNLOAD_DIR)
aria2_downloader = None
try:
    aria2_downloader = Aria2Downloader(download_dir=DOWNLOAD_DIR)
except RuntimeError:
    print("Aria2 is not installed or not found. Multi-threaded downloads will not be available.")


# Serve the main page
@app.route('/')
def index():
    return app.send_static_file('index.html')


# API status endpoint
@app.route('/api/status')
def status():
    return jsonify({
        'status': 'ok',
        'version': '1.0.0',
        'aria2_available': aria2_downloader is not None
    })


# Get video information
@app.route('/api/video-info')
def video_info():
    url = request.args.get('url')
    use_proxy = request.args.get('proxy', 'false').lower() == 'true'
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    if not is_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    try:
        # Get proxy if needed
        proxy = None
        if use_proxy and proxy_manager:
            proxy = proxy_manager.get_proxy()
        
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
        
        return jsonify({
            'id': info.get('id', ''),
            'title': info.get('title', ''),
            'channel': info.get('uploader', ''),
            'duration': info.get('duration', 0),
            'views': info.get('view_count', 0),
            'thumbnail': info.get('thumbnail', ''),
            'formats': formats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Start a download
@app.route('/api/download', methods=['POST'])
def download():
    data = request.json
    
    url = data.get('url')
    format_id = data.get('formatId')
    use_aria2 = data.get('useAria2', True)
    use_proxy = data.get('useProxy', False)
    download_subtitles = data.get('downloadSubtitles', False)
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    if not is_youtube_url(url):
        return jsonify({'error': 'Invalid YouTube URL'}), 400
    
    if not format_id:
        return jsonify({'error': 'Format ID is required'}), 400
    
    # Generate a unique download ID
    download_id = str(uuid.uuid4())
    
    # Get proxy if needed
    proxy = None
    if use_proxy and proxy_manager:
        proxy = proxy_manager.get_proxy()
    
    # Start the download in a separate thread
    thread = threading.Thread(
        target=do_download,
        args=(download_id, url, format_id, use_aria2, proxy, download_subtitles)
    )
    thread.daemon = True
    thread.start()
    
    # Return the download ID
    return jsonify({'downloadId': download_id})


# Get download status
@app.route('/api/download-status')
def download_status():
    download_id = request.args.get('id')
    
    if not download_id:
        return jsonify({'error': 'Download ID is required'}), 400
    
    # Check if download is in batch manager
    batch_download = batch_manager.get_download(download_id)
    if batch_download:
        return jsonify({
            'status': batch_download['status'],
            'progress': batch_download['progress'],
            'title': batch_download.get('title', ''),
            'error': batch_download.get('error', None),
            'fileUrl': f'/api/download-file/{download_id}' if batch_download['status'] == 'completed' else None
        })
    
    # Check if download is in active downloads
    if download_id in active_downloads:
        download_data = active_downloads[download_id]
        return jsonify({
            'status': download_data.get('status', 'unknown'),
            'progress': download_data.get('progress', 0),
            'speed': download_data.get('speed', 0),
            'eta': download_data.get('eta', 0),
            'title': download_data.get('title', ''),
            'error': download_data.get('error', None),
            'fileUrl': f'/api/download-file/{download_id}' if download_data.get('status') == 'completed' else None
        })
    
    return jsonify({'error': 'Download not found'}), 404


# Cancel a download
@app.route('/api/cancel-download', methods=['POST'])
def cancel_download():
    data = request.json
    download_id = data.get('downloadId')
    
    if not download_id:
        return jsonify({'error': 'Download ID is required'}), 400
    
    # Check if download is in batch manager
    if batch_manager.cancel_download(download_id):
        return jsonify({'success': True})
    
    # Check if download is in active downloads
    if download_id in active_downloads:
        active_downloads[download_id]['status'] = 'cancelled'
        return jsonify({'success': True})
    
    return jsonify({'error': 'Download not found'}), 404


# Start a batch download
@app.route('/api/batch-download', methods=['POST'])
def batch_download():
    data = request.json
    
    urls = data.get('urls', [])
    format_str = data.get('format', 'best')
    max_concurrent = data.get('maxConcurrent', 3)
    use_aria2 = data.get('useAria2', True)
    use_proxy = data.get('useProxy', False)
    download_subtitles = data.get('downloadSubtitles', False)
    
    if not urls or not isinstance(urls, list) or len(urls) == 0:
        return jsonify({'error': 'URLs are required'}), 400
    
    # Validate URLs
    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        if is_youtube_url(url):
            valid_urls.append(url)
        else:
            invalid_urls.append(url)
    
    if not valid_urls:
        return jsonify({'error': 'No valid YouTube URLs provided'}), 400
    
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
    
    return jsonify({
        'downloadIds': download_ids,
        'invalidUrls': invalid_urls,
        'message': f"Started {len(valid_urls)} downloads. {len(invalid_urls)} URLs were invalid."
    })


# Download a file
@app.route('/api/download-file/<download_id>')
def download_file(download_id):
    # Check if the file exists in download files
    if download_id in download_files and os.path.exists(download_files[download_id]):
        filename = os.path.basename(download_files[download_id])
        return send_file(
            download_files[download_id],
            as_attachment=True,
            download_name=filename
        )
    
    # Check if the file exists in batch manager
    batch_download = batch_manager.get_download(download_id)
    if batch_download and batch_download['status'] == 'completed' and batch_download.get('output_file'):
        if os.path.exists(batch_download['output_file']):
            filename = os.path.basename(batch_download['output_file'])
            return send_file(
                batch_download['output_file'],
                as_attachment=True,
                download_name=filename
            )
    
    # File not found
    abort(404)


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
        info = ytdlp_downloader.get_info(url, proxy=proxy)
        active_downloads[download_id]['title'] = info.get('title', '')
        
        # Determine which downloader to use
        output_file = None
        
        if format_id.startswith('bestaudio') or format_id.endswith('mp3'):
            # Audio-only download with yt-dlp
            output_file = ytdlp_downloader.download(
                url=url,
                format_str='bestaudio/best',
                proxy=proxy,
                subtitles=download_subtitles,
                on_progress=progress_callback
            )
        elif use_aria2 and aria2_downloader is not None and format_id.startswith('http'):
            # Direct URL download with Aria2
            output_file = aria2_downloader.download(
                url=format_id,  # Direct URL to the format
                proxy=proxy,
                on_progress=progress_callback
            )
        else:
            # Video download with yt-dlp
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
    
    except Exception as e:
        # Update tracking data with error
        active_downloads[download_id].update({
            'status': 'failed',
            'error': str(e)
        })
        print(f"Download error: {e}")


if __name__ == '__main__':
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5000)