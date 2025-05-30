import logging
import sys
import requests
import os # Added import
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

# --- PTB Application Setup ---
# Build the PTB application instance first
bot_application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

# --- Bot Class Definition ---
class YouTubeBot:
    def __init__(self, application):
        self.app = application  # Use the passed PTB Application
        self.downloader = VideoDownloader()
        self._register_handlers()

    def _register_handlers(self):
        """Register all command and message handlers"""
        # Check if handlers are already added to prevent duplicates if instantiated multiple times
        if not self.app.handlers.get(0):
            self.app.add_handler(CommandHandler("start", self._start))
            self.app.add_handler(CommandHandler("help", self._help))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
            self.app.add_handler(CallbackQueryHandler(self._verify_subscription, pattern="^verify_sub$"))
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
            # Allow members, admins, and creators
            return chat_member.status in ["member", "administrator", "creator"]
        except Exception as e:
            # Handle potential errors like user not found in channel or bot permissions issue
            logger.error(f"Subscription check failed for user {user_id}: {e}")
            return False

    async def _require_subscription(self, update: Update):
        """Prompt user to join the channel"""
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✨ Join Channel", url=Config.CHANNEL_LINK)],
            [InlineKeyboardButton("✅ Verify Join", callback_data="verify_sub")]
        ])

        # Ensure we reply to a message if possible
        reply_method = update.message.reply_text if update.message else update.effective_message.reply_text
        await reply_method(
            "📢 Please join our channel to use this bot:",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def _verify_subscription(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle subscription verification via callback query"""
        query = update.callback_query
        await query.answer() # Acknowledge the callback query immediately

        user_id = query.from_user.id
        if await self._check_subscription(user_id):
            logger.info(f"User {user_id} verified subscription.")
            await query.edit_message_text("✅ Access granted! Send me a video link.")
        else:
            logger.info(f"User {user_id} failed subscription verification.")
            # Provide clearer feedback
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
        # Ignore potential edits or non-message updates if any slip through filters
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

        msg = None # Initialize msg to None
        file_path = None # Initialize file_path
        try:
            # Send "Downloading..." message and store it
            msg = await update.message.reply_text("⏳ Downloading video... Please wait.")
            logger.info(f"User {user.id} requested download for: {url}")

            # Attempt download
            file_path, title = await self.downloader.download_video(url)

            if file_path:
                logger.info(f"Download successful for {url}. Sending video: {file_path}")
                # Send the video file
                await update.message.reply_video(
                    video=open(file_path, "rb"),
                    caption=f"🎥 {title}", # Title is already truncated in downloader
                    supports_streaming=True,
                    # Consider adding timeout for large uploads if needed
                    # write_timeout=60.0,
                    # connect_timeout=60.0,
                    # read_timeout=60.0
                )
                # Delete the "Downloading..." message after successful send
                await msg.delete()
                logger.info(f"Successfully sent video for {url}")
            else:
                # Download failed (downloader returned None)
                logger.warning(f"Download function returned no file path for {url}")
                if msg:
                    await msg.edit_text("❌ Download failed. Could not retrieve the video file. The link might be invalid, private, or too large.")

        except Exception as e:
            # Catch potential errors during download or sending
            logger.error(f"Error handling message for {url}: {e}", exc_info=True)
            error_message = f"⚠️ An error occurred: {str(e)[:200]}"
            if msg:
                # Try to edit the status message to show the error
                try:
                    await msg.edit_text(error_message)
                except Exception as edit_err:
                    logger.error(f"Failed to edit message on error: {edit_err}")
                    # Fallback to sending a new message if editing fails
                    await update.message.reply_text(error_message)
            else:
                # If the initial status message failed, send a new error message
                await update.message.reply_text(error_message)
        finally:
            # Ensure cleanup happens even if sending fails
            if file_path:
                cleanup_file(file_path)
                logger.info(f"Cleaned up file: {file_path}")

# --- FastAPI Lifespan & Webhook Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FastAPI lifespan startup: Initializing and starting PTB application...")
    # Initialize the bot instance and register handlers
    # Ensure handlers are registered on the global bot_application
    YouTubeBot(bot_application)

    await bot_application.initialize()
    await bot_application.start()
    logger.info("PTB application started.")

    # --- Webhook Setting --- 
    # It's generally safer to set the webhook *after* the server is confirmed running.
    # Render's build command is too early. Doing it here is better, but has risks
    # if the app restarts frequently or the URL changes.
    # Consider a manual setup or a separate setup script after first deployment.
    # If uncommenting, ensure APP_URL is correctly set in environment.
    # try:
    #     logger.info(f"Attempting to set webhook to {Config.WEBHOOK_URL}")
    #     await bot_application.bot.set_webhook(url=Config.WEBHOOK_URL, allowed_updates=Update.ALL_TYPES)
    #     logger.info("Webhook set successfully via PTB.")
    # except Exception as e:
    #     logger.error(f"Failed to set webhook during startup: {e}")
    # -----------------------

    yield
    # Shutdown
    logger.info("FastAPI lifespan shutdown: Stopping and shutting down PTB application...")
    await bot_application.stop()
    await bot_application.shutdown()
    logger.info("PTB application stopped.")

# Initialize FastAPI
webserver = FastAPI(lifespan=lifespan)

# --- FastAPI Routes ---
@webserver.get("/")
def read_root():
    # Simple health check endpoint
    return {"status": "Bot webserver is running"}

@webserver.post(Config.WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Handle incoming Telegram updates via webhook"""
    try:
        update_data = await request.json()
        logger.debug(f"Webhook received data: {update_data}")

        # Create an Update object
        update = Update.de_json(update_data, bot_application.bot)

        # Process the update via PTB's dispatcher
        await bot_application.process_update(update)

        # Return success to Telegram
        return JSONResponse(content={"status": "ok"}, status_code=status.HTTP_200_OK)

    except Exception as e:
        # Log errors thoroughly
        logger.error(f"Error processing webhook update: {e}", exc_info=True)
        try:
            # Log raw body for debugging difficult issues
            raw_body = await request.body()
            logger.error(f"Raw request body on error: {raw_body.decode()}")
        except Exception as req_err:
            logger.error(f"Could not get raw request body on error: {req_err}")

        # Return a generic error response to Telegram
        return JSONResponse(
            content={"status": "error", "detail": "Internal server error processing update"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

# --- Webhook Setting Function (for manual use or build command if necessary) ---
def set_webhook_sync():
    """Synchronous function to set the webhook (e.g., for build command)"""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.WEBHOOK_URL:
        logger.error("Bot token or webhook URL is missing in config. Cannot set webhook.")
        return False

    webhook_set_url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook"
    params = {"url": Config.WEBHOOK_URL}
    try:
        response = requests.post(webhook_set_url, json=params)
        response.raise_for_status() # Check for HTTP errors
        logger.info(f"Webhook set successfully via requests to {Config.WEBHOOK_URL}. Response: {response.json()}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to set webhook using requests: {e}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during webhook setup: {e}", exc_info=True)
        return False

# --- Main Execution Block (for running with Uvicorn) ---
if __name__ == "__main__":
    # This block is typically NOT executed when running with Uvicorn/Gunicorn
    # Uvicorn runs the 'webserver' object directly.
    # However, it can be used for actions like setting the webhook via command line.

    if "--set-webhook" in sys.argv:
        logger.info("Attempting to set webhook via --set-webhook flag...")
        if set_webhook_sync():
            logger.info("Webhook setup command finished successfully.")
        else:
            logger.error("Webhook setup command failed.")
        sys.exit(0) # Exit after attempting to set webhook

    # If you need to run locally with polling for testing (not recommended for production):
    # logger.info("Running bot in polling mode for local testing...")
    # YouTubeBot(bot_application) # Ensure handlers are registered
    # bot_application.run_polling()

    # The Uvicorn command should be run from the shell as specified in render.yaml
    logger.info("This script is intended to be run via a web server like Uvicorn.")
    logger.info("Example: uvicorn bot:webserver --host 0.0.0.0 --port $PORT")


