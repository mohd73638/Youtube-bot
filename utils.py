import os
import re
import logging # Added logging
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse
from send2trash import send2trash

# Assuming Config is available, otherwise import it
# from config import Config 

logger = logging.getLogger(__name__) # Added logger instance

# --- Expanded list of potentially supported domains (yt-dlp covers many) ---
# Note: Actual support depends on yt-dlp's capabilities and potential site changes.
SUPPORTED_DOMAINS = [
    # Core
    "youtube.com", "youtu.be", "tiktok.com", "instagram.com",
    # Major Video Platforms
    "vimeo.com", "dailymotion.com", "facebook.com", "fb.watch", 
    "twitter.com", "x.com", # Twitter/X
    "twitch.tv",
    # Other common platforms (yt-dlp might support)
    "soundcloud.com", "bilibili.com", "nicovideo.jp", "vk.com",
    "pinterest.com", "reddit.com",
    # Add more domains as needed based on yt-dlp documentation or user requests
]

def get_domain(url: str) -> Optional[str]:
    """Extract the main domain name from a URL."""
    try:
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.lower()
        # Handle cases like 'm.youtube.com' -> 'youtube.com'
        parts = netloc.split('.')
        if len(parts) > 2 and parts[0] in ['www', 'm', 'mobile']:
            return '.'.join(parts[1:])
        # Handle short domains like youtu.be, fb.watch
        if netloc in [d for d in SUPPORTED_DOMAINS if '.' not in d[1:]]: # Check if it's a short domain in our list
             return netloc
        # General case for subdomains
        if len(parts) >= 2:
            return '.'.join(parts[-2:])
        return netloc # Should not happen often for valid URLs
    except Exception as e:
        logger.error(f"Error parsing domain from URL 	'{url}	': {e}")
        return None

def is_supported_url(url: str) -> bool:
    """Check if the URL's domain is in our supported list."""
    domain = get_domain(url)
    if domain:
        # Check if the extracted domain or a known variation exists in SUPPORTED_DOMAINS
        return any(supported_domain in domain for supported_domain in SUPPORTED_DOMAINS)
    return False

def cleanup_file(path: str) -> bool:
    """Safe file deletion using send2trash (or direct delete for temp)."""
    # Ensure Config.TEMP_DIR is accessible or handle the path comparison differently
    # For simplicity, we'll assume path comparison works or remove it.
    # Let's default to send2trash for safety unless path is clearly temporary.
    try:
        path_obj = Path(path)
        if path_obj.exists():
            # Basic check if it's likely a temp file based on name pattern (less reliable)
            # A better approach would be passing the temp dir path to this function.
            # if "temp" in str(path_obj.parent).lower() or path_obj.name.startswith("tmp"):
            #    path_obj.unlink() # Immediate delete for likely temp files
            # else:
            send2trash(str(path_obj)) # Safer default
            logger.info(f"Moved to trash: {path}")
        return True
    except Exception as e:
        logger.error(f"Cleanup failed for 	'{path}	': {e}")
        return False

# Example of how Config might be used if imported
# class Config:
#    TEMP_DIR = Path("./temp_placeholder")

