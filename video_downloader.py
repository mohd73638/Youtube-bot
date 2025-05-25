import os
import yt_dlp
import logging
import tempfile
from config import YT_DLP_OPTIONS, MAX_FILE_SIZE, DOWNLOAD_DIR
from utils import cleanup_file, format_file_size, sanitize_filename, ensure_download_dir

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        ensure_download_dir()
        
    def download_video(self, url, user_id=None):
        """
        Download video from URL and return file path
        Returns: (success: bool, file_path: str, error_message: str, video_info: dict)
        """
        try:
            # Create user-specific subdirectory
            user_dir = os.path.join(DOWNLOAD_DIR, str(user_id) if user_id else 'temp')
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
                
            # Configure yt-dlp options for this download
            ydl_opts = YT_DLP_OPTIONS.copy()
            ydl_opts['outtmpl'] = os.path.join(user_dir, '%(title)s.%(ext)s')
            
            # Add progress hook
            downloaded_file = None
            
            def progress_hook(d):
                nonlocal downloaded_file
                if d['status'] == 'finished':
                    downloaded_file = d['filename']
                    logger.info(f"Download finished: {downloaded_file}")
                elif d['status'] == 'error':
                    logger.error(f"Download error: {d}")
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info first
                logger.info(f"Extracting info for URL: {url}")
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return False, None, "Could not extract video information", None
                
                # Check file size before downloading
                filesize = info.get('filesize') or info.get('filesize_approx', 0)
                if filesize and filesize > MAX_FILE_SIZE:
                    size_mb = filesize / (1024 * 1024)
                    return False, None, f"Video too large ({size_mb:.1f}MB). Maximum allowed size is {MAX_FILE_SIZE / (1024 * 1024)}MB", None
                
                # Check duration
                duration = info.get('duration', 0)
                if duration and duration > 600:  # 10 minutes
                    return False, None, f"Video too long ({duration//60}:{duration%60:02d}). Maximum allowed duration is 10 minutes", None
                
                # Download the video
                logger.info(f"Starting download for: {info.get('title', 'Unknown')}")
                ydl.download([url])
                
                if not downloaded_file or not os.path.exists(downloaded_file):
                    return False, None, "Download completed but file not found", None
                
                # Check actual file size
                actual_size = os.path.getsize(downloaded_file)
                if actual_size > MAX_FILE_SIZE:
                    cleanup_file(downloaded_file)
                    return False, None, f"Downloaded file too large ({format_file_size(actual_size)})", None
                
                # Sanitize filename
                dir_name = os.path.dirname(downloaded_file)
                base_name = os.path.basename(downloaded_file)
                sanitized_name = sanitize_filename(base_name)
                
                if sanitized_name != base_name:
                    new_path = os.path.join(dir_name, sanitized_name)
                    os.rename(downloaded_file, new_path)
                    downloaded_file = new_path
                
                video_info = {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'file_size': actual_size,
                    'format': info.get('ext', 'unknown')
                }
                
                logger.info(f"Successfully downloaded: {downloaded_file}")
                return True, downloaded_file, None, video_info
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e)
            logger.error(f"yt-dlp download error: {error_msg}")
            
            # Provide more user-friendly error messages
            if "Private video" in error_msg:
                return False, None, "This video is private and cannot be downloaded", None
            elif "Video unavailable" in error_msg:
                return False, None, "This video is not available for download", None
            elif "Unsupported URL" in error_msg:
                return False, None, "This URL is not supported or the video format is not compatible", None
            else:
                return False, None, f"Download failed: {error_msg}", None
                
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return False, None, f"An unexpected error occurred: {str(e)}", None
    
    def get_video_info(self, url):
        """Get video information without downloading"""
        try:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    return None
                    
                return {
                    'title': info.get('title', 'Unknown'),
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'view_count': info.get('view_count', 0),
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', '')[:200] + '...' if info.get('description', '') else ''
                }
        except Exception as e:
            logger.error(f"Error extracting video info: {e}")
            return None
