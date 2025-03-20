#!/usr/bin/env python3
import os

# List of directories that should be Python packages
directories = [
    'youtube_downloader',
    'youtube_downloader/downloaders',
    'youtube_downloader/services',
    'youtube_downloader/utils',
    'youtube_downloader/ui',
    'web'
]

for directory in directories:
    # Create the directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)
    
    # Create __init__.py in the directory if it doesn't exist
    init_file = os.path.join(directory, '__init__.py')
    if not os.path.exists(init_file):
        with open(init_file, 'w') as f:
            f.write('# Auto-generated __init__.py file\n')
        print(f"Created {init_file}")
    else:
        print(f"{init_file} already exists")

print("Finished creating __init__.py files")
