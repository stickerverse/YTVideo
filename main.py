#!/usr/bin/env python3
"""
Main entry point for the YouTube Downloader application.
"""

import sys
import os
import argparse

from .ui.cli import CliInterface
from .config import config


def main() -> int:
    """
    Main entry point for the application.
    
    Returns:
        Exit code
    """
    # Check if running in GUI mode
    if len(sys.argv) > 1 and sys.argv[1] == '--gui':
        try:
            from .ui.gui import GuiInterface
            gui = GuiInterface()
            return gui.run()
        except ImportError:
            print("Error: PySimpleGUI is not installed. Run 'pip install PySimpleGUI' to use the GUI.")
            return 1
    
    # Otherwise run in CLI mode
    cli = CliInterface()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())