#!/usr/bin/env python3
import os
import logging
import asyncio
import tempfile
import shutil
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
import yt_dlp
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DOWNLOAD_DIR = "./downloads"
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB - Telegram's file size limit
REQUIRED_CHANNEL = "@atheraber"  # Users must subscribe to this channel

# Supported platforms
SUPPORTED_PLATFORMS = [
    'youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 'fb.watch'
]

def is_supported_url(url):
    """Check if the URL is from a supported platform"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        return any(platform in domain for platform in SUPPORTED_PLATFORMS)
    except:
        return False

def get_platform_name(url):
    """Get the platform name from URL"""
    try:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.lower()
        
        if 'youtube.com' in domain or 'youtu.be' in domain:
            return 'YouTube'
        elif 'instagram.com' in domain:
            return 'Instagram'
        elif 'facebook.com' in domain or 'fb.watch' in domain:
            return 'Facebook'
        else:
            return 'Unknown'
    except:
        return 'Unknown'

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def cleanup_file(file_path):
    """Safely delete a file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up file: {file_path}")
    except Exception as e:
        logger.error(f"Error cleaning up file {file_path}: {e}")

async def check_subscription(bot, user_id):
    """Check if user is subscribed to the required channel"""
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        # Check if user is a member (subscribed) or admin/creator
        # Note: 'left' means user left the channel, 'kicked' means banned
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error checking subscription for user {user_id}: {e}")
        
        # If the user is not found in the channel or other errors, they're not subscribed
        return False

async def send_subscription_message(update, context):
    """Send subscription requirement message"""
    subscription_message = f"""
🔒 **Subscription Required** 🔒

To use this video downloader bot, you need to subscribe to our channel first!

📢 **Please subscribe to:** {REQUIRED_CHANNEL}

**Steps:**
1️⃣ Click the link: {REQUIRED_CHANNEL}
2️⃣ Join the channel
3️⃣ Come back and try again

Once you subscribe, you can download videos from:
• YouTube
• Instagram  
• Facebook

**After subscribing, send /start again to use the bot!** ✨
    """
    await update.message.reply_text(subscription_message, parse_mode='Markdown')

def download_video(url, user_id=None):
    """Download video from URL and return file path"""
    try:
        # Create download directory
        if not os.path.exists(DOWNLOAD_DIR):
            os.makedirs(DOWNLOAD_DIR)
            
        # Create user-specific subdirectory
        user_dir = os.path.join(DOWNLOAD_DIR, str(user_id) if user_id else 'temp')
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'best[filesize<50M]/best',
            'outtmpl': os.path.join(user_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extractaudio': False,
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': True,
        }
        
        downloaded_file = None
        
        def progress_hook(d):
            nonlocal downloaded_file
            if d['status'] == 'finished':
                downloaded_file = d['filename']
                logger.info(f"Download finished: {downloaded_file}")
        
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
                return False, None, f"Video too large ({size_mb:.1f}MB). Maximum allowed size is 50MB", None
            
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    
    # Check if user is subscribed to required channel
    is_subscribed = await check_subscription(context.bot, user_id)
    
    if not is_subscribed:
        await send_subscription_message(update, context)
        return
    
    welcome_message = f"""
🎥 **Video Downloader Bot** 🎥

🎉 **Welcome back, subscriber!** 🎉

Thanks for being a member of {REQUIRED_CHANNEL}! You now have full access to download videos from:

📱 **Supported Platforms:**
✅ YouTube (youtube.com, youtu.be)
✅ Instagram (instagram.com) 
✅ Facebook (facebook.com, fb.watch)

🚀 **How to use:**
Simply send me any video URL and I'll download it for you instantly!

📊 **Features:**
• Fast downloads up to 50MB
• High quality videos
• Automatic cleanup
• No ads or watermarks

💡 **Pro tip:** Just paste the video link and wait for magic! ✨

Ready to download? Send me a video URL now! 🎬
    """
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    user_id = update.effective_user.id
    
    # Check if user is subscribed to required channel
    is_subscribed = await check_subscription(context.bot, user_id)
    
    if not is_subscribed:
        await send_subscription_message(update, context)
        return
    
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

Happy downloading! 🎬
    """
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video URL messages"""
    url = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check if user is subscribed to required channel
    is_subscribed = await check_subscription(context.bot, user_id)
    
    if not is_subscribed:
        await send_subscription_message(update, context)
        return
    
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
        "⏳ Starting download...",
        parse_mode='Markdown'
    )
    
    try:
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        
        # Download the video
        success, file_path, error_message, download_info = download_video(url, user_id)
        
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
                duration = download_info.get('duration', 0) or 0
                duration_str = f"{int(duration)//60}:{int(duration)%60:02d}" if duration > 0 else "Unknown"
                
                # Clean title and uploader for Telegram markdown
                clean_title = download_info['title'].replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                clean_uploader = download_info['uploader'].replace('*', '').replace('_', '').replace('[', '').replace(']', '')
                
                caption = (
                    f"🎥 {clean_title[:50]}{'...' if len(clean_title) > 50 else ''}\n\n"
                    f"📺 Platform: {platform}\n"
                    f"⏱️ Duration: {duration_str}\n"
                    f"👤 Uploader: {clean_uploader}\n"
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

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle non-URL text messages"""
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Check if user is subscribed to required channel
    is_subscribed = await check_subscription(context.bot, user_id)
    
    if not is_subscribed:
        await send_subscription_message(update, context)
        return
    
    # Check if it might be a URL without protocol
    if any(platform in text.lower() for platform in ['youtube.com', 'youtu.be', 'instagram.com', 'facebook.com', 'fb.watch']):
        # Try to fix the URL
        if not text.startswith(('http://', 'https://')):
            text = 'https://' + text
            await handle_url(update._replace(message=update.message._replace(text=text)), context)
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

def main():
    """Start the bot and health server"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set!")
        exit(1)
    
    # Start health check server in a separate thread
    import threading
    from health_server import start_health_server
    
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    logger.info("Health check server started for UptimeRobot monitoring")
    
    logger.info("Starting Telegram Video Downloader Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # URL handler - matches http/https URLs
    application.add_handler(MessageHandler(
        filters.Regex(r'https?://[^\s]+'), 
        handle_url
    ))
    
    # Text handler for non-URL messages
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex(r'https?://[^\s]+'),
        handle_text
    ))
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()