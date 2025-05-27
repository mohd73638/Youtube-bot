import os
import logging
import requests
import tempfile
import time
from datetime import datetime
from config import Config
from video_downloader import VideoDownloader
from utils import is_valid_url, format_file_size, clean_filename
from database import DatabaseManager
from models import db

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = Config.BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.token}"
        self.video_downloader = VideoDownloader()
        
        if not self.token:
            raise ValueError("BOT_TOKEN not found in environment variables")
    
    def send_message(self, chat_id, text, parse_mode=None, reply_to_message_id=None):
        """Send a text message to a chat"""
        try:
            data = {
                'chat_id': chat_id,
                'text': text
            }
            
            if parse_mode:
                data['parse_mode'] = parse_mode
            
            if reply_to_message_id:
                data['reply_to_message_id'] = reply_to_message_id
            
            response = requests.post(f"{self.api_url}/sendMessage", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}")
            return None
    
    def send_video(self, chat_id, video_path, caption=None, reply_to_message_id=None):
        """Send a video file to a chat"""
        try:
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                data = {'chat_id': chat_id}
                
                if caption:
                    data['caption'] = caption
                
                if reply_to_message_id:
                    data['reply_to_message_id'] = reply_to_message_id
                
                response = requests.post(f"{self.api_url}/sendVideo", files=files, data=data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error sending video: {str(e)}")
            return None
    
    def send_document(self, chat_id, document_path, caption=None, reply_to_message_id=None):
        """Send a document to a chat"""
        try:
            with open(document_path, 'rb') as doc_file:
                files = {'document': doc_file}
                data = {'chat_id': chat_id}
                
                if caption:
                    data['caption'] = caption
                
                if reply_to_message_id:
                    data['reply_to_message_id'] = reply_to_message_id
                
                response = requests.post(f"{self.api_url}/sendDocument", files=files, data=data)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Error sending document: {str(e)}")
            return None
    
    def send_chat_action(self, chat_id, action):
        """Send chat action (typing, uploading, etc.)"""
        try:
            data = {
                'chat_id': chat_id,
                'action': action
            }
            response = requests.post(f"{self.api_url}/sendChatAction", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error sending chat action: {str(e)}")
            return None
    
    def set_webhook(self, webhook_url):
        """Set webhook URL"""
        try:
            data = {'url': webhook_url}
            response = requests.post(f"{self.api_url}/setWebhook", json=data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error setting webhook: {str(e)}")
            return None
    
    def get_webhook_info(self):
        """Get webhook information"""
        try:
            response = requests.get(f"{self.api_url}/getWebhookInfo")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error getting webhook info: {str(e)}")
            return None
    
    def process_update(self, update):
        """Process incoming update from Telegram"""
        try:
            if 'message' not in update:
                logger.warning("No message in update")
                return None
            
            message = update['message']
            chat_id = message['chat']['id']
            
            # Track user activity in database
            if 'from' in message:
                user_data = message['from']
                DatabaseManager.get_or_create_user(user_data)
            
            # Handle different message types
            if 'text' in message:
                return self.handle_text_message(message)
            elif 'photo' in message or 'video' in message or 'document' in message:
                return self.handle_media_message(message)
            else:
                self.send_message(chat_id, "I can only process text messages and URLs. Please send me a video URL to download!")
                return "Media message not supported"
        
        except Exception as e:
            logger.error(f"Error processing update: {str(e)}")
            return None
    
    def handle_text_message(self, message):
        """Handle text messages"""
        try:
            chat_id = message['chat']['id']
            text = message['text']
            message_id = message['message_id']
            user = message.get('from', {})
            username = user.get('username', user.get('first_name', 'User'))
            
            logger.info(f"Received message from {username}: {text}")
            
            # Handle commands
            if text.startswith('/start'):
                welcome_text = f"""
🤖 *Welcome to YouTube Video Downloader Bot!*

Hello {username}! I can help you download videos from various platforms.

*How to use:*
📹 Send me any video URL (YouTube, Instagram, TikTok, etc.)
⬇️ I'll download it and send it back to you

*Supported platforms:*
• YouTube
• Instagram
• TikTok
• Twitter
• Facebook
• And many more!

*Commands:*
/help - Show this help message
/start - Start the bot

Just send me a video URL and I'll get to work! 🚀
                """
                self.send_message(chat_id, welcome_text, parse_mode='Markdown')
                return "Welcome message sent"
            
            elif text.startswith('/help'):
                help_text = """
🆘 *Help - YouTube Video Downloader Bot*

*How to download videos:*
1. Copy a video URL from any supported platform
2. Send it to me in this chat
3. Wait for me to process and download it
4. Receive your video file!

*Supported platforms:*
• YouTube (youtube.com, youtu.be)
• Instagram (instagram.com)
• TikTok (tiktok.com)
• Twitter (twitter.com, x.com)
• Facebook (facebook.com)
• And many more!

*Tips:*
• I can handle most video URLs
• Large files might take a bit longer
• Some platforms have download restrictions

Need more help? Just send me a video URL to try it out! 😊
                """
                self.send_message(chat_id, help_text, parse_mode='Markdown')
                return "Help message sent"
            
            # Check if message contains a URL
            elif is_valid_url(text):
                # Create download record in database
                download_record = DatabaseManager.create_download_record(chat_id, text)
                return self.download_and_send_video(chat_id, text, message_id, username, download_record)
            
            else:
                self.send_message(
                    chat_id, 
                    "Please send me a valid video URL! 🔗\n\nSupported platforms: YouTube, Instagram, TikTok, Twitter, Facebook, and many more.\n\nUse /help for more information.",
                    reply_to_message_id=message_id
                )
                return "Invalid URL message sent"
        
        except Exception as e:
            logger.error(f"Error handling text message: {str(e)}")
            return None
    
    def handle_media_message(self, message):
        """Handle media messages"""
        chat_id = message['chat']['id']
        self.send_message(chat_id, "I can process video URLs! Please send me a text message with a video URL to download.")
        return "Media message handled"
    
    def download_and_send_video(self, chat_id, url, message_id, username, download_record=None):
        """Download video and send to user"""
        start_time = time.time()
        
        try:
            # Update download status to processing
            if download_record:
                DatabaseManager.update_download_status(download_record.id, 'processing')
            
            # Send "uploading video" action
            self.send_chat_action(chat_id, 'upload_video')
            
            # Send processing message
            processing_msg = self.send_message(
                chat_id, 
                "🔄 Processing your video... This might take a moment!",
                reply_to_message_id=message_id
            )
            
            # Download the video
            logger.info(f"Starting download for {username}: {url}")
            result = self.video_downloader.download(url)
            
            if result['success']:
                file_path = result['file_path']
                title = result.get('title', 'Downloaded Video')
                duration = result.get('duration', 'Unknown')
                file_size = result.get('file_size', 0)
                uploader = result.get('uploader', 'Unknown')
                
                # Update download record with video info
                if download_record:
                    DatabaseManager.update_download_status(
                        download_record.id, 
                        'completed',
                        file_size=file_size,
                        download_time=time.time() - start_time
                    )
                
                # Prepare caption
                caption = f"🎬 *{title}*\n"
                if duration != 'Unknown':
                    caption += f"⏱ Duration: {duration}\n"
                caption += f"📁 Size: {format_file_size(file_size)}\n"
                if uploader != 'Unknown':
                    caption += f"📺 Channel: {uploader}\n"
                caption += f"👤 Requested by: {username}"
                
                # Send the video
                self.send_chat_action(chat_id, 'upload_video')
                
                # Check file size (Telegram limit is 50MB for videos)
                if file_size > 50 * 1024 * 1024:  # 50MB
                    # Send as document if too large
                    sent = self.send_document(
                        chat_id, 
                        file_path, 
                        caption=caption + "\n\n📎 Sent as document due to size limit",
                        reply_to_message_id=message_id
                    )
                else:
                    # Send as video
                    sent = self.send_video(
                        chat_id, 
                        file_path, 
                        caption=caption,
                        reply_to_message_id=message_id
                    )
                
                if sent:
                    success_msg = "✅ Video downloaded and sent successfully!"
                    logger.info(f"Video sent successfully to {username}")
                    
                    # Update daily stats
                    DatabaseManager.update_daily_stats()
                else:
                    success_msg = "❌ Failed to send video. The file might be too large or corrupted."
                    logger.error(f"Failed to send video to {username}")
                    
                    # Mark as failed in database
                    if download_record:
                        DatabaseManager.update_download_status(
                            download_record.id, 
                            'failed',
                            error_message="Failed to send video to user"
                        )
                
                # Clean up
                try:
                    os.unlink(file_path)
                    logger.info(f"Cleaned up file: {file_path}")
                except:
                    pass
                
                return success_msg
            
            else:
                error_msg = f"❌ Failed to download video: {result.get('error', 'Unknown error')}"
                self.send_message(chat_id, error_msg, reply_to_message_id=message_id)
                logger.error(f"Download failed for {username}: {result.get('error')}")
                
                # Update download record as failed
                if download_record:
                    DatabaseManager.update_download_status(
                        download_record.id, 
                        'failed',
                        error_message=result.get('error', 'Unknown error'),
                        download_time=time.time() - start_time
                    )
                
                return error_msg
        
        except Exception as e:
            error_msg = f"❌ An error occurred while processing your request: {str(e)}"
            self.send_message(chat_id, error_msg, reply_to_message_id=message_id)
            logger.error(f"Error in download_and_send_video: {str(e)}")
            
            # Update download record as failed
            if download_record:
                DatabaseManager.update_download_status(
                    download_record.id, 
                    'failed',
                    error_message=str(e),
                    download_time=time.time() - start_time
                )
            
            return error_msg
