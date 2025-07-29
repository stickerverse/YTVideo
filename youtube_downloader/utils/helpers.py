import os
import re
import subprocess
import platform
from typing import List, Optional, Tuple
from urllib.parse import urlparse

def is_url(url: str) -> bool:
    """
    Check if a string is a valid URL.
    
    Args:
        url: String to check
        
    Returns:
        True if the string is a valid URL, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def is_youtube_url(url: str) -> bool:
    """
    Check if a URL is a valid YouTube URL.
    
    Args:
        url: URL to check
        
    Returns:
        True if the URL is a valid YouTube URL, False otherwise
    """
    if not is_url(url):
        return False
    
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    return bool(re.match(youtube_regex, url))

def ensure_dir(directory: str) -> str:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        The directory path
    """
    if not os.path.exists(directory):
        os.makedirs(directory)
    return directory

def read_urls_from_file(file_path: str) -> List[str]:
    """
    Read URLs from a text file, one URL per line.
    
    Args:
        file_path: Path to the text file
        
    Returns:
        List of URLs
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path, 'r') as f:
        urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
    
    return urls

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Replace invalid characters with underscore
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Trim to reasonable length
    if len(sanitized) > 255:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:255-len(ext)] + ext
        
    return sanitized

def check_aria2_installed() -> Tuple[bool, Optional[str]]:
    """
    Check if Aria2 is installed and available in the system.
    
    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = subprocess.run(['aria2c', '--version'], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        if result.returncode == 0:
            # Extract version from output
            version_match = re.search(r'aria2 version ([0-9.]+)', result.stdout)
            version = version_match.group(1) if version_match else None
            return True, version
        return False, None
    except Exception:
        return False, None

def get_system_info() -> dict:
    """
    Get system information for debugging.
    
    Returns:
        Dictionary with system information
    """
    return {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'aria2_installed': check_aria2_installed()[0],
        'aria2_version': check_aria2_installed()[1],
    }

def format_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.23 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"