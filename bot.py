import os
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)
from telegram.error import TelegramError
from config import BOT_TOKEN, setup_logging
from video_downloader import VideoDownloader
from utils import is_supported_url, get_platform_name, cleanup_file, format_file_size

# إعداد تسجيل الأخطاء
setup_logging()
logger = logging.getLogger(__name__)

# رابط تطبيقك على Render
APP_URL = "https://youtube-bot-j2rf.onrender.com"

# معرف القناة المطلوب الاشتراك فيها
CHANNEL_USERNAME = "@atheraber"

class TelegramVideoBot:
    def __init__(self):
        self.downloader = VideoDownloader()

    async def check_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        user_id = update.effective_user.id
        try:
            member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
            return member.status in ["member", "administrator", "creator"]
        except TelegramError:
            return False

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_subscription(update, context):
            await update.message.reply_text(
                "يجب عليك الاشتراك في القناة أولاً لاستخدام البوت:\n" + CHANNEL_USERNAME
            )
            return

        await update.message.reply_text(
            "أهلاً بك في بوت التحميل!\nأرسل رابط الفيديو من YouTube أو Instagram أو Facebook."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_subscription(update, context):
            await update.message.reply_text(
                "الرجاء الاشتراك في القناة للاستمرار:\n" + CHANNEL_USERNAME
            )
            return

        url = update.message.text.strip()
        if not is_supported_url(url):
            await update.message.reply_text("الرابط غير مدعوم حالياً.")
            return

        platform = get_platform_name(url)
        await update.message.reply_text(f"جاري تحميل الفيديو من {platform}...")

        try:
            file_path = await self.downloader.download(url)
            if not file_path:
                await update.message.reply_text("فشل في تحميل الفيديو.")
                return

            file_size = os.path.getsize(file_path)
            await update.message.reply_video(video=open(file_path, 'rb'), caption=f"الحجم: {format_file_size(file_size)}")
        except Exception as e:
            logger.error("Download error", exc_info=e)
            await update.message.reply_text("حدث خطأ أثناء تحميل الفيديو.")
        finally:
            cleanup_file(file_path)

async def main():
    bot = TelegramVideoBot()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    # إعداد Webhook
    WEBHOOK_PATH = f"/{BOT_TOKEN}"
    WEBHOOK_URL = APP_URL + WEBHOOK_PATH
    PORT = int(os.environ.get("PORT", 10000))

    await application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
