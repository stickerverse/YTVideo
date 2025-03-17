"""
Services for handling various aspects of the YouTube Downloader.
"""

from .proxy_manager import ProxyManager
from .captcha_solver import CaptchaSolver
from .batch_manager import BatchManager

__all__ = [
    'ProxyManager',
    'CaptchaSolver',
    'BatchManager',
]