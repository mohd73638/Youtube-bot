import yt_dlp
import logging
from typing import Tuple, Optional
from config import Config

logger = logging.getLogger(__name__)

class VideoDownloader:
    """Enhanced downloader with error handling"""
    
    @staticmethod
    def download_video(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Download with platform optimization"""
        try:
            ydl_opts = {
                "format": "best[filesize<50M]",
                "outtmpl": str(Config.TEMP_DIR / "%(title)s.%(ext)s"),
                "max_filesize": Config.MAX_FILE_SIZE,
                "quiet": True,
                "no_warnings": True,
                "logger": logger
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                return (
                    ydl.prepare_filename(info),
                    info.get("title", "video")[:200]
                )
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            
        return None, None
