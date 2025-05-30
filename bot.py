#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import sys
import requests
import os
import asyncio
from contextlib import asynccontextmanager
from functools import partial # Keep partial for run_in_executor
from pathlib import Path
Path("downloads").mkdir(exist_ok=True)

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
from fastapi.responses import JSONResponse, Response # Keep Response for HEAD

# Assuming these files exist in the same directory or PYTHONPATH is set correctly
from config import Config
from video_downloader import VideoDownloader
from utils import is_supported_url, cleanup_file

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- PTB Application Setup ---
bot_application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

# --- Bot Class Definition ---
class YouTubeBot:
    def __init__(self, application):
        self.app = application
        self.downloader = VideoDownloader()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command and message handlers"""
        if not self.app.handlers.get(0):
            self.app.add_handler(CommandHandler("start", self._start))
            self.app.add_handler(CommandHandler("help", self._help))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            self.app.add_handler(CallbackQueryHandler(self._verify_subscription, pattern="^verify_sub$"))
            self.app.add_handler(MessageHandler(filters.TEXT & _filters.Entity("url"), self._handle_url))
            logger.info("PTB handlers registered.")
        else:
            logger.warning("PTB handlers seem to be already registered. Skipping registration.")

    async def _check_subscription(self, user_id: int) -> bool:
        """Check if user is subscribed to the channel"""
        if not Config.CHANNEL_USERNAME:
            logger.warning("CHANNEL_USERNAME not set, skipping subscription check.")
            return True
        try:
            chat_member = await self.app.bot.get_chat_member(
                chat_id=f"@{Config.CHANNEL_USERNAME}",
                user_id=user_id
            )
            logger.debug(f"Subscription status for {user_id} in {Config.CHANNEL_USERNAME}: {chat_member.status}")
            return chat_member.status in ["member", "administrator", "creator"]
        except Exception as e:
            logger.error(f"Subscription check failed for user {user_id}: {e}")
            return False

    async def _require_subscription(self, update: Update):
        """Prompt user to join the channel"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Join Channel", url=Config.CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_sub")]
        ])
        reply_method = update.message.reply_text if update.message else update.effective_message.reply_text
        await reply_method(
            "📢 Please join our channel to use this bot:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def _verify_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription verification via callback query"""
        query = update.callback_query
        await query.answer()
        user_id = query.from_user.id
        if await self._check_subscription(user_id):
            logger.info(f"User {user_id} verified subscription.")
            await query.edit_message_text("✅ Access granted! Send me a video link.")
        else:
            logger.info(f"User {user_id} failed subscription verification.")
            await query.answer("You haven't joined the channel yet, or Telegram needs a moment to update. Please join and try verifying again.", show_alert=True)

    async def _start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command handler"""
        user_id = update.effective_user.id
        if not await self._check_subscription(user_id):
            await self._require_subscription(update)
            return
        await update.message.reply_text("Hello! Send me a supported video link (YouTube, TikTok, Instagram). Use /help for more info.")

    async def _help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help command handler"""
        help_text = (
            "🎬 *Video Download Bot*\n\n"
            "Send me a link from one of the supported platforms, and I'll download the video for you.\n\n"
            "*Supported platforms:*\n"
            "- YouTube\n- TikTok\n- Instagram\n\n"
        )
        if Config.CHANNEL_LINK:
            help_text += f"*Required Channel:* [{Config.CHANNEL_USERNAME}]({Config.CHANNEL_LINK})\n\n"
        help_text += "Just paste the video link directly into the chat."
        await update.message.reply_text(
            help_text,
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process video links sent as messages"""
        if not update.message or not update.message.text:
            return

        user = update.effective_user
        if not await self._check_subscription(user.id):
            await self._require_subscription(update)
            return

        url = update.message.text
        if not is_supported_url(url):
            await update.message.reply_text("❌ Unsupported link. Please send a valid link from YouTube, TikTok, or Instagram.")
            return


        msg = None
        file_path = None
        try:
            msg = await update.message.reply_text("⏳ Downloading video... Please wait.")
            logger.info(f"Download started for: {url}")

        # Run synchronous download in executor
            loop = asyncio.get_running_loop()
            file_path, result = await loop.run_in_executor(
                None, 
                lambda: self.downloader.download_video(url)
            )

            if file_path:
            # Check file size before sending
                file_size = os.path.getsize(file_path)
                if file_size > 50 * 1024 * 1024:  # 50MB limit
                    await msg.edit_text("❌ Video exceeds 50MB size limit")
                    return

                await update.message.reply_video(
                    video=open(file_path,  rb ),
                    caption=result[:1024],  # Telegram caption limit
                    supports_streaming=True,
                    width=1280,
                    height=720
                )
                await msg.delete()
            else:
                await msg.edit_text(f"❌ Download failed: {result or ' Unknown error' }")

        except Exception as e:
            logger.error(f"Download error: {str(e)}", exc_info=True)
            error_msg = f"⚠️ Error: {str(e)[:200]}"
            if msg:
                await msg.edit_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
        finally: 
            if file_path and os.path.exists(file_path):
                cleanup_file(file_path)


async def handle_url(update, context):
    url = update.message.text
    await update.message.reply_text(f"Got your URL: {url}")

async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logging.error("Exception while handling update:", exc_info=context.error)



def run(self):
    self._register_handlers()
    self.app.run_polling()



# --- FastAPI Lifespan & Webhook Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI lifespan startup: Initializing and starting PTB application...")
    YouTubeBot(bot_application) # Initialize bot class to register handlers
    await bot_application.initialize()
    await bot_application.start()
    logger.info("PTB application started.")
    # Webhook setting is best done manually or via a separate script after deployment
    yield
    logger.info("FastAPI lifespan shutdown: Stopping and shutting down PTB application...")
    await bot_application.stop()
    await bot_application.shutdown()
    logger.info("PTB application stopped.")

# Initialize FastAPI
webserver = FastAPI(lifespan=lifespan)

# --- FastAPI Routes ---
# --- Keep Simplified GET/HEAD handling for root path health check ---
@webserver.get("/", include_in_schema=False)
async def health_check_get():
    """Handles GET requests for health check."""
    return {"status": "Bot webserver is running"}

@webserver.head("/", include_in_schema=False)
async def health_check_head():
    """Handles HEAD requests for health check by returning empty 200 OK."""
    return Response(status_code=status.HTTP_200_OK)
# ------------------------------------------------------------------

@webserver.post(Config.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Handle incoming Telegram updates via webhook"""
    try:
        update_data = await request.json()
        logger.debug(f"Webhook received data: {update_data}")
        update = Update.de_json(update_data, bot_application.bot)
        await bot_application.process_update(update)
        return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        try:
            raw_body = await request.body()
            logger.error(f"Raw request body on error: {raw_body.decode()}")
        except Exception as req_err:
            logger.error(f"Could not get raw request body on error: {req_err}")
        return JSONResponse(
            content={"status": "error", "detail": "Internal server error processing update"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- Webhook Setting Function (Synchronous) ---
def set_webhook_sync():
    """Synchronous function to set the webhook (e.g., for build command or manual run)"""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.WEBHOOK_URL:
        logger.error("Bot token or webhook URL is missing in config. Cannot set webhook.")
        return False
    webhook_set_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
    params = {"url": Config.WEBHOOK_URL}
    try:
        response = requests.post(webhook_set_url, json=params)
        response.raise_for_status()
        logger.info(f"Webhook set successfully via requests to {Config.WEBHOOK_URL}. Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set webhook using requests: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during webhook setup: {e}", exc_info=True)
        return False

# --- Main Execution Block (for command line actions like setting webhook) ---
if __name__ == "__main__":
    if "--set-webhook" in sys.argv:
        logger.info("Attempting to set webhook via --set-webhook flag...")
        if set_webhook_sync():
            logger.info("Webhook setup command finished successfully.")
        else:
            logger.error("Webhook setup command failed.")
        sys.exit(0)
        
        bot = YourBotClass()
        bot.run()
  
    logger.info("This script is intended to be run via a web server like Uvicorn.")
    logger.info("Example: uvicorn bot:webserver --host 0.0.0.0 --port $PORT")


