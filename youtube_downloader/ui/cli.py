#!/usr/bin/env python3
"""
Command Line Interface for the YouTube Downloader application.
"""

import os
import sys
import argparse
from typing import List, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import config
from ..utils import is_youtube_url, ensure_dir, read_urls_from_file
from ..downloaders import YtdlpDownloader, Aria2Downloader


class CliInterface:
    """
    Command line interface for the YouTube Downloader.
    """
    
    def __init__(self):
        """Initialize the CLI interface."""
        self.downloader = None
        
    def run(self) -> int:
        """
        Run the CLI interface.
        
        Returns:
            Exit code
        """
        parser = argparse.ArgumentParser(description='YouTube Video Downloader')
        parser.add_argument('-u', '--url', type=str, help='YouTube URL to download')
        parser.add_argument('-f', '--file', type=str, help='File containing URLs to download')
        parser.add_argument('-o', '--output', type=str, help='Output directory')
        parser.add_argument('-p', '--proxy', type=str, help='Proxy URL')
        parser.add_argument('--format', type=str, help='Video format to download')
        parser.add_argument('--use-aria2', action='store_true', help='Use Aria2 for downloading')
        parser.add_argument('--subtitles', action='store_true', help='Download subtitles')
        
        args = parser.parse_args()
        
        try:
            # Get URLs to download
            urls = []
            if args.url:
                urls.append(args.url)
            elif args.file:
                urls.extend(read_urls_from_file(args.file))
            else:
                print("Error: Please provide either a URL (-u) or a file (-f)")
                return 1
            
            # Validate URLs
            invalid_urls = [url for url in urls if not is_youtube_url(url)]
            if invalid_urls:
                print(f"Error: Invalid YouTube URLs: {', '.join(invalid_urls)}")
                return 1
            
            # Set up output directory
            output_dir = args.output or config.get('download_dir')
            ensure_dir(output_dir)
            
            # Initialize downloader
            self.downloader = YtdlpDownloader(output_dir)
            
            # Download each URL
            for url in urls:
                print(f"Downloading: {url}")
                try:
                    output_file = self.downloader.download(
                        url,
                        format_str=args.format,
                        proxy=args.proxy,
                        subtitles=args.subtitles
                    )
                    print(f"Downloaded: {output_file}")
                except Exception as e:
                    print(f"Error downloading {url}: {e}")
                    
            print("Download complete!")
            return 0
            
        except Exception as e:
            print(f"Error: {e}")
            return 1