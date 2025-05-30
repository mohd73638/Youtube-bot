import logging
import sys
from contextlib import asynccontextmanager
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from config import Config
from video_downloader import VideoDownloader
from utils import is_supported_url, cleanup_file

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await bot_application.initialize()
    await bot_application.start()
    logger.info("Bot initialized")
    yield
    # Shutdown
    await bot_application.shutdown()
    await bot_application.stop()
    logger.info("Bot stopped")

# Initialize FastAPI and PTB Application
webserver = FastAPI(lifespan=lifespan)
bot_application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

class YouTubeBot:
    def __init__(self):
        self.app = bot_application  # Use the global PTB Application
        self.downloader = VideoDownloader()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command and message handlers"""
        self.app.add_handler(CommandHandler("start", self._start))
        self.app.add_handler(CommandHandler("help", self._help))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        self.app.add_handler(CallbackQueryHandler(self._verify_subscription, pattern="^verify_sub$"))

    async def _check_subscription(self, user_id: int) -> bool:
        """Check if user is subscribed to the channel"""
        if not Config.CHANNEL_USERNAME:
            return True
            
        try:
            chat_member = await self.app.bot.get_chat_member(
                chat_id=f"@{Config.CHANNEL_USERNAME}",
                user_id=user_id
            )
            return chat_member.status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"Subscription check failed: {e}")
            return False

    async def _require_subscription(self, update: Update):
        """Prompt user to join the channel"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Join Channel", url=Config.CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_sub")]
        ])
        
        await update.message.reply_text(
            "📢 Please join our channel to use this bot:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def _verify_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription verification"""
        query = update.callback_query
        await query.answer()
        
        if await self._check_subscription(query.from_user.id):
            await query.edit_message_text("✅ Access granted! Send me a video link.")
        else:
            await query.answer("You haven't joined yet!", show_alert=True)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command handler"""
        if not await self._check_subscription(update.effective_user.id):
            await self._require_subscription(update)
            return
        await update.message.reply_text("Hello! Send me a YouTube/TikTok/Instagram link.")

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help command handler"""
        await update.message.reply_text(
            "🎬 *Video Download Bot*\n\n"
            "Supported platforms:\n"
            "- YouTube\n- TikTok\n- Instagram\n\n"
            f"Channel: {Config.CHANNEL_LINK}",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process video links"""
        user = update.effective_user
        if not await self._check_subscription(user.id):
            await self._require_subscription(update)
            return
            
        url = update.message.text
        if not is_supported_url(url):
            await update.message.reply_text("❌ Unsupported link. Try YouTube/TikTok/Instagram.")
            return

        try:
            msg = await update.message.reply_text("⏳ Downloading...")
            file_path, title = await self.downloader.download_video(url)
            
            if file_path:
                await update.message.reply_video(
                    video=open(file_path, "rb"),
                    caption=f"🎥 {title[:200]}",
                    supports_streaming=True
                )
                cleanup_file(file_path)
            else:
                await msg.edit_text("❌ Download failed")
        except Exception as e:
            logger.error(f"Download error: {e}")
            await update.message.reply_text(f"⚠️ Error: {str(e)[:200]}")

# FastAPI Routes
@webserver.get("/")
def read_root():
    return {"status": "Bot is running"}

@webserver.post(Config.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Handle Telegram updates via webhook"""
    try:
        update_data = await request.json()
        update = Update.de_json(update_data, bot_application.bot)
        
        if not bot_application.running:
            await bot_application.initialize()
            
        await bot_application.process_update(update)
        return JSONResponse(
            content={"status": "ok"},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(
            content={"status": "error", "detail": str(e)},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

def set_webhook():
    """Register the webhook with Telegram"""
    import requests
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook",
            json={"url": Config.WEBHOOK_URL}
        )
        logger.info(f"Webhook set: {Config.WEBHOOK_URL} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

if __name__ == "__main__":
    if "--webhook" in sys.argv:
        # Webhook mode (for Render)
        set_webhook()
        import uvicorn
        uvicorn.run(
            "bot:webserver",
            host="0.0.0.0",
            port=8000,
            reload=False
        )
    else:
        # Polling mode (for local testing)
        YouTubeBot().run()
