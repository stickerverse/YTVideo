import os
import subprocess
import time
import re
from typing import Optional, Dict, Any, List, Tuple, Callable
import threading
from pathlib import Path

from ..config import config
from ..utils import ensure_dir, check_aria2_installed, sanitize_filename


class Aria2Downloader:
    """
    Downloader implementation using Aria2 for multi-threaded downloads.
    """
    
    def __init__(self, download_dir: Optional[str] = None):
        """
        Initialize the Aria2 downloader.
        
        Args:
            download_dir: Directory to save downloads to (defaults to config value)
        """
        self.download_dir = download_dir or config.get('download_dir')
        self.aria2_path = config.get('aria2.path', 'aria2c')
        self.max_connections = config.get('aria2.max_connections', 4)
        self.split = config.get('aria2.split', 4)
        
        # Ensure the download directory exists
        ensure_dir(self.download_dir)
        
        # Check if Aria2 is installed
        is_installed, version = check_aria2_installed()
        if not is_installed:
            raise RuntimeError("Aria2 is not installed or not found in PATH. Please install Aria2 first.")
        
        self._processes: Dict[str, subprocess.Popen] = {}
        self._progress_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
    
    def download(self, url: str, output_file: Optional[str] = None, 
                proxy: Optional[str] = None, 
                on_progress: Optional[Callable[[str, int, int], None]] = None) -> str:
        """
        Download a file using Aria2.
        
        Args:
            url: URL to download
            output_file: Path to save the file (defaults to the filename from URL)
            proxy: Proxy URL to use
            on_progress: Callback function for progress updates (url, downloaded_bytes, total_bytes)
            
        Returns:
            Path to the downloaded file
        """
        # Determine output file path
        if output_file:
            # If output_file is just a filename, put it in the download directory
            if not os.path.dirname(output_file):
                output_file = os.path.join(self.download_dir, output_file)
        else:
            # Extract filename from URL or use a default
            filename = os.path.basename(url.split('?')[0]) or 'download'
            filename = sanitize_filename(filename)
            output_file = os.path.join(self.download_dir, filename)
        
        # Ensure the directory exists
        ensure_dir(os.path.dirname(output_file))
        
        # Build Aria2 command
        command = [
            self.aria2_path,
            '--max-connection-per-server', str(self.max_connections),
            '--split', str(self.split),
            '--dir', os.path.dirname(output_file),
            '--out', os.path.basename(output_file),
            '--summary-interval', '1',  # Update summary every second
            '--console-log-level', 'notice',
        ]
        
        # Add proxy if provided
        if proxy:
            command.extend(['--all-proxy', proxy])
        
        # Add URL
        command.append(url)
        
        # Create a stop event for the progress thread
        download_id = str(hash(url + output_file))
        stop_event = threading.Event()
        self._stop_events[download_id] = stop_event
        
        # Start Aria2 process
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
        )
        
        self._processes[download_id] = process
        
        # Start progress monitoring thread if callback provided
        if on_progress:
            thread = threading.Thread(
                target=self._monitor_progress,
                args=(process, url, output_file, on_progress, stop_event),
                daemon=True
            )
            thread.start()
            self._progress_threads[download_id] = thread
        
        # Wait for the process to finish
        process.wait()
        
        # Signal the progress thread to stop
        if download_id in self._stop_events:
            self._stop_events[download_id].set()
        
        # Check if download was successful
        if process.returncode != 0:
            raise RuntimeError(f"Aria2 download failed with exit code {process.returncode}")
        
        # Clean up
        if download_id in self._processes:
            del self._processes[download_id]
        if download_id in self._progress_threads:
            del self._progress_threads[download_id]
        if download_id in self._stop_events:
            del self._stop_events[download_id]
        
        return output_file
    
    def _monitor_progress(self, process: subprocess.Popen, url: str, 
                         output_file: str, 
                         on_progress: Callable[[str, int, int], None],
                         stop_event: threading.Event) -> None:
        """
        Monitor the progress of a download by parsing Aria2 output.
        
        Args:
            process: Aria2 subprocess
            url: Download URL
            output_file: Output file path
            on_progress: Callback function for progress updates
            stop_event: Event to signal the thread to stop
        """
        downloaded = 0
        total = 0
        
        # Regular expressions to extract progress information
        download_regex = r'\(([0-9.]+)%\)'
        speed_regex = r'([0-9.]+[KMGT]?i?B/s)'
        size_regex = r'([0-9.]+[KMGT]?i?B)/([0-9.]+[KMGT]?i?B)'
        
        while process.poll() is None and not stop_event.is_set():
            if process.stdout:
                line = process.stdout.readline().strip()
                if not line:
                    continue
                
                # Parse progress percentage
                download_match = re.search(download_regex, line)
                if download_match:
                    percentage = float(download_match.group(1))
                    
                    # Parse size information
                    size_match = re.search(size_regex, line)
                    if size_match:
                        downloaded_str = size_match.group(1)
                        total_str = size_match.group(2)
                        
                        # Convert size strings to bytes
                        downloaded = self._parse_size(downloaded_str)
                        total = self._parse_size(total_str)
                        
                        # Call the progress callback
                        on_progress(url, downloaded, total)
            
            time.sleep(0.1)
        
        # Send a final progress update
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            on_progress(url, file_size, file_size)
    
    def _parse_size(self, size_str: str) -> int:
        """
        Parse a size string (e.g., "10.5MiB") to bytes.
        
        Args:
            size_str: Size string to parse
            
        Returns:
            Size in bytes
        """
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024**2,
            'GB': 1024**3,
            'TB': 1024**4,
            'KiB': 1024,
            'MiB': 1024**2,
            'GiB': 1024**3,
            'TiB': 1024**4,
        }
        
        match = re.match(r'([0-9.]+)\s*([KMGT]i?B|B)', size_str)
        if match:
            value, unit = match.groups()
            return int(float(value) * units.get(unit, 1))
        
        return 0
    
    def cancel_download(self, url: str, output_file: Optional[str] = None) -> None:
        """
        Cancel an ongoing download.
        
        Args:
            url: URL of the download to cancel
            output_file: Output file path of the download to cancel
        """
        if output_file is None:
            filename = os.path.basename(url.split('?')[0]) or 'download'
            filename = sanitize_filename(filename)
            output_file = os.path.join(self.download_dir, filename)
            
        download_id = str(hash(url + output_file))
        
        if download_id in self._processes:
            process = self._processes[download_id]
            if process.poll() is None:  # If process is still running
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            
            # Signal the progress thread to stop
            if download_id in self._stop_events:
                self._stop_events[download_id].set()
            
            # Clean up
            if download_id in self._processes:
                del self._processes[download_id]
            if download_id in self._progress_threads:
                del self._progress_threads[download_id]
            if download_id in self._stop_events:
                del self._stop_events[download_id]