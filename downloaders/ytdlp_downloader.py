import os
import time
from typing import Optional, Dict, Any, List, Tuple, Callable, Union
import yt_dlp

from ..config import config
from ..utils import ensure_dir, is_youtube_url, sanitize_filename


class YtdlpDownloader:
    """
    Downloader implementation using yt-dlp for YouTube and other supported sites.
    """
    
    def __init__(self, download_dir: Optional[str] = None):
        """
        Initialize the yt-dlp downloader.
        
        Args:
            download_dir: Directory to save downloads to (defaults to config value)
        """
        self.download_dir = download_dir or config.get('download_dir')
        self.format = config.get('ytdlp.format', 'bestvideo+bestaudio/best')
        self.preferred_codec = config.get('ytdlp.preferred_codec', 'mp4')
        
        # Ensure the download directory exists
        ensure_dir(self.download_dir)
        
        # Active downloads
        self._active_downloads: Dict[str, Dict[str, Any]] = {}
    
    def download(self, url: str, output_template: Optional[str] = None, 
                format_str: Optional[str] = None, 
                proxy: Optional[str] = None, 
                subtitles: bool = False,
                on_progress: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        Download a video using yt-dlp.
        
        Args:
            url: URL to download
            output_template: Output filename template (defaults to "%(title)s.%(ext)s")
            format_str: Video format to download (defaults to config value)
            proxy: Proxy URL to use
            subtitles: Whether to download subtitles
            on_progress: Callback function for progress updates (url, downloaded_bytes, total_bytes)
            
        Returns:
            Path to the downloaded file
        """
        if not is_youtube_url(url):
            raise ValueError(f"URL '{url}' is not a valid YouTube URL")
        
        # Determine output template
        if not output_template:
            output_template = "%(title)s.%(ext)s"
        
        # Full output path with download directory
        output_path = os.path.join(self.download_dir, output_template)
        
        # yt-dlp options
        ydl_opts = {
            'format': format_str or self.format,
            'outtmpl': output_path,
            'progress_hooks': [self._create_progress_hook(url, on_progress)],
            'quiet': not bool(on_progress),  # Only show output if we're not tracking progress ourselves
            'no_warnings': not bool(on_progress),
            'nocheckcertificate': True,  # Skip HTTPS certificate validation
            'ignoreerrors': False,  # Stop on errors
            'noplaylist': True,  # Download single video, not playlist
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': self.preferred_codec,
            }],
        }
        
        # Add proxy if provided
        if proxy:
            ydl_opts['proxy'] = proxy
        
        # Add subtitles if requested
        if subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = ['en']  # Default to English
        
        # Create download tracker
        download_id = str(hash(url + output_path))
        self._active_downloads[download_id] = {
            'url': url,
            'output_path': output_path,
            'started_at': time.time(),
            'status': 'downloading',
            'progress': 0.0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
        }
        
        try:
            # Download with yt-dlp
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                
                # Get the downloaded file path
                if info:
                    title = info.get('title', 'video')
                    title = sanitize_filename(title)
                    ext = info.get('ext', self.preferred_codec)
                    filename = f"{title}.{ext}"
                    downloaded_file = os.path.join(self.download_dir, filename)
                    
                    # Update download status
                    self._active_downloads[download_id]['status'] = 'completed'
                    self._active_downloads[download_id]['progress'] = 100.0
                    
                    # Return the path to the downloaded file
                    return downloaded_file
        except Exception as e:
            # Update download status
            self._active_downloads[download_id]['status'] = 'failed'
            self._active_downloads[download_id]['error'] = str(e)
            
            raise RuntimeError(f"yt-dlp download failed: {str(e)}")
        finally:
            # Clean up
            if download_id in self._active_downloads:
                del self._active_downloads[download_id]
        
        raise RuntimeError("yt-dlp download failed: No file downloaded")
    
    def _create_progress_hook(self, url: str, on_progress: Optional[Callable[[str, int, int], None]]) -> Callable:
        """
        Create a progress hook function for yt-dlp.
        
        Args:
            url: Download URL
            on_progress: Callback function for progress updates
            
        Returns:
            Progress hook function
        """
        def progress_hook(d: Dict[str, Any]) -> None:
            if d['status'] == 'downloading':
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                
                # Update progress in active downloads
                download_id = str(hash(url + d.get('filename', '')))
                if download_id in self._active_downloads:
                    self._active_downloads[download_id].update({
                        'progress': d.get('percentage', 0),
                        'downloaded_bytes': downloaded_bytes,
                        'total_bytes': total_bytes,
                        'speed': d.get('speed', 0),
                        'eta': d.get('eta', 0),
                    })
                
                # Call the progress callback if provided
                if on_progress and total_bytes > 0:
                    on_progress(url, downloaded_bytes, total_bytes)
            
            elif d['status'] == 'finished':
                # Final progress update
                if on_progress:
                    filename = d.get('filename', '')
                    if os.path.exists(filename):
                        file_size = os.path.getsize(filename)
                        on_progress(url, file_size, file_size)
        
        return progress_hook
    
    def get_info(self, url: str, proxy: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about a video without downloading it.
        
        Args:
            url: URL to get information for
            proxy: Proxy URL to use
            
        Returns:
            Dictionary with video information
        """
        if not is_youtube_url(url):
            raise ValueError(f"URL '{url}' is not a valid YouTube URL")
        
        # yt-dlp options
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,  # Don't download the video
            'nocheckcertificate': True,
            'ignoreerrors': False,
        }
        
        # Add proxy if provided
        if proxy:
            ydl_opts['proxy'] = proxy
        
        # Get video info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info if info else {}
    
    def get_formats(self, url: str, proxy: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get available formats for a video.
        
        Args:
            url: URL to get formats for
            proxy: Proxy URL to use
            
        Returns:
            List of available formats
        """
        info = self.get_info(url, proxy)
        return info.get('formats', [])
    
    def list_active_downloads(self) -> Dict[str, Dict[str, Any]]:
        """
        Get a list of active downloads.
        
        Returns:
            Dictionary of active downloads
        """
        return self._active_downloads.copy()
    
    def cancel_download(self, download_id: str) -> bool:
        """
        Cancel an active download.
        
        Args:
            download_id: ID of the download to cancel
            
        Returns:
            True if the download was cancelled, False otherwise
        """
        if download_id in self._active_downloads:
            # We can't directly cancel yt-dlp downloads, but we can mark it as cancelled
            # and clean up the tracking information
            self._active_downloads[download_id]['status'] = 'cancelled'
            del self._active_downloads[download_id]
            return True
        
        return False