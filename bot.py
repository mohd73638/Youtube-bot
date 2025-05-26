
import os
import logging
from telegram import Update, ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from config import BOT_TOKEN, setup_logging
from video_downloader import VideoDownloader
from utils import is_supported_url, get_platform_name, cleanup_file, format_file_size

# إعدادات عامة
setup_logging()
logger = logging.getLogger(__name__)

# قناة الاشتراك
CHANNEL_USERNAME = "@atheraber"

# رابط تطبيقك على Render
APP_URL = "https://youtube-bot-j2rf.onrender.com"

class TelegramVideoBot:
    def __init__(self):
        self.downloader = VideoDownloader()

    async def check_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user_id = update.effective_user.id
        try:
            chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
            if chat_member.status in ["member", "administrator", "creator"]:
                return True
            else:
                await update.message.reply_text("❗️ يجب الاشتراك في القناة أولاً:\n" + CHANNEL_USERNAME)
                return False
        except Exception as e:
            logger.error(f"فشل التحقق من الاشتراك: {e}")
            await update.message.reply_text("❗️ حصل خطأ أثناء التحقق من الاشتراك.")
            return False

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "مرحباً بك في بوت تحميل الفيديوهات!\nأرسل رابط الفيديو من يوتيوب أو إنستجرام أو فيسبوك وسأقوم بتحميله لك."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_subscription(update, context):
            return

        url = update.message.text.strip()
        if not is_supported_url(url):
            await update.message.reply_text("❗️ هذا الرابط غير مدعوم.")
            return

        platform = get_platform_name(url)
        await update.message.reply_text(f"🔍 جاري تحميل الفيديو من {platform}...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VIDEO)

        try:
            file_path, file_name, file_size = self.downloader.download(url)
            caption = f"✅ تم التحميل من {platform}\nالحجم: {format_file_size(file_size)}"
            with open(file_path, "rb") as video_file:
                await update.message.reply_video(video=video_file, caption=caption)
            cleanup_file(file_path)
        except Exception as e:
            logger.error(f"خطأ أثناء تحميل الفيديو: {e}")
            await update.message.reply_text("❗️ حصل خطأ أثناء تحميل الفيديو.")

# بدء التطبيق
bot_instance = TelegramVideoBot()
application = Application.builder().token(BOT_TOKEN).build()
application.add_handler(CommandHandler("start", bot_instance.start_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot_instance.handle_message))

# إعداد Webhook
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = f"{APP_URL}{WEBHOOK_PATH}"

if __name__ == "__main__":
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=WEBHOOK_URL
    )
