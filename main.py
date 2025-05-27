"""
Main entry point for the Telegram video downloader bot
Handles webhook setup and Flask app initialization
"""
import os
import logging
from flask import Flask, request, jsonify
from bot import TelegramBot
from webhook_handler import WebhookHandler
from config import Config
from models import db
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize database
db.init_app(app)

# Initialize bot and webhook handler
config = Config()
telegram_bot = TelegramBot(config)
db_manager = DatabaseManager()
webhook_handler = WebhookHandler(telegram_bot, db_manager)

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "Bot is running", "message": "البوت يعمل بشكل طبيعي"})

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook requests from Telegram"""
    try:
        json_data = request.get_json()
        if json_data:
            logger.info(f"Received webhook data: {json_data}")
            webhook_handler.process_update(json_data)
            return jsonify({"status": "ok"})
        else:
            logger.warning("Received empty webhook data")
            return jsonify({"error": "No data received"}), 400
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/set_webhook', methods=['POST'])
def set_webhook():
    """Set webhook URL for the bot"""
    try:
        webhook_url = f"{config.WEBHOOK_URL}/webhook"
        success = telegram_bot.set_webhook(webhook_url)
        if success:
            return jsonify({"status": "Webhook set successfully", "url": webhook_url})
        else:
            return jsonify({"error": "Failed to set webhook"}), 500
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        # Create database tables
        try:
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
    
    # Set webhook on startup if webhook URL is provided
    if config.WEBHOOK_URL:
        try:
            webhook_url = f"{config.WEBHOOK_URL}/webhook"
            telegram_bot.set_webhook(webhook_url)
            logger.info(f"Webhook set to: {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to set webhook on startup: {str(e)}")
    
    # Run Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
