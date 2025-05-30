import yt_dlp
import logging
from typing import Tuple, Optional, List
from pytube import YouTube
from pytube.exceptions import PytubeError
import time
import os
import subprocess
from pathlib import Path
import random
from datetime import datetime, timedelta

# Auto-update yt-dlp
subprocess.run(["yt-dlp", "-U"], check=False)

# Import config
from config import Config
from utils import get_domain

logger = logging.getLogger(__name__)

class VideoDownloader:
    """Enhanced video downloader with yt-dlp and fallback support."""
    
    # User agents for rotation
    _USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
    ]

    @classmethod
    def initialize(cls):
        """Initialize downloader setup."""
        Path(Config.TEMP_DIR).mkdir(exist_ok=True)
        cls._check_cookies()
        cls.cleanup_old_files()

    @classmethod
    def _random_user_agent(cls) -> str:
        """Get a random user agent."""
        return random.choice(cls._USER_AGENTS)

    @staticmethod
    def _check_cookies():
        """Verify required cookies files exist."""
        if Config.YOUTUBE_COOKIES and not Path(Config.YOUTUBE_COOKIES).exists():
            logger.warning("YouTube cookies file missing!")
        if Config.FACEBOOK_COOKIES and not Path(Config.FACEBOOK_COOKIES).exists():
            logger.warning("Facebook cookies file missing!")

    @staticmethod
    def cleanup_old_files(days: int = 1):
        """Clean up files older than specified days."""
        now = time.time()
        for f in Config.TEMP_DIR.glob('*'):
            if f.is_file() and (now - f.stat().st_mtime) > (days * 86400):
                try:
                    f.unlink()
                    logger.info(f"Cleaned up old file: {f.name}")
                except Exception as e:
                    logger.error(f"Failed to clean {f.name}: {e}")


    @staticmethod
    def _download_with_yt_dlp(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Download using yt-dlp with enhanced options for YouTube and other supported sites."""
        try:
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]/best[height<=720]',
                'outtmpl': str(Config.TEMP_DIR / '%(id)s.%(ext)s'),
                'cookiefile': Config.YOUTUBE_COOKIES,
                'ignoreerrors': True,
                'quiet': False,
                'no_warnings': False,
                'verbose': True,
                'force_ipv4': True,
                'retries': 3,
                'socket_timeout': 30,
                'extract_flat': False,
                'extractor_args': {
                    'youtube': ['player_client=web']  # Fix for 400 error on YouTube
                },
                'http_headers': {
                'User-Agent': VideoDownloader._random_user_agent()
                }
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None, "Failed to extract video info"

                filename = ydl.prepare_filename(info)
                if not Path(filename).exists():
                    for f in Config.TEMP_DIR.glob(f"*{info.get('id', '')}*"):
                        filename = str(f)
                        break

                if Path(filename).exists():
                    return filename, info.get('title', 'video')[:200]

            return None, "Downloaded file not found"

        except Exception as e:
            return None, f"yt-dlp error: {str(e)}"
    
    @staticmethod
    def _download_with_pytube(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fallback YouTube downloader using pytube."""
        try:
            yt = YouTube(
                url,
                on_progress_callback=lambda *args: logger.debug("Download progress: %s", args),
                on_complete_callback=lambda *args: logger.debug("Download complete: %s", args)
            )
            
            stream = yt.streams.filter(
                progressive=True,
                file_extension='mp4'
            ).order_by('resolution').desc().first()
            
            if not stream:
                return None, "No suitable streams available"
                
            if stream.filesize > Config.MAX_FILE_SIZE:
                return None, f"Video too large ({stream.filesize//(1024*1024)}MB)"
                
            filename = f"{yt.video_id}_{int(time.time())}.mp4"
            downloaded_path = stream.download(
                output_path=str(Config.TEMP_DIR),
                filename=filename
            )
            
            return downloaded_path, yt.title[:200]
            
        except PytubeError as e:
            return None, f"Pytube Error: {str(e)[:100]}"
        except Exception as e:
            return None, f"Unexpected Pytube Error: {str(e)[:100]}"

    @staticmethod
    def _download_facebook(url: str, retries: int = 2) -> Tuple[Optional[str], Optional[str]]:
        """Facebook video downloader with retry support."""
        last_error = None
        
        for attempt in range(retries):
            try:
                ydl_opts = {
                    'format': 'best',
                    'outtmpl': str(Config.TEMP_DIR / '%(id)s.%(ext)s'),
                    'cookiefile': Config.FACEBOOK_COOKIES,
                    'http_headers': {
                        'User-Agent': VideoDownloader._random_user_agent(),
                        'Accept-Language': 'en-US,en;q=0.9'
                    },
                    'force_ipv4': True,
                    'extract_flat': False,
                    'retries': 3,
                    'socket_timeout': 30
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    if not info:
                        raise ValueError("No video info extracted")
                    
                    filename = ydl.prepare_filename(info)
                    if not Path(filename).exists():
                        for f in Config.TEMP_DIR.glob(f"*{info.get('id', '')}*"):
                            filename = str(f)
                            break
                    
                    if Path(filename).exists():
                        return filename, info.get('title', 'video')[:200]
                    
                return None, "Downloaded file not found"
                
            except Exception as e:
                last_error = str(e)
                if attempt < retries - 1:
                    time.sleep(3)
        
        return None, last_error or "Facebook download failed"

     
    @staticmethod
    def download_video(url: str, max_retries: int = 2) -> Tuple[Optional[str], Optional[str]]:
        """Main download method with retry logic."""
        VideoDownloader.initialize()
        last_error = None

        for attempt in range(max_retries):
            try:
                if "youtube.com" in url or "youtu.be" in url:
                    result = VideoDownloader._download_with_yt_dlp(url)
                    if result[0]:
                        return result

                    if attempt == max_retries - 1:
                        logger.warning("Falling back to pytube")
                        result = VideoDownloader._download_with_pytube(url)
                        if result[0]:
                            return result

                elif "facebook.com" in url or "fb.watch" in url:
                    result = VideoDownloader._download_facebook(url)
                    if result[0]:
                        return result

                elif "instagram.com" in url:
                    return None, "❌ Instagram is no longer supported by yt-dlp."

                else:
                    return None, "❌ Unsupported website"

            except Exception as e:
                last_error = str(e)
                logger.error(f"Attempt {attempt+1} failed: {last_error}")
                time.sleep(2 ** attempt)

            VideoDownloader.cleanup_old_files(days=0)

        return None, last_error or "All download attempts failed"
    

    @staticmethod
    def _cleanup_file(file_path: Optional[str]):
        """Clean up downloaded files and temp files."""
        if not file_path:
            return
            
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
                
            # Clean temp files with same stem
            for temp_file in path.parent.glob(f"*{path.stem}*"):
                if temp_file != path and temp_file.exists():
                    temp_file.unlink()
        except Exception as e:
            logger.error(f"Cleanup failed for {file_path}: {e}")

# Initialize on import
VideoDownloader.initialize()
