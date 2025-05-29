import os
import yt_dlp
import logging
from config import Config
from utils import cleanup_file, format_file_size, sanitize_filename, ensure_download_dir
from typing import Tuple

logger = logging.getLogger(__name__)

from config import Config
    Config.validate()  # Ensure config is loaded
  
class VideoDownloader:
def __init__(self):
          self.options = Config.YT_DLP_OPTIONS

    @staticmethod
    def get_video_info(url: str) -> dict:
        """Get video metadata without downloading"""
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            return ydl.extract_info(url, download=False)

    @staticmethod
    def download_video(url: str, max_size: int = 50*1024*1024) -> Tuple[str, str]:
        """
        Downloads video and returns (file_path, title)
        Handles YouTube, TikTok, Instagram, Twitter, etc.
        """
        ydl_opts = {
            'format': 'best[filesize<50M]',
            'outtmpl': '%(title)s.%(ext)s',
            'max_filesize': max_size,
            'merge_output_format': 'mp4'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info), info.get('title', 'video')
