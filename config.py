import os
from pathlib import Path

class Config:
    """Configuration class for the bot with Render.com optimizations"""
    
    # --- Required Configs ---
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://youtube-bot-3-1g9w.onrender.com")

    # --- Path Configurations ---
    BASE_DIR = Path(__file__).parent.parent
    TEMP_DIR = BASE_DIR / os.getenv("TEMP_DIR", "temp")
    DOWNLOAD_DIR = BASE_DIR / "downloads"

    # --- Download Settings ---
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB
    DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", 300))  # 5 minutes
    VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "best[height<=720]")  # 720p max
    AUDIO_FORMAT = os.getenv("AUDIO_FORMAT", "mp3")
    ENABLE_AUDIO_EXTRACTION = os.getenv("ENABLE_AUDIO_EXTRACTION", "false").lower() == "true"

    # --- YT-DLP Options ---
    YT_DLP_OPTIONS = {
        "format": "best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "paths": {
            "home": str(DOWNLOAD_DIR),
            "temp": str(TEMP_DIR)
        }
    }

    @classmethod
    def validate(cls):
        """Validate config and create directories"""
        # Create required directories
        cls.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        cls.DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)

        # Validate required vars
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not cls.WEBHOOK_URL:
            raise ValueError("WEBHOOK_URL is required")

        return True
