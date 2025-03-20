#!/usr/bin/env python3
"""
Test script to verify module imports.
"""

import os
import sys
import importlib

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath('.'))

# List of modules to test
modules_to_test = [
    'youtube_downloader',
    'youtube_downloader.config',
    'youtube_downloader.downloaders',
    'youtube_downloader.services',
    'youtube_downloader.utils',
    'web',
    'web.api'
]

# Test importing each module
for module_name in modules_to_test:
    try:
        module = importlib.import_module(module_name)
        print(f"✅ Successfully imported {module_name}")
        if hasattr(module, '__file__'):
            print(f"   Location: {module.__file__}")
    except ImportError as e:
        print(f"❌ Failed to import {module_name}: {e}")
