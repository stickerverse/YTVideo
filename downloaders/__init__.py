"""
Downloader implementations for different download methods.
"""

from .aria2_downloader import Aria2Downloader
from .ytdlp_downloader import YtdlpDownloader

__all__ = [
    'Aria2Downloader',
    'YtdlpDownloader',
]