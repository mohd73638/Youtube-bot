import os
import logging
import threading
from flask import Flask, request, jsonify, render_template
from werkzeug.middleware.proxy_fix import ProxyFix
from bot import TelegramBot
from webhook_handler import WebhookHandler

flask_app = Flask(__name__)

@flask_app.route("/webhook/telegram", methods=["POST"])
def flask_webhook():
    """Fallback webhook handler"""
    update = Update.de_json(request.get_json(), YouTubeBot().app.bot)
    YouTubeBot().process_update(update)
    return {"status": "ok"}

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Initialize components
telegram_bot = TelegramBot()
webhook_handler = WebhookHandler()

@app.route("/")
def index():
    """Main page showing bot status and information"""
    bot_info = {
        "status": "Running",
        "commands": [
            "/start - Start the bot",
            "/help - Show help message",
            "/analyze <repo_url> - Analyze a GitHub repository",
            "/status - Check bot status",
            "/repos - List watched repositories"
        ]
    }
    return render_template("index.html", bot_info=bot_info)

@app.route("/webhook/github", methods=["POST"])
def github_webhook():
    """Handle GitHub webhook events"""
    try:
        signature = request.headers.get("X-Hub-Signature-256")
        event_type = request.headers.get("X-GitHub-Event")
        payload = request.get_json()
        
        logger.info(f"Received GitHub webhook: {event_type}")
        
        # Verify webhook signature
        if signature and not webhook_handler.verify_signature(request.data, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 403
        
        # Process the webhook event
        if event_type:
            result = webhook_handler.handle_event(event_type, payload)
        else:
            result = {"status": "error", "message": "Missing event type"}
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    """Handle Telegram webhook updates"""
    try:
        update = request.get_json()
        logger.info("Received Telegram webhook update")
        
        # Process the update
        telegram_bot.process_update(update)
        
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/webhook/info")
def webhook_info():
    """Show webhook configuration information"""
    webhook_url = os.environ.get("WEBHOOK_URL", "https://youtube-bot-3-1g9w.onrender.com")
    return render_template("webhook_info.html", webhook_url=webhook_url)

@app.route("/health")
def health_check():
    """Health check endpoint for monitoring"""
    return jsonify({
        "status": "healthy",
        "bot_running": telegram_bot.is_running(),
        "github_connected": webhook_handler.is_configured()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

def start_telegram_bot():
    """Start the Telegram bot in polling mode"""
    try:
        telegram_bot.start_polling()
        logger.info("Telegram bot started in polling mode")
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {str(e)}")

if __name__ == "__main__":
    # Start Telegram bot in a separate thread for development
    if os.environ.get("FLASK_ENV") == "development":
        bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
        bot_thread.start()
    
    # Run Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
