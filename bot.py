import logging
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from fastapi import FastAPI, Request
from telegram import Update

app = FastAPI()

def set_webhook():
    """Run once during deployment to set webhook URL"""
    from config import Config
    import requests
    requests.post(
        f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook",
        json={"url": f"{Config.WEBHOOK_URL}/webhook/telegram"}
    )

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram updates"""
    update = Update.de_json(await request.json(), bot)
    await YouTubeBot().process_update(update)
    return {"status": "ok"}

# Keep your existing YouTubeBot class

from config import Config
from video_downloader import VideoDownloader
from utils import is_supported_url, cleanup_file

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YouTubeBot:
    def __init__(self):
        self.app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
        self.downloader = VideoDownloader()
        self._register_handlers()

    def _register_handlers(self):
        """All handlers with subscription checks"""
        self.app.add_handler(CommandHandler("start", self._start))
        self.app.add_handler(CommandHandler("help", self._help))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        self.app.add_handler(CallbackQueryHandler(self._verify_subscription, pattern="^verify_sub$"))

    async def _check_subscription(self, user_id: int) -> bool:
        """Robust channel membership check"""
        if not Config.CHANNEL_USERNAME:
            return True
            
        try:
            chat_member = await self.app.bot.get_chat_member(
                chat_id=f"@{Config.CHANNEL_USERNAME}",
                user_id=user_id
            )
            return chat_member.status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"Subscription check failed: {str(e)}")
            return False

    async def _require_subscription(self, update: Update):
        """Interactive join prompt"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Join AtherAber", url=Config.CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_sub")]
        ])
        
        await update.message.reply_text(
            "📢 To use this bot, please join our channel first:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def _verify_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle verification button"""
        query = update.callback_query
        await query.answer()
        
        if await self._check_subscription(query.from_user.id):
            await query.edit_message_text("✅ Access granted! Send me a video link.")
        else:
            await query.answer("You haven't joined yet!", show_alert=True)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command with channel check"""
        if not await self._check_subscription(update.effective_user.id):
            await self._require_subscription(update)
            return
            
    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("This is the help message. Use /start to begin.")

        await update.message.reply_text(
            "🎬 *AtherAber Video Bot*\n\n"
            "Send links from:\n"
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
            await update.message.reply_text("❌ Unsupported platform. Try YouTube/TikTok/Instagram links.")
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
            logger.error(f"Download error: {str(e)}")
            await update.message.reply_text(f"⚠️ Error: {str(e)[:200]}")

    def run(self):
        """Start the bot"""
        logger.info(f"Starting bot for channel: {Config.CHANNEL_LINK}")
        self.app.run_polling()

if __name__ == "__main__":
    YouTubeBot().run()

if __name__ == "__main__":
    import sys
    if "--webhook" in sys.argv:
        from fastapi import FastAPI
        app = FastAPI()
        # ... (FastAPI setup)
    else:
        YouTubeBot().run()  # Standard polling
