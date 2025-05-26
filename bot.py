import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")
APP_URL = "https://youtube-bot-j2rf.onrender.com"  # رابط تطبيقك على Render

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً! البوت شغال عبر Webhook!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

WEBHOOK_PATH = "/bot_webhook"
WEBHOOK_URL = APP_URL + WEBHOOK_PATH

app.run_webhook(
    listen="0.0.0.0",
    port=int(os.environ.get("PORT", 10000)),
    webhook_url=WEBHOOK_URL,
    webhook_path=WEBHOOK_PATH
)
