import os
import tempfile
import logging
from urllib.parse import urlparse
from config import SUPPORTED_PLATFORMS, DOWNLOAD_DIR

logger = logging.getLogger(__name__)

def is_supported_url(url):
    """Check if the URL is from a supported platform"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        return any(platform in domain for platform in SUPPORTED_PLATFORMS)
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
        return False

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def cleanup_file(file_path):
    """Safely delete a file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}")

def ensure_download_dir():
    """Ensure download directory exists"""
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
        logger.info(f"Created download directory: {DOWNLOAD_DIR}")

def get_platform_name(url):
    """Get the platform name from URL"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'YouTube'
        elif 'instagram.com' in domain:
            return 'Instagram'
        elif 'facebook.com' in domain or 'fb.watch' in domain:
            return 'Facebook'
        else:
            return 'Unknown'
    except:
        return 'Unknown'

def sanitize_filename(filename):
    """Sanitize filename for safe file operations"""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200-len(ext)] + ext
    return filename
