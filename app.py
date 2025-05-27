import os
import logging
from flask import Flask, request, jsonify
from bot import TelegramBot
from config import Config
from models import db
from database import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize bot
bot = TelegramBot()

# Create database tables
with app.app_context():
    db.create_all()
    logger.info("Database tables created successfully")

@app.route('/')
def index():
    """Health check endpoint"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Bot</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status {
                color: #28a745;
                font-size: 18px;
                font-weight: bold;
            }
            .info {
                margin-top: 20px;
                padding: 15px;
                background-color: #e9ecef;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 YouTube Bot Service</h1>
            <p class="status">✅ Bot is running and ready!</p>
            <div class="info">
                <h3>Features:</h3>
                <ul>
                    <li>Download videos from YouTube and other platforms</li>
                    <li>Webhook-based Telegram integration</li>
                    <li>Automatic video processing and delivery</li>
                    <li>Error handling and user feedback</li>
                </ul>
                <h3>Commands:</h3>
                <ul>
                    <li>/start - Start the bot</li>
                    <li>/help - Show help message</li>
                    <li>Send any video URL to download</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming Telegram webhooks"""
    try:
        data = request.get_json()
        logger.info(f"Received webhook data: {data}")
        
        if not data:
            logger.error("No data received in webhook")
            return jsonify({'error': 'No data received'}), 400
        
        # Process the update
        response = bot.process_update(data)
        
        if response:
            logger.info(f"Bot response: {response}")
            return jsonify({'status': 'success', 'response': response})
        else:
            return jsonify({'status': 'success', 'message': 'Update processed'})
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/set_webhook', methods=['GET', 'POST'])
def set_webhook():
    """Set webhook URL for the bot"""
    try:
        webhook_url = f"{Config.WEBHOOK_URL}/webhook"
        result = bot.set_webhook(webhook_url)
        logger.info(f"Webhook set result: {result}")
        return jsonify({
            'status': 'success',
            'webhook_url': webhook_url,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information"""
    try:
        info = bot.get_webhook_info()
        return jsonify(info)
    except Exception as e:
        logger.error(f"Error getting webhook info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Get database stats
        with app.app_context():
            overview = DatabaseManager.get_bot_overview()
        
        return jsonify({
            'status': 'healthy',
            'bot_token_configured': bool(Config.BOT_TOKEN),
            'webhook_url': Config.WEBHOOK_URL,
            'database_connected': True,
            'bot_stats': overview
        })
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            'status': 'healthy',
            'bot_token_configured': bool(Config.BOT_TOKEN),
            'webhook_url': Config.WEBHOOK_URL,
            'database_connected': False,
            'error': str(e)
        })

@app.route('/stats')
def stats():
    """Get bot statistics"""
    try:
        with app.app_context():
            overview = DatabaseManager.get_bot_overview()
            recent_downloads = DatabaseManager.get_recent_downloads(20)
            
        return jsonify({
            'overview': overview,
            'recent_downloads': recent_downloads
        })
    except Exception as e:
        logger.error(f"Stats endpoint error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
