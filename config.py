
import logging
import os
import yt_dlp
from typing import Tuple, Optional, Dict
from pathlib import Path
from config import Config
from utils import cleanup_file
import time

logger = logging.getLogger(__name__)

class VideoDownloader:
    @staticmethod
    def get_video_info(url: str) -> Optional[dict]:
        """Fetch video metadata with enhanced error handling."""
        try:
            with yt_dlp.YoutubeDL({
                "quiet": True,
                "no_warnings": True,
                "logger": logger
            }) as ydl:
                start_time = time.time()
                info = ydl.extract_info(url, download=False)
                logger.info(f"Fetched metadata in {time.time()-start_time:.2f}s")
                return info
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Metadata fetch failed (invalid URL): {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected metadata error: {str(e)}")
        return None

    @staticmethod
    def download_video(url: str, max_size: int = 50*1024*1024) -> Tuple[Optional[str], Optional[str]]:
        """Download video with temp file handling and progress tracking."""
        temp_file = None
        try:
            # Prepare download directory
            download_dir = Config.get_temp_dir()
            os.makedirs(download_dir, exist_ok=True)
            
            ydl_opts = {
                "format": "best[filesize<50M]",
                "outtmpl": os.path.join(download_dir, "%(title)s.%(ext)s"),
                "max_filesize": max_size,
                "quiet": True,
                "logger": logger,
                "noprogress": False,
                "progress_hooks": [VideoDownloader._progress_hook],
                "postprocessor_hooks": [VideoDownloader._postprocess_hook]
            }
            
            start_time = time.time()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = ydl.prepare_filename(info)
                
                # Verify download completed
                if not os.path.exists(file_path):
                    raise FileNotFoundError("Downloaded file not found")
                
                logger.info(f"Download completed in {time.time()-start_time:.2f}s")
                return file_path, info.get("title", "Untitled")
                
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download failed: {str(e)}")
        except Exception as e:
            logger.error(f"Download error: {str(e)}")
            if temp_file and os.path.exists(temp_file):
                cleanup_file(temp_file)
        return None, None

    @staticmethod
    def _progress_hook(d: Dict) -> None:
        """Handle download progress updates."""
        if d[ status ] ==  downloading :
            percent = d.get( _percent_str , "?")
            speed = d.get( _speed_str , "?")
            logger.debug(f"Downloading: {percent} at {speed}")

    @staticmethod
    def _postprocess_hook(d: Dict) -> None:
        """Handle post-processing events."""
        if d[ status ] ==  finished :
            logger.debug("Post-processing completed")
