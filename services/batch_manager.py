import os
import time
import threading
import queue
from typing import List, Dict, Any, Optional, Callable, Tuple
import concurrent.futures
from uuid import uuid4

from ..config import config
from ..utils import read_urls_from_file, is_youtube_url
from ..downloaders import YtdlpDownloader, Aria2Downloader
from .proxy_manager import ProxyManager


class BatchManager:
    """
    Manager for handling batch downloads.
    """
    
    def __init__(self, download_dir: Optional[str] = None, 
                max_concurrent: Optional[int] = None,
                proxy_manager: Optional[ProxyManager] = None):
        """
        Initialize the batch manager.
        
        Args:
            download_dir: Directory to save downloads to (defaults to config value)
            max_concurrent: Maximum number of concurrent downloads (defaults to config value)
            proxy_manager: Proxy manager instance (optional)
        """
        self.download_dir = download_dir or config.get('download_dir')
        self.max_concurrent = max_concurrent or config.get('batch.max_concurrent', 3)
        self.proxy_manager = proxy_manager
        
        # Downloaders
        self.ytdlp = YtdlpDownloader(download_dir=self.download_dir)
        self.aria2 = None
        if config.get('aria2.enabled', True):
            try:
                self.aria2 = Aria2Downloader(download_dir=self.download_dir)
            except RuntimeError:
                print("Aria2 is not installed or not found in PATH. Falling back to yt-dlp only.")
        
        # Download tracking
        self.downloads: Dict[str, Dict[str, Any]] = {}
        self.download_queue = queue.Queue()
        self.queue_thread = None
        self.stop_flag = threading.Event()
        self.locks = {}  # Locks for thread-safe updates to download entries
    
    def add_url(self, url: str, use_aria2: bool = False, 
               format_str: Optional[str] = None,
               proxy: Optional[str] = None,
               subtitles: bool = False) -> str:
        """
        Add a URL to the download queue.
        
        Args:
            url: URL to download
            use_aria2: Whether to use Aria2 for the download
            format_str: Video format to download (for yt-dlp)
            proxy: Proxy URL to use
            subtitles: Whether to download subtitles (for yt-dlp)
            
        Returns:
            Download ID
        """
        download_id = str(uuid4())
        
        download_entry = {
            'id': download_id,
            'url': url,
            'status': 'queued',
            'progress': 0.0,
            'downloaded_bytes': 0,
            'total_bytes': 0,
            'speed': 0,
            'eta': 0,
            'added_at': time.time(),
            'started_at': None,
            'completed_at': None,
            'use_aria2': use_aria2 and self.aria2 is not None,
            'format': format_str,
            'proxy': proxy,
            'subtitles': subtitles,
            'output_file': None,
            'error': None,
        }
        
        self.locks[download_id] = threading.Lock()
        self.downloads[download_id] = download_entry
        self.download_queue.put(download_id)
        
        # Start the queue processing thread if it's not already running
        self._ensure_queue_thread()
        
        return download_id
    
    def add_urls(self, urls: List[str], use_aria2: bool = False,
                format_str: Optional[str] = None,
                proxy: Optional[str] = None,
                subtitles: bool = False) -> List[str]:
        """
        Add multiple URLs to the download queue.
        
        Args:
            urls: List of URLs to download
            use_aria2: Whether to use Aria2 for the downloads
            format_str: Video format to download (for yt-dlp)
            proxy: Proxy URL to use
            subtitles: Whether to download subtitles (for yt-dlp)
            
        Returns:
            List of download IDs
        """
        download_ids = []
        
        for url in urls:
            download_id = self.add_url(
                url=url,
                use_aria2=use_aria2,
                format_str=format_str,
                proxy=proxy,
                subtitles=subtitles
            )
            download_ids.append(download_id)
        
        return download_ids
    
    def add_from_file(self, file_path: str, use_aria2: bool = False,
                     format_str: Optional[str] = None,
                     proxy: Optional[str] = None,
                     subtitles: bool = False) -> List[str]:
        """
        Add URLs from a text file to the download queue.
        
        Args:
            file_path: Path to a text file containing URLs (one per line)
            use_aria2: Whether to use Aria2 for the downloads
            format_str: Video format to download (for yt-dlp)
            proxy: Proxy URL to use
            subtitles: Whether to download subtitles (for yt-dlp)
            
        Returns:
            List of download IDs
        """
        urls = read_urls_from_file(file_path)
        return self.add_urls(
            urls=urls,
            use_aria2=use_aria2,
            format_str=format_str,
            proxy=proxy,
            subtitles=subtitles
        )
    
    def cancel_download(self, download_id: str) -> bool:
        """
        Cancel a download.
        
        Args:
            download_id: ID of the download to cancel
            
        Returns:
            True if the download was cancelled, False otherwise
        """
        if download_id not in self.downloads:
            return False
        
        with self.locks.get(download_id, threading.Lock()):
            download = self.downloads[download_id]
            
            if download['status'] in ('completed', 'failed', 'cancelled'):
                return False
            
            if download['status'] == 'downloading':
                # Cancel the active download if possible
                if download['use_aria2'] and self.aria2 is not None:
                    self.aria2.cancel_download(download['url'])
                elif hasattr(self.ytdlp, 'cancel_download'):
                    self.ytdlp.cancel_download(download_id)
            
            # Update status
            download['status'] = 'cancelled'
            download['completed_at'] = time.time()
            
            return True
    
    def get_download(self, download_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a download.
        
        Args:
            download_id: ID of the download
            
        Returns:
            Download information dictionary, or None if not found
        """
        return self.downloads.get(download_id)
    
    def get_all_downloads(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all downloads.
        
        Returns:
            Dictionary mapping download IDs to download information
        """
        return self.downloads.copy()
    
    def clear_completed(self) -> int:
        """
        Clear completed downloads from the tracking list.
        
        Returns:
            Number of downloads cleared
        """
        cleared = 0
        
        for download_id in list(self.downloads.keys()):
            with self.locks.get(download_id, threading.Lock()):
                download = self.downloads[download_id]
                
                if download['status'] in ('completed', 'failed', 'cancelled'):
                    del self.downloads[download_id]
                    if download_id in self.locks:
                        del self.locks[download_id]
                    cleared += 1
        
        return cleared
    
    def stop(self) -> None:
        """
        Stop the batch manager and cancel all active downloads.
        """
        self.stop_flag.set()
        
        # Cancel all active downloads
        for download_id, download in self.downloads.items():
            if download['status'] == 'downloading':
                self.cancel_download(download_id)
        
        # Wait for the queue thread to finish
        if self.queue_thread and self.queue_thread.is_alive():
            self.queue_thread.join(timeout=5)
    
    def _ensure_queue_thread(self) -> None:
        """
        Ensure the queue processing thread is running.
        """
        if self.queue_thread is None or not self.queue_thread.is_alive():
            self.stop_flag.clear()
            self.queue_thread = threading.Thread(
                target=self._process_queue,
                daemon=True
            )
            self.queue_thread.start()
    
    def _process_queue(self) -> None:
        """
        Process the download queue.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            futures = {}
            
            while not self.stop_flag.is_set():
                # Submit new downloads if we have capacity
                while len(futures) < self.max_concurrent and not self.download_queue.empty():
                    try:
                        download_id = self.download_queue.get(block=False)
                        
                        # Skip if the download has been cancelled
                        if self.downloads[download_id]['status'] == 'cancelled':
                            self.download_queue.task_done()
                            continue
                        
                        # Update status
                        with self.locks[download_id]:
                            self.downloads[download_id]['status'] = 'downloading'
                            self.downloads[download_id]['started_at'] = time.time()
                        
                        # Submit the download
                        future = executor.submit(
                            self._download,
                            download_id
                        )
                        futures[future] = download_id
                        
                        self.download_queue.task_done()
                    except queue.Empty:
                        break
                
                # Check for completed downloads
                for future in list(concurrent.futures.as_completed(futures.keys(), timeout=0.1)):
                    download_id = futures[future]
                    
                    try:
                        output_file = future.result()
                        
                        # Update status
                        with self.locks[download_id]:
                            self.downloads[download_id]['status'] = 'completed'
                            self.downloads[download_id]['output_file'] = output_file
                            self.downloads[download_id]['completed_at'] = time.time()
                            self.downloads[download_id]['progress'] = 100.0
                    except Exception as e:
                        # Update status
                        with self.locks[download_id]:
                            self.downloads[download_id]['status'] = 'failed'
                            self.downloads[download_id]['error'] = str(e)
                            self.downloads[download_id]['completed_at'] = time.time()
                    
                    # Remove the future
                    del futures[future]
                
                # Sleep briefly to avoid high CPU usage
                time.sleep(0.1)
                
                # Exit if we're stopping and there are no active downloads
                if self.stop_flag.is_set() and not futures:
                    break
    
    def _download(self, download_id: str) -> str:
        """
        Download a URL.
        
        Args:
            download_id: ID of the download
            
        Returns:
            Path to the downloaded file
        """
        download = self.downloads[download_id]
        url = download['url']
        
        # Get a proxy if needed
        proxy = download['proxy']
        if not proxy and self.proxy_manager:
            proxy = self.proxy_manager.get_proxy()
        
        # Define progress callback
        def progress_callback(url: str, downloaded_bytes: int, total_bytes: int) -> None:
            with self.locks[download_id]:
                progress = (downloaded_bytes / total_bytes * 100) if total_bytes > 0 else 0
                self.downloads[download_id].update({
                    'progress': progress,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes,
                })
        
        try:
            # Use appropriate downloader based on configuration
            if download['use_aria2'] and self.aria2 is not None:
                output_file = self.aria2.download(
                    url=url,
                    proxy=proxy,
                    on_progress=progress_callback
                )
            else:
                # Check if it's a YouTube URL
                if is_youtube_url(url):
                    output_file = self.ytdlp.download(
                        url=url,
                        format_str=download['format'],
                        proxy=proxy,
                        subtitles=download['subtitles'],
                        on_progress=progress_callback
                    )
                else:
                    # For non-YouTube URLs, fallback to Aria2 if available
                    if self.aria2 is not None:
                        output_file = self.aria2.download(
                            url=url,
                            proxy=proxy,
                            on_progress=progress_callback
                        )
                    else:
                        raise ValueError(f"URL '{url}' is not a YouTube URL and Aria2 is not available")
            
            return output_file
        
        except Exception as e:
            # If using a proxy and it fails, mark it as failed
            if proxy and self.proxy_manager:
                self.proxy_manager.mark_proxy_failure(proxy)
            
            raise e