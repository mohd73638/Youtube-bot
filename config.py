import os
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class Config:
    """Central configuration with Render.com optimization"""
    
    # Required (auto-loaded from Render/GitHub secrets)
    TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]  # Will fail fast if missing
    APP_URL = os.getenv("APP_URL", "")
    WEBHOOK_PATH = "/webhook/telegram"
    
    # Channel system (using your @atheraber)
    CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "atheraber").lstrip("@")
    CHANNEL_LINK = f"https://t.me/{CHANNEL_USERNAME}" if CHANNEL_USERNAME else None
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    TEMP_DIR = BASE_DIR / "temp"
    DOWNLOAD_DIR = BASE_DIR / "downloads"
    
    # Download settings
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    @classmethod
    def validate(cls):
        """Strict validation for production"""
        cls.TEMP_DIR.mkdir(exist_ok=True, parents=True)
        cls.DOWNLOAD_DIR.mkdir(exist_ok=True, parents=True)
        
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        
        logger.info(f"Bot configured for channel: {cls.CHANNEL_LINK or 'None'}")

# Validate immediately on import
Config.validate()
