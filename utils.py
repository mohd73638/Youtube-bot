import os
import re
from pathlib import Path
from typing import Optional, Dict
from urllib.parse import urlparse
from send2trash import send2trash

def is_supported_url(url: str) -> bool:
    """Check if URL is from supported platforms"""
    domains = ["youtube.com", "youtu.be", "tiktok.com", "instagram.com"]
    try:
        return any(d in urlparse(url).netloc.lower() for d in domains)
    except:
        return False

def cleanup_file(path: str) -> bool:
    """Safe file deletion with temp/permanent handling"""
    try:
        path = Path(path)
        if path.exists():
            if str(path).startswith(str(Config.TEMP_DIR)):
                path.unlink()  # Immediate delete for temp files
            else:
                send2trash(str(path))  # Safer for user files
        return True
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        return False
