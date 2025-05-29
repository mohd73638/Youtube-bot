
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters
)
from video_downloader import VideoDownloader
from config import Config
import asyncio

logging.basicConfig(
    format= %(asctime)s - %(name)s - %(levelname)s - %(message)s ,
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    """Send welcome message with usage instructions."""
    help_text = """
    🎬 YouTube/TikTok Downloader Bot
    
    Commands:
    /download <URL> - Download video
    /formats <URL> - Show available formats
    /cancel - Stop current download
    """
    await update.message.reply_text(help_text)

async def download_video(update: Update, context):
    """Handle download requests with queue management."""
    user = update.effective_user
    if Config.ALLOWED_USER_IDS and user.id not in Config.ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Access denied")
        return

    url =    .join(context.args)
    if not url:
        await update.message.reply_text("Please provide a URL")
        return

    try:
        msg = await update.message.reply_text("⏳ Starting download...")
        
        # Show typing indicator during download
        async with context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action= upload_video 
        ):
            file_path, title = await asyncio.to_thread(
                VideoDownloader.download_video, url
            )

        if file_path:
            await context.bot.send_video(
                chat_id=update.effective_chat.id,
                video=open(file_path,  rb ),
                caption=f"🎥 {title}"
            )
            cleanup_file(file_path)
        else:
            await msg.edit_text("❌ Download failed")

    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        await update.message.reply_text(f"Error: {str(e)}")

def main():
    """Start the bot with enhanced error handling."""
    try:
        app = ApplicationBuilder().token(Config.TELEGRAM_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("download", download_video))
        
        logger.info("Bot starting...")
        app.run_polling()
    except Exception as e:
        logger.critical(f"Bot crashed: {str(e)}")
        raise

if __name__ ==  __main__ :
    main()
