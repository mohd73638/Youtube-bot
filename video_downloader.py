import os
import yt_dlp
import logging
from config import YT_DLP_OPTIONS, MAX_FILE_SIZE, DOWNLOAD_DIR
from utils import cleanup_file, format_file_size, sanitize_filename, ensure_download_dir

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        ensure_download_dir()
        
        # Download options with anti-bot measures
        self.ydl_opts = {
             format :  best[height<=720] ,  # Max 720p quality
             outtmpl : os.path.join(DOWNLOAD_DIR,  %(title)s.%(ext)s ),
             no_warnings : False,
             extract_flat : False,
             writethumbnail : False,
             writeinfojson : False,
             writesubtitles : False,
             writeautomaticsub : False,
             ignoreerrors : True,
             no_color : True,
             socket_timeout : 30,
             retries : 3,
             fragment_retries : 3,
             http_chunk_size : 10485760,  # 10MB chunks
            # Anti-bot detection measures
             user_agent :  Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 ,
             sleep_interval : 1,
             max_sleep_interval : 5,
             sleep_interval_requests : 1,
             extractor_retries : 3,
             playlist_items :  1 ,
        }

    def download(self, url):
        """Alias for download_video method for backward compatibility"""
        try:
            result = self.download_video(url)
            if isinstance(result, dict):
                # Return format expected by current code
                if result.get( success ):
                    return True, result.get( file_path )
                else:
                    return False, result.get( error ,  Download failed )
            else:
                # Handle tuple format from deployed code
                return result
        except Exception as e:
            return False, str(e)

    def download_video(self, url, user_id=None):
        """
        Download video from URL and return file path.
        Returns: (success: bool, file_path: str, error_message: str, video_info: dict)
        """
        try:
            # Create user-specific subdirectory
            user_dir = os.path.join(DOWNLOAD_DIR, str(user_id) if user_id else "temp")
            os.makedirs(user_dir, exist_ok=True)

            # Configure yt-dlp options for this download
            ydl_opts = self.ydl_opts.copy()
            output_template = os.path.join(user_dir, "%(title)s.%(ext)s")
            ydl_opts["outtmpl"] = output_template

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
            
            # Check file size
            file_size = os.path.getsize(downloaded_file)
            if file_size > MAX_FILE_SIZE:
                cleanup_file(downloaded_file)
                return False, None, "حجم الملف أكبر من الحد المسموح به.", info

            return True, downloaded_file, None, info

        except Exception as e:
            logger.error(f"خطأ أثناء التحميل: {e}")
            return False, None, str(e), None
