import os

YT_DLP_OPTIONS = {
    "format": "best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
DOWNLOAD_DIR = "downloads"
class Config:
    """Configuration class for the bot"""
    
    # Telegram Bot Token - REQUIRED
    BOT_TOKEN = os.getenv('BOT_TOKEN', '')
    
    # Webhook URL - REQUIRED for production
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://youtube-bot-3-1g9w.onrender.com')
    
    # Download settings
    MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', 50 * 1024 * 1024))  # 50MB default
    DOWNLOAD_TIMEOUT = int(os.getenv('DOWNLOAD_TIMEOUT', 300))  # 5 minutes
    
    # Temporary directory for downloads
    # ...
    TEMP_DIR = os.getenv("TEMP_DIR", "temp")  # مثال لقيمة افتراضية

    temp_dir = TEMP_DIR  # أو فقط استخدم TEMP_DIR بدون متغير جديد
    
    # Video quality settings
    VIDEO_QUALITY = os.getenv('VIDEO_QUALITY', 'best[height<=720]')  # 720p max
    
    # Audio format for audio-only downloads
    AUDIO_FORMAT = os.getenv('AUDIO_FORMAT', 'mp3')
    
    # Enable/disable audio extraction
    ENABLE_AUDIO_EXTRACTION = os.getenv('ENABLE_AUDIO_EXTRACTION', 'false').lower() == 'true'
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is required")
        
        if not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL environment variable is required")
        
        return True
