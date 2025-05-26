import os
import logging

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7838126945:AAHYk93RfyWjayjlitbdBdZonkkeAXg79OA")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Download configuration
DOWNLOAD_DIR = os.getenv("DOWNLOAD_DIR", "./downloads")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - Telegram's file size limit
MAX_DURATION = 600  # 10 minutes max duration

# yt-dlp configuration
YT_DLP_OPTIONS = {
    'format': 'best[filesize<50M]/best',
    'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
    'noplaylist': True,
    'extractaudio': False,
    'audioformat': 'mp3',
    'embed_subs': False,
    'writesubtitles': False,
    'writeautomaticsub': False,
    'ignoreerrors': True,
}

# Supported platforms
SUPPORTED_PLATFORMS = [
    'youtube.com',
    'youtu.be',
    'instagram.com',
    'facebook.com',
    'fb.watch'
]

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    )
    
    # Reduce noise from other libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
