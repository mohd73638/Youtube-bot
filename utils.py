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


def cleanup_file(file_path: str):
    """Safely remove downloaded files"""
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            # Clean any related temporary files
            base_name = Path(file_path).stem
            for f in Path(file_path).parent.glob(f"{base_name}*"):
                if f != file_path:
                    os.unlink(f)
    except Exception as e:
        logging.warning(f"Cleanup failed for {file_path}: {e}")

def is_supported_url(url: str) -> bool:
    """Check if URL is from supported platforms"""
    domains = [
        " youtube.com" ,
       "  youtu.be ",
        " tiktok.com ",
        " instagram.com ",
        " facebook.com ",
       "  fb.watch "
    ]
    return any(d in url.lower() for d in domains)

# Example of how Config might be used if imported
# class Config:
#    TEMP_DIR = Path("./temp_placeholder")

