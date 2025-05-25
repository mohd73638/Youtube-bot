import os
import logging
import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import tempfile
import shutil

from config import BOT_TOKEN, setup_logging
from video_downloader import VideoDownloader
from utils import is_supported_url, get_platform_name, cleanup_file, format_file_size

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

class TelegramVideoBot:
    def __init__(self):
        self.downloader = VideoDownloader()
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🎥 **Video Downloader Bot** 🎥

Welcome! I can help you download videos from:
• YouTube
• Instagram  
• Facebook

**How to use:**
1. Send me a video URL from any supported platform
2. I'll download and send it back to you

**Commands:**
/start - Show this welcome message
/help - Show help information

**Supported platforms:**
✅ YouTube (youtube.com, youtu.be)
✅ Instagram (instagram.com)
✅ Facebook (facebook.com, fb.watch)

Just send me a video URL to get started! 🚀
        """
        await update.message.reply_text(welcome_message, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🆘 **Help & Information** 🆘

**How to download videos:**
1. Copy a video URL from YouTube, Instagram, or Facebook
2. Send the URL to this bot
3. Wait for the download to complete
4. Receive your video file!

**Limitations:**
• Maximum file size: 50MB
• Maximum duration: 10 minutes
• Only public videos can be downloaded

**Supported URL formats:**
• https://www.youtube.com/watch?v=...
• https://youtu.be/...
• https://www.instagram.com/p/...
• https://www.facebook.com/watch?v=...
• https://fb.watch/...

**Troubleshooting:**
• Make sure the video is public
• Check if the URL is correct
• Try again if the download fails

For technical issues, the video might be:
- Private or restricted
- Too large (>50MB)
- Too long (>10 minutes)
- In an unsupported format

Happy downloading! 🎬
        """
        await update.message.reply_text(help_message, parse_mode='Markdown')
    
    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle video URL messages"""
        url = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Check if URL is supported
        if not is_supported_url(url):
            await update.message.reply_text(
                "❌ **Unsupported URL**\n\n"
                "I can only download videos from:\n"
                "• YouTube (youtube.com, youtu.be)\n"
                "• Instagram (instagram.com)\n"
                "• Facebook (facebook.com, fb.watch)\n\n"
                "Please send a valid video URL from one of these platforms.",
                parse_mode='Markdown'
            )
            return
        
        platform = get_platform_name(url)
        
        # Send initial response
        status_message = await update.message.reply_text(
            f"🔍 **Processing {platform} video...**\n\n"
            "⏳ Extracting video information...",
            parse_mode='Markdown'
        )
        
        try:
            # Show typing indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
            
            # Get video info first
            video_info = self.downloader.get_video_info(url)
            
            if video_info:
                duration_str = f"{video_info['duration']//60}:{video_info['duration']%60:02d}" if video_info['duration'] else "Unknown"
                
                await status_message.edit_text(
                    f"📹 **Found {platform} video!**\n\n"
                    f"**Title:** {video_info['title'][:50]}{'...' if len(video_info['title']) > 50 else ''}\n"
                    f"**Duration:** {duration_str}\n"
                    f"**Uploader:** {video_info['uploader']}\n\n"
                    "⬇️ Starting download...",
                    parse_mode='Markdown'
                )
            
            # Show upload indicator
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)
            
            # Download the video
            success, file_path, error_message, download_info = self.downloader.download_video(url, user_id)
            
            if success and file_path:
                # Update status
                await status_message.edit_text(
                    f"📤 **Uploading {platform} video...**\n\n"
                    f"**File size:** {format_file_size(download_info['file_size'])}\n"
                    "Please wait...",
                    parse_mode='Markdown'
                )
                
                # Send the video file
                with open(file_path, 'rb') as video_file:
                    caption = (
                        f"🎥 **{download_info['title'][:50]}{'...' if len(download_info['title']) > 50 else ''}**\n\n"
                        f"📺 Platform: {platform}\n"
                        f"⏱️ Duration: {download_info['duration']//60}:{download_info['duration']%60:02d}\n"
                        f"👤 Uploader: {download_info['uploader']}\n"
                        f"📊 Size: {format_file_size(download_info['file_size'])}"
                    )
                    
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=video_file,
                        caption=caption[:1024],  # Telegram caption limit
                        parse_mode='Markdown',
                        supports_streaming=True
                    )
                
                # Delete status message
                await status_message.delete()
                
                # Send success message
                await update.message.reply_text(
                    f"✅ **Download completed!**\n\n"
                    f"Your {platform} video has been successfully downloaded and sent!",
                    parse_mode='Markdown'
                )
                
                # Cleanup
                cleanup_file(file_path)
                
            else:
                await status_message.edit_text(
                    f"❌ **Download failed**\n\n"
                    f"**Error:** {error_message}\n\n"
                    "Please try again with a different video or check if the URL is correct.",
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error handling URL {url}: {e}")
            await status_message.edit_text(
                f"❌ **An error occurred**\n\n"
                f"Something went wrong while processing your {platform} video. "
                f"Please try again later.\n\n"
                f"**Error details:** {str(e)[:100]}...",
                parse_mode='Markdown'
            )
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle non-URL text messages"""
        text = update.message.text.strip()
        
        # Check if it might be a URL without protocol
        if any(platform in text.lower() for platform in ['youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 'fb.watch']):
            # Try to fix the URL
            if not text.startswith(('http://', 'https://')):
                text = 'https://' + text
                await self.handle_url(update._replace(message=update.message._replace(text=text)), context)
                return
        
        await update.message.reply_text(
            "👋 **Hello!**\n\n"
            "I'm a video downloader bot. Send me a video URL from:\n"
            "• YouTube\n"
            "• Instagram\n"
            "• Facebook\n\n"
            "Or use /help for more information!",
            parse_mode='Markdown'
        )
    
    async def set_bot_commands(self, application):
        """Set bot commands for the menu"""
        commands = [
            BotCommand("start", "Start the bot and see welcome message"),
            BotCommand("help", "Show help and usage information"),
        ]
        await application.bot.set_my_commands(commands)
    
    def run(self):
        """Start the bot"""
        logger.info("Starting Telegram Video Downloader Bot...")
        
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        
        # URL handler - matches http/https URLs
        application.add_handler(MessageHandler(
            filters.Regex(r'https?://[^\s]+'), 
            self.handle_url
        ))
        
        # Text handler for non-URL messages
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'https?://[^\s]+'),
            self.handle_text
        ))
        
        # Set bot commands
        application.post_init = self.set_bot_commands
        
        # Start the bot
        logger.info("Bot is starting...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "your_bot_token_here":
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        logger.error("Please set your Telegram Bot Token:")
        logger.error("export TELEGRAM_BOT_TOKEN='your_actual_bot_token'")
        exit(1)
    
    bot = TelegramVideoBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
