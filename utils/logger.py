import os
import logging
import logging.handlers
from datetime import datetime
import traceback
from pathlib import Path
from typing import Optional

from ..config import config

# Get log settings from config
LOG_LEVEL = config.get('log_level', 'INFO').upper()
LOG_DIR = config.get('log_dir', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs'))

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Available log levels
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',  # Cyan
        'INFO': '\033[32m',   # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',  # Red
        'CRITICAL': '\033[41m\033[37m',  # White on red background
        'RESET': '\033[0m'    # Reset color
    }
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname
        return super().format(record)

def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with console and file handlers
    
    Args:
        name: Logger name
        log_file: Log file name (optional, defaults to name.log)
        
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    # Set the log level
    logger.setLevel(LOG_LEVELS.get(LOG_LEVEL, logging.INFO))
    
    # Create handlers
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(ColoredFormatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(console_handler)
    
    # Add file handler if log file is specified
    if log_file is None:
        log_file = f"{name.split('.')[-1]}.log"
    
    log_path = os.path.join(LOG_DIR, log_file)
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, 
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    logger.addHandler(file_handler)
    
    return logger

# Create main application logger
app_logger = setup_logger('4kvideoreaper', 'app.log')
download_logger = setup_logger('4kvideoreaper.download', 'download.log')
api_logger = setup_logger('4kvideoreaper.api', 'api.log')

def log_exception(e: Exception, logger: Optional[logging.Logger] = None) -> None:
    """
    Log an exception with traceback
    
    Args:
        e: Exception to log
        logger: Logger to use (defaults to app_logger)
    """
    if logger is None:
        logger = app_logger
    
    logger.error(f"Exception: {str(e)}")
    logger.error(f"Traceback: {traceback.format_exc()}")

def log_download_start(url: str, download_id: str, format_id: Optional[str] = None) -> None:
    """
    Log the start of a download
    
    Args:
        url: Download URL
        download_id: Download ID
        format_id: Format ID (optional)
    """
    download_logger.info(f"Download started | ID: {download_id} | URL: {url} | Format: {format_id or 'default'}")

def log_download_complete(url: str, download_id: str, output_file: str) -> None:
    """
    Log the completion of a download
    
    Args:
        url: Download URL
        download_id: Download ID
        output_file: Output file path
    """
    download_logger.info(f"Download completed | ID: {download_id} | URL: {url} | File: {output_file}")

def log_download_error(url: str, download_id: str, error: str) -> None:
    """
    Log a download error
    
    Args:
        url: Download URL
        download_id: Download ID
        error: Error message
    """
    download_logger.error(f"Download failed | ID: {download_id} | URL: {url} | Error: {error}")

def log_api_request(endpoint: str, method: str, ip: str, status_code: int, duration_ms: float) -> None:
    """
    Log an API request
    
    Args:
        endpoint: API endpoint
        method: HTTP method
        ip: Client IP address
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
    """
    api_logger.info(f"{method} {endpoint} | IP: {ip} | Status: {status_code} | Duration: {duration_ms:.2f}ms")
