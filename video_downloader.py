import yt_dlp
import logging
from typing import Tuple, Optional
from pytube import YouTube
from pytube.exceptions import PytubeError
import time
import os

# Assuming Config and get_domain are available
from config import Config
from utils import get_domain # Assuming get_domain is in utils_updated.py

logger = logging.getLogger(__name__)

class VideoDownloader:
    """Enhanced downloader with yt-dlp and pytube fallback for YouTube."""

    @staticmethod
    def _download_with_yt_dlp(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Attempt download using yt-dlp with optimized options."""
        try:
            # More robust options: prefer mp4, limit filesize, handle cookies if needed
            ydl_opts = {
                # Prefer mp4 format, fallback to best video + best audio
                # Use 'bv*+ba' for potentially better quality but separate files initially
                # Using 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' is common
                # Simpler: 'best[ext=mp4][filesize<50M]/best[filesize<50M]'
                "format": f"bestvideo[ext=mp4][filesize<?{Config.MAX_FILE_SIZE}]+bestaudio[ext=m4a]/best[ext=mp4][filesize<?{Config.MAX_FILE_SIZE}]/best[filesize<?{Config.MAX_FILE_SIZE}]",
                "outtmpl": str(Config.TEMP_DIR / "%(id)s_%(epoch)s.%(ext)s"), # Use epoch for uniqueness
                "max_filesize": Config.MAX_FILE_SIZE,
                "quiet": True,
                "no_warnings": True,
                "logger": logger,
                "noprogress": True,
                "noplaylist": True, # Download single video even if part of playlist
                # Consider adding cookiefile if login is needed for some sites
                # "cookiefile": "path/to/cookies.txt", 
                # Force IPv4 if IPv6 causes issues
                # "source_address": "0.0.0.0", 
            }
            logger.info(f"Attempting download with yt-dlp for: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Use download=False first to check info without downloading immediately
                info = ydl.extract_info(url, download=False)
                
                # Check if filesize is available and within limits before download
                filesize = info.get("filesize") or info.get("filesize_approx")
                if filesize and filesize > Config.MAX_FILE_SIZE:
                    logger.warning(f"Video filesize ({filesize}) exceeds limit ({Config.MAX_FILE_SIZE}) for {url}")
                    # Optionally, try to find a smaller format if needed, but format selection handles this
                    # return None, f"Video too large (>{Config.MAX_FILE_SIZE // 1024 // 1024}MB)"
                    # Let format selection handle it, but log the warning

                # Proceed with download using the selected format
                logger.info(f"Starting yt-dlp download for {url}")
                ydl.download([url])
                # Construct filename based on template and info
                # Note: ydl.prepare_filename might not work as expected after download=True
                # We need to find the actual downloaded file based on the template pattern
                downloaded_file = None
                for filename in os.listdir(Config.TEMP_DIR):
                     # Match based on video ID and epoch timestamp in the filename template
                     if info.get("id") in filename and str(info.get("epoch")) in filename:
                          downloaded_file = str(Config.TEMP_DIR / filename)
                          break
                
                if downloaded_file:
                    logger.info(f"yt-dlp download successful: {downloaded_file}")
                    return downloaded_file, info.get("title", "video")[:200]
                else:
                    logger.error(f"yt-dlp downloaded but file not found for {url}. Template: {ydl_opts['outtmpl']}")
                    return None, "Download completed but file not found."

        except yt_dlp.utils.DownloadError as e:
            # Log specific yt-dlp errors
            error_msg = str(e)
            logger.warning(f"yt-dlp download failed for {url}: {error_msg}")
            # Return specific error messages for common issues if possible
            if "Video unavailable" in error_msg or "Private video" in error_msg:
                return None, "Video unavailable or private."
            if "age restricted" in error_msg.lower():
                return None, "Video is age-restricted."
            # Generic yt-dlp error
            return None, f"yt-dlp Error: {error_msg[:100]}"
        except Exception as e:
            logger.error(f"Unexpected error during yt-dlp download for {url}: {e}", exc_info=True)
            return None, f"Unexpected yt-dlp Error: {str(e)[:100]}"

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
    def download_video(url: str) -> Tuple[Optional[str], Optional[str]]:
        """Main download function trying yt-dlp first, then pytube for YouTube."""
        file_path, title_or_error = VideoDownloader._download_with_yt_dlp(url)

        # If yt-dlp fails and it's a YouTube link, try pytube
        if file_path is None and get_domain(url) in ["youtube.com", "youtu.be"]:
            logger.warning(f"yt-dlp failed for YouTube URL ({url}). Trying pytube fallback...")
            # Keep the original error message from yt-dlp unless pytube succeeds or gives a different error
            pytube_file_path, pytube_title_or_error = VideoDownloader._download_with_pytube(url)
            if pytube_file_path:
                return pytube_file_path, pytube_title_or_error # Pytube succeeded
            else:
                # Pytube also failed, return its error message if it's different/more specific
                if pytube_title_or_error and pytube_title_or_error != title_or_error:
                     return None, pytube_title_or_error
                else:
                     # Return the original yt-dlp error if pytube didn't add info
                     return None, title_or_error 
        
        # Return yt-dlp result (success or failure for non-YouTube URLs)
        return file_path, title_or_error

