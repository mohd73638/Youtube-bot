import os
import yt_dlp
import logging
from config import YT_DLP_OPTIONS, MAX_FILE_SIZE, DOWNLOAD_DIR
from utils import cleanup_file, format_file_size, sanitize_filename, ensure_download_dir

logger = logging.getLogger(__name__)

class VideoDownloader:
    def __init__(self):
        ensure_download_dir()

    
    def download(self, url):
    """Alias for download_video method for backward compatibility"""
    try:
        success, file_path, error_msg, info = self.download_video(url)
        if success:
            return { success : True,  file_path : file_path,  title : info.get( title ) if info else None}
        else:
            return { success : False,  error : error_msg}
    except Exception as e:
        return { success : False,  error : str(e)}

    
    def download_video(self, url, user_id=None):
        """
        Download video from URL and return file path.
        Returns: (success: bool, file_path: str, error_message: str, video_info: dict)
        """
        try:
            user_dir = os.path.join(DOWNLOAD_DIR, str(user_id) if user_id else "temp")
            os.makedirs(user_dir, exist_ok=True)

            ydl_opts = YT_DLP_OPTIONS.copy()
            output_template = os.path.join(user_dir, "%(title)s.%(ext)s")
            ydl_opts["outtmpl"] = output_template

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
            
            file_size = os.path.getsize(downloaded_file)
            if file_size > MAX_FILE_SIZE:
                cleanup_file(downloaded_file)
                return False, None, "حجم الملف أكبر من الحد المسموح به.", info

            return True, downloaded_file, None, info

        except Exception as e:
            logger.error(f"خطأ أثناء التحميل: {e}")
            return False, None, str(e), None
