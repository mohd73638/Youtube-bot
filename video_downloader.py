import logging
import yt_dlp
from typing import Tuple, Optional
from config import Config
from utils import cleanup_file

logger = logging.getLogger(__name__)

class VideoDownloader:
    @staticmethod
    def get_video_info(url: str) -> Optional[dict]:
        """Fetch video metadata or return None if failed."""
        try:
            with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to fetch info for {url}: {str(e)}")
            return None

    @staticmethod
    def download_video(url: str, max_size: int = 50*1024*1024) -> Tuple[Optional[str], Optional[str]]:
        """Download video with error handling."""
        try:
            ydl_opts = {
                "format": "best[filesize<50M]",
                "outtmpl": "%(title)s.%(ext)s",
                "max_filesize": max_size,
                "quiet": True,
                "logger": logger  # Redirect yt-dlp logs to your logger
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                logger.info(f"Downloaded: {file_path}")
                return file_path, info.get("title", "video")
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download failed (invalid URL/network): {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
        return None, None
