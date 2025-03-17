"""
User interface implementations for the YouTube Downloader.
"""

from .cli import CliInterface
try:
    from .gui import GuiInterface
except ImportError:
    # PySimpleGUI might not be installed
    pass

__all__ = [
    'CliInterface',
    'GuiInterface',
]