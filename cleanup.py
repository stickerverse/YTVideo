#!/usr/bin/env python3
"""
Cleanup script for 4K Video Reaper
---------------------------------

This script removes old downloaded files to free up disk space.
It's designed to be run as a cron job or scheduled task.
"""

import os
import sys
import time
import argparse
import logging
import shutil
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.environ.get('LOG_DIR', '/tmp/logs'), 'cleanup.log'))
    ]
)
logger = logging.getLogger('cleanup')

def check_disk_space(directory):
    """
    Check available disk space and return statistics
    
    Args:
        directory: Directory to check
    
    Returns:
        Tuple of (free_space_mb, total_space_mb, used_percent)
    """
    try:
        # Get disk stats
        stats = shutil.disk_usage(directory)
        free_space_mb = stats.free / (1024 * 1024)
        total_space_mb = stats.total / (1024 * 1024)
        used_percent = (stats.used / stats.total) * 100
        
        logger.info(f"Disk space: {free_space_mb:.2f}MB free out of {total_space_mb:.2f}MB total ({used_percent:.1f}% used)")
        
        return free_space_mb, total_space_mb, used_percent
    except Exception as e:
        logger.error(f"Error checking disk space: {e}")
        return 0, 0, 0

def cleanup_old_files(directory, max_age_hours=24, dry_run=False, min_free_space_mb=1024):
    """
    Clean up old files in a directory.
    
    Args:
        directory: Directory to clean
        max_age_hours: Maximum age of files in hours before deletion
        dry_run: If True, don't actually delete files
        min_free_space_mb: Minimum free space to maintain in MB
    
    Returns:
        Tuple of (number of files deleted, space freed in bytes)
    """
    logger.info(f"Starting cleanup in {directory}")
    logger.info(f"Max age: {max_age_hours} hours, Min free space: {min_free_space_mb} MB, Dry run: {dry_run}")
    
    if not os.path.exists(directory):
        logger.warning(f"Directory does not exist: {directory}")
        return 0, 0
    
    # Check current free space
    free_space_mb, total_space_mb, used_percent = check_disk_space(directory)
    
    # If we're below the minimum free space or above 80% usage, be more aggressive
    if free_space_mb < min_free_space_mb or used_percent > 80:
        logger.warning(f"Low disk space ({free_space_mb:.2f} MB), aggressive cleanup needed")
        # Reduce max age to free up more space
        original_max_age = max_age_hours
        max_age_hours = max(1, max_age_hours // 2)
        logger.info(f"Reduced max age from {original_max_age} to {max_age_hours} hours for aggressive cleanup")
    
    # If critically low (less than 100MB), delete all files
    if free_space_mb < 100:
        logger.critical(f"Critical disk space: {free_space_mb:.2f}MB free. Removing all files.")
        max_age_hours = 0
    
    cutoff_time = time.time() - (max_age_hours * 60 * 60)
    files_deleted = 0
    space_freed = 0
    
    # If max_age_hours is 0, delete all files
    if max_age_hours == 0:
        logger.warning(f"Removing ALL files from {directory}")
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                try:
                    file_size = os.path.getsize(file_path)
                    
                    if dry_run:
                        logger.info(f"Would delete: {file_path} ({format_size(file_size)})")
                    else:
                        os.remove(file_path)
                        logger.info(f"Deleted: {file_path} ({format_size(file_size)})")
                    
                    files_deleted += 1
                    space_freed += file_size
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}")
        
        logger.info(f"Cleanup completed. Deleted {files_deleted} files, freed {format_size(space_freed)}")
        return files_deleted, space_freed
    
    # Otherwise, delete files older than the cutoff time
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        
        # Skip directories
        if os.path.isdir(file_path):
            continue
        
        # Check file age
        try:
            file_mtime = os.path.getmtime(file_path)
            if file_mtime < cutoff_time:
                file_size = os.path.getsize(file_path)
                
                if dry_run:
                    logger.info(f"Would delete: {file_path} ({format_size(file_size)})")
                else:
                    os.remove(file_path)
                    logger.info(f"Deleted: {file_path} ({format_size(file_size)})")
                
                files_deleted += 1
                space_freed += file_size
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    logger.info(f"Cleanup completed. Deleted {files_deleted} files, freed {format_size(space_freed)}")
    
    # Check if we still need to free up more space
    free_space_mb, _, used_percent = check_disk_space(directory)
    if free_space_mb < min_free_space_mb and max_age_hours > 1 and not dry_run:
        # Still not enough space, run again with a shorter max age
        logger.warning(f"Still insufficient space ({free_space_mb:.2f} MB), running additional cleanup")
        additional_files, additional_space = cleanup_old_files(
            directory,
            max_age_hours=max(1, max_age_hours // 2),
            dry_run=dry_run,
            min_free_space_mb=min_free_space_mb
        )
        files_deleted += additional_files
        space_freed += additional_space
    
    return files_deleted, space_freed

def format_size(size_bytes):
    """Format a file size in bytes to a human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Clean up old downloaded files')
    parser.add_argument('--dir', type=str, default=os.environ.get('DOWNLOAD_DIR', '/tmp/downloads'),
                        help='Directory to clean (default: DOWNLOAD_DIR env var or /tmp/downloads)')
    parser.add_argument('--max-age', type=int, default=24,
                        help='Maximum age of files in hours before deletion (default: 24)')
    parser.add_argument('--min-free-space', type=int, default=1024,
                        help='Minimum free space to maintain in MB (default: 1024)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Do not actually delete files, just print what would be deleted')
    args = parser.parse_args()
    
    try:
        cleanup_old_files(
            args.dir,
            max_age_hours=args.max_age,
            dry_run=args.dry_run,
            min_free_space_mb=args.min_free_space
        )
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
