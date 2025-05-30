import yt_dlp
import logging
from typing import Tuple, Optional
from pytube import YouTube
from pytube.exceptions import PytubeError
import time
import os
import subprocess
from pathlib import Path
import random

# تحديث yt-dlp تلقائيًا عند التشغيل
subprocess.run(["yt-dlp", "-U"], check=False)
# Assuming Config and get_domain are available
from config import Config
from utils import get_domain # Assuming get_domain is in utils_updated.py

logger = logging.getLogger(__name__)
YOUTUBE_COOKIES = "youtube_cookies.txt"
FACEBOOK_COOKIES = "facebook_cookies.txt"

class VideoDownloader:
    """Enhanced downloader with yt-dlp and pytube fallback for YouTube."""

    @staticmethod
    def _download_with_yt_dlp(url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            ydl_opts = {
                'format': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
                'outtmpl': str(Config.TEMP_DIR / '%(id)s.%(ext)s'),
                'cookiefile': Config.YOUTUBE_COOKIES,
                'ignoreerrors': True,
                'quiet': True,
                'force_ipv4': True,
            }
        
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None, "Failed to extract video info"
            
                filename = ydl.prepare_filename(info)
                if Path(filename).exists():
                    return filename, info.get('title', 'video')
            
            return None, "File not found after download"
        except Exception as e:
            return None, f"yt-dlp error: {str(e)}"
        
    @staticmethod
    def _download_with_pytube(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Attempt YouTube download using pytube as a fallback."""
        try:
            logger.info(f"Attempting YouTube download with pytube for: {url}")
            yt = YouTube(url)
            
            # Filter streams: progressive, mp4, below size limit, order by resolution
            stream = yt.streams.filter(
                progressive=True, 
                file_extension='mp4', 
                res='720p' # Prioritize 720p
            ).order_by('resolution').desc().first()
            
            # Fallback to lower resolutions if 720p not found or too large
            if not stream or (stream.filesize and stream.filesize > Config.MAX_FILE_SIZE):
                 stream = yt.streams.filter(
                     progressive=True, 
                     file_extension='mp4'
                 ).order_by('resolution').desc().last() # Get lowest available progressive mp4

            # Final check if a suitable stream was found and within size limits
            if stream and stream.filesize <= Config.MAX_FILE_SIZE:
                logger.info(f"Found suitable pytube stream: resolution={stream.resolution}, size={stream.filesize}")
                # Generate a unique filename
                filename = f"{yt.video_id}_{int(time.time())}.mp4"
                output_path = str(Config.TEMP_DIR)
                logger.info(f"Starting pytube download to {output_path} as {filename}")
                downloaded_path = stream.download(output_path=output_path, filename=filename)
                logger.info(f"pytube download successful: {downloaded_path}")
                return downloaded_path, yt.title[:200]
            elif stream:
                logger.warning(f"No suitable pytube stream found below size limit for {url}. Smallest progressive mp4 size: {stream.filesize}")
                return None, f"Video too large (>{Config.MAX_FILE_SIZE // 1024 // 1024}MB)"
            else:
                logger.warning(f"No progressive mp4 streams found by pytube for {url}")
                return None, "No suitable download format found (pytube)."

        except PytubeError as e:
            logger.error(f"Pytube download failed for {url}: {e}")
            return None, f"Pytube Error: {str(e)[:100]}"
        except Exception as e:
            logger.error(f"Unexpected error during pytube download for {url}: {e}", exc_info=True)
            return None, f"Unexpected Pytube Error: {str(e)[:100]}"

    @staticmethod
    def _download_facebook(url: str) -> Tuple[Optional[str], Optional[str]]:
        try:
            ydl_opts = {
                'format': 'best',
                'outtmpl': str(Config.TEMP_DIR / '%(id)s.%(ext)s'),
                'cookiefile': Config.FACEBOOK_COOKIES,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36'
                },
                'force_ipv4': True,
                'extract_flat': True
            }
        
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info) 
                return filename, info.get('title', 'video')
            
        except Exception as e:
            return None, f"Facebook Error: {str(e)}"
    
   
    @staticmethod
    def download_video(url: str) -> Tuple[Optional[str], Optional[str]]:
        # تحديد نوع الرابط
        if "youtube.com" in url or "youtu.be" in url:
            return VideoDownloader._download_with_yt_dlp(url)
        elif "facebook.com" in url:
            return VideoDownloader._download_facebook(url)
        else:
            return None, "Unsupported website"

    @staticmethod
    def _is_youtube_url(url: str) -> bool:
        """Check if URL is from any YouTube domain."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(domain.endswith(d) for d in [".youtube.com", ".youtu.be", ".youtube-nocookie.com"])

    @staticmethod
    def _cleanup_file(file_path: Optional[str]): 
        """Delete partially downloaded files on failure."""
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path) 
                logger.info(f"Cleaned up file: {file_path}")
            except Exception as e:
                logger.error(f"Failed to cleanup {file_path}: {e}")

    @staticmethod
    def _format_errors(primary_err: str, fallback_err: str) -> str:
        """Combine errors without duplicates."""
        if not fallback_err or fallback_err == primary_err:
            return primary_err
        return f"yt-dlp: {primary_err} | pytube: {fallback_err}"
