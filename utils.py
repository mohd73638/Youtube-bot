import os
import logging
import shutil
from pathlib import Path
from typing import Optional
from send2trash import send2trash

logger = logging.getLogger(__name__)

def cleanup_file(path: str) -> bool:
    """Safely remove files with different strategies for temp vs. permanent files."""
    try:
        path_obj = Path(path)
        if not path_obj.exists():
            return True
            
        # Use system trash for user downloads, immediate delete for temp files
        if str(path_obj).startswith(Config.get_temp_dir()):
            path_obj.unlink()
        else:
            send2trash(str(path_obj))
            
        logger.info(f"Cleaned up: {path}")
        return True
    except Exception as e:
        logger.error(f"Cleanup failed for {path}: {str(e)}")
        return False

def format_file_size(bytes: int) -> str:
    """Convert bytes to human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024.0:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.2f} TB"

def sanitize_filename(filename: str) -> str:
    """Make filenames safe for storage."""
    keepchars = (' ', '.', '_', '-')
    return "".join(
        c for c in filename 
        if c.isalnum() or c in keepchars
    ).rstrip()

def ensure_download_dir() -> Path:
    """Ensure download directory exists with proper permissions."""
    path = Path(Config.DOWNLOAD_DIR)
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Set permissions (rwx for owner, rx for others)
        path.chmod(0o755)
        return path
    except Exception as e:
        logger.critical(f"Failed to create download directory: {str(e)}")
        raise
