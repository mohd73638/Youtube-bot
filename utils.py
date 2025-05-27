import re
import os
import subprocess
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_valid_url(url):
    """Check if the provided string is a valid URL"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def cleanup_file(file_path):
    # Your code here
    pass
def clean_filename(filename):
    """Clean filename for safe file system usage"""
    if not filename:
        return "video"
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    if not filename:
        return "video"
    
    return filename


import re

def sanitize_filename(filename):
    # يحذف أو يستبدل الرموز غير الصالحة من اسم الملف
    return re.sub(r'[\\/*?:"<>|]', "_", filename)
def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if not size_bytes:
        return "Unknown"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def format_duration(seconds):
    """Format duration in human readable format"""
    if not seconds:
        return "Unknown"
    
    try:
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    except:
        return "Unknown"

def get_file_size(file_path):
    """Get file size in bytes"""
    try:
        return os.path.getsize(file_path)
    except:
        return 0

def get_video_duration(file_path):
    """Get video duration using ffprobe if available"""
    try:
        # Try using ffprobe first
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return format_duration(duration)
    except:
        pass
    
    # Fallback: try to get from file metadata
    try:
        # This is a simple fallback, might not always work
        stat = os.stat(file_path)
        # We can't really get duration without proper tools, so return unknown
        return "Unknown"
    except:
        return "Unknown"

def extract_video_id(url):
    """Extract video ID from various video platform URLs"""
    patterns = {
        'youtube': [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        ],
        'instagram': [
            r'instagram\.com\/p\/([a-zA-Z0-9_-]+)',
            r'instagram\.com\/reel\/([a-zA-Z0-9_-]+)',
        ],
        'tiktok': [
            r'tiktok\.com\/@[^/]+\/video\/(\d+)',
            r'vm\.tiktok\.com\/([a-zA-Z0-9]+)',
        ],
        'twitter': [
            r'twitter\.com\/[^/]+\/status\/(\d+)',
            r'x\.com\/[^/]+\/status\/(\d+)',
        ]
    }
    
    for platform, platform_patterns in patterns.items():
        for pattern in platform_patterns:
            match = re.search(pattern, url)
            if match:
                return {
                    'platform': platform,
                    'id': match.group(1)
                }
    
    return {
        'platform': 'unknown',
        'id': None
    }

def is_supported_platform(url):
    """Check if the URL is from a supported platform"""
    supported_domains = [
        'youtube.com', 'youtu.be', 'youtube-nocookie.com',
        'instagram.com', 'instagr.am',
        'tiktok.com', 'vm.tiktok.com',
        'twitter.com', 'x.com', 't.co',
        'facebook.com', 'fb.com', 'fb.watch',
        'vimeo.com',
        'dailymotion.com',
        'twitch.tv',
        'reddit.com', 'v.redd.it',
        'streamable.com',
        'imgur.com'
    ]
    
    try:
        domain = urlparse(url).netloc.lower()
        # Remove www. prefix
        domain = domain.replace('www.', '')
        
        return any(supported in domain for supported in supported_domains)
    except:
        return False

def validate_environment():
    """Validate that all required environment variables are set"""
    required_vars = ['BOT_TOKEN']
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
