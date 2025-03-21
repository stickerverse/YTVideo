#!/usr/bin/env python3
"""
Creates necessary __init__.py files and ensures directory structure is correct.
"""
import os
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('create_init_files')

# List of directories that should be Python packages
directories = [
    'youtube_downloader',
    'youtube_downloader/downloaders',
    'youtube_downloader/services',
    'youtube_downloader/utils',
    'youtube_downloader/ui',
    'web'
]

def main():
    logger.info("Starting to create __init__.py files...")
    
    # Get the current working directory
    cwd = os.getcwd()
    logger.info(f"Current working directory: {cwd}")
    
    # Create directories and __init__.py files
    for directory in directories:
        # Create the directory if it doesn't exist
        dir_path = os.path.join(cwd, directory)
        os.makedirs(dir_path, exist_ok=True)
        
        # Create __init__.py in the directory if it doesn't exist
        init_file = os.path.join(dir_path, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'"""\n{directory} package.\n"""\n')
            logger.info(f"Created {init_file}")
        else:
            logger.info(f"{init_file} already exists")
    
    # Create a minimal web/__init__.py file if it doesn't already have content
    web_init = os.path.join(cwd, 'web', '__init__.py')
    if os.path.exists(web_init) and os.path.getsize(web_init) < 10:
        with open(web_init, 'w') as f:
            f.write('"""\nweb package for 4K Video Reaper\n"""\n\n# This file is required for Python to recognize this directory as a package\n')
        logger.info(f"Updated {web_init} with content")
    
    # Ensure web/wsgi.py exists
    wsgi_file = os.path.join(cwd, 'web', 'wsgi.py')
    if not os.path.exists(wsgi_file):
        logger.warning(f"{wsgi_file} does not exist! Creating a minimal version.")
        with open(wsgi_file, 'w') as f:
            f.write('''"""
WSGI entry point for running the 4K Video Reaper web application in production.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

try:
    # Import Flask app from the web/api.py module
    from web.api import app
except Exception as e:
    logger.error(f"Failed to import app: {str(e)}")
    import traceback
    logger.error(traceback.format_exc())
    raise

if __name__ == "__main__":
    # Run the Flask application directly
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port)
''')
        logger.info(f"Created {wsgi_file}")
    
    # Check if web/api.py exists
    api_file = os.path.join(cwd, 'web', 'api.py')
    if not os.path.exists(api_file):
        logger.error(f"{api_file} does not exist! This is required for the application to run.")
    else:
        logger.info(f"{api_file} exists.")
    
    # List all created directories and files
    logger.info("Finished creating __init__.py files")
    logger.info("Directory structure:")
    
    for root, dirs, files in os.walk(cwd):
        level = root.replace(cwd, '').count(os.sep)
        indent = ' ' * 4 * level
        logger.info(f"{indent}{os.path.basename(root)}/")
        sub_indent = ' ' * 4 * (level + 1)
        for file in sorted(f for f in files if f == '__init__.py'):
            logger.info(f"{sub_indent}{file}")

if __name__ == "__main__":
    main()
