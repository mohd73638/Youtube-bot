import os
import logging
from fastapi import FastAPI, Request
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.constants import ChatMemberStatus
from utils import is_supported_url, get_platform_name, cleanup_file, format_file_size
from video_downloader import VideoDownloader
from config import BOT_TOKEN, setup_logging

# إعدادات
APP_URL = "https://youtube-bot-3-1g9w.onrender.com"  # رابط تطبيقك على Render
WEBHOOK_PATH = f"/{BOT_TOKEN}"
WEBHOOK_URL = APP_URL + WEBHOOK_PATH
CHANNEL_USERNAME = "@atheraber"  # معرف القناة

# تسجيل الأحداث
setup_logging()
logger = logging.getLogger(__name__)

# إنشاء تطبيق FastAPI
webserver = FastAPI()

# إنشاء البوت
application = Application.builder().token(BOT_TOKEN).build()
downloader = VideoDownloader()

# التحقق من الاشتراك في القناة
async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user_id = update.effective_user.id
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except Exception as e:
        logger.error(f"Subscription check failed: {e}")
        return False

# أمر /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await update.message.reply_text("يرجى الاشتراك في القناة أولاً: " + CHANNEL_USERNAME)
        return

    msg = (
        "🎥 **Video Downloader Bot** 🎥\n\n"
        "مرحباً! أرسل لي رابط فيديو من:\n"
        "• YouTube\n• Facebook\n• Instagram\n\n"
        "وسأقوم بتحميله لك."
    )
    await update.message.reply_text(msg)

# استلام الرابط
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await update.message.reply_text("يرجى الاشتراك في القناة أولاً: " + CHANNEL_USERNAME)
        return

    url = update.message.text.strip()
    if not is_supported_url(url):
        await update.message.reply_text("هذا الرابط غير مدعوم.")
        return

    await update.message.reply_text("جارٍ تحميل الفيديو، الرجاء الانتظار...")

    try:
        video_path, file_size = downloader.download(url)
        if not video_path:
            await update.message.reply_text("فشل التحميل.")
            return

        await context.bot.send_video(
            chat_id=update.effective_chat.id,
            video=open(video_path, "rb"),
            caption=f"✅ تم التحميل بنجاح\nالحجم: {format_file_size(file_size)}"
        )
    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text("حدث خطأ أثناء التحميل.")
    finally:
        cleanup_file(video_path)

# ربط الأوامر والمعالجات
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# نقطة استقبال التحديثات من Telegram
@webserver.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return {"ok": True}

# إعداد Webhook عند بدء التشغيل
@webserver.on_event("startup")
async def on_startup():
    await application.bot.set_webhook(WEBHOOK_URL)
    print("Webhook set:", WEBHOOK_URL)

@webserver.post(f"/{BOT_TOKEN}")
async def handle_webhook(request: Request):
    data = await request.json()
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
