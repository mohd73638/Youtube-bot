import os
import logging
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from github_analyzer import GitHubAnalyzer
import asyncio
import json

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not self.token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
            raise ValueError("Telegram bot token is required")
        
        self.bot = Bot(token=self.token)
        self.application = None
        self.github_analyzer = GitHubAnalyzer()
        self.running = False
        
    def is_running(self):
        """Check if bot is running"""
        return self.running
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = """
🤖 *GitHub Code Analyzer Bot*

Welcome! I can help you analyze GitHub repositories for code issues and improvements.

*Available Commands:*
/help - Show this help message
/analyze <repo_url> - Analyze a GitHub repository
/status - Check bot and service status
/repos - List your watched repositories

*Example:*
`/analyze https://github.com/user/repo`

Let s get started! 🚀
        """
        await update.message.reply_text(welcome_message, parse_mode="Markdown")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = """
🔧 *GitHub Code Analyzer Bot Help*

*Commands:*
• `/start` - Start the bot
• `/help` - Show this help message
• `/analyze <repo_url>` - Analyze a GitHub repository for issues
• `/status` - Check bot and GitHub API status
• `/repos` - List repositories you re watching

*How to analyze a repository:*
1. Use `/analyze` followed by a GitHub repository URL
2. Example: `/analyze https://github.com/octocat/Hello-World`
3. The bot will scan the code and report issues

*Features:*
• Code quality analysis
• Security vulnerability detection
• Best practice suggestions
• GitHub webhook integration

Need more help? Contact your administrator.
        """
        await update.message.reply_text(help_message, parse_mode="Markdown")
    
    async def analyze_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /analyze command"""
        if not context.args:
            await update.message.reply_text(
                "❌ Please provide a GitHub repository URL.\n"
                "Example: `/analyze https://github.com/user/repo`",
                parse_mode="Markdown"
            )
            return
        
        repo_url = context.args[0]
        chat_id = update.effective_chat.id
        
        # Send initial message
        status_message = await update.message.reply_text(
            "🔍 *Analyzing repository...*\n"
            f"Repository: `{repo_url}`\n"
            "This may take a few moments...",
            parse_mode="Markdown"
        )
        
        try:
            # Analyze the repository
            analysis_result = await self.github_analyzer.analyze_repository(repo_url)
            
            if analysis_result.get("success"):
                # Format the results
                result_message = self._format_analysis_result(analysis_result)
                await status_message.edit_text(result_message, parse_mode="Markdown")
            else:
                await status_message.edit_text(
                    f"❌ *Analysis Failed*\n"
                    f"Error: {analysis_result.get( error ,  Unknown error )}",
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error in analyze command: {str(e)}")
            await status_message.edit_text(
                "❌ *Analysis Failed*\n"
                "An unexpected error occurred. Please try again later.",
                parse_mode="Markdown"
            )
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            github_status = await self.github_analyzer.check_api_status()
            
            if github_status:
                github_status_text = "✅ Connected"
            else:
                github_status_text = "❌ Error"
                
            status_message = f"""
🟢 *Bot Status*

*Telegram Bot:* ✅ Online
*GitHub API:* {github_status_text}
*Analysis Engine:* ✅ Ready

*Statistics:*
• Repositories analyzed: N/A
• Issues detected: N/A
• Last analysis: N/A

Bot is ready to analyze repositories! 🚀
            """
            
            await update.message.reply_text(status_message, parse_mode="Markdown")
            
        except Exception as e:
            logger.error(f"Error in status command: {str(e)}")
            await update.message.reply_text(
                "❌ Error checking status. Please try again later.",
                parse_mode="Markdown"
            )
    
    async def repos_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /repos command"""
        # For now, return a placeholder message
        repos_message = """
📚 *Watched Repositories*

No repositories are currently being watched.

To add a repository to your watch list, use:
`/analyze <repo_url>`

The bot will automatically monitor analyzed repositories for new commits and issues.
        """
        await update.message.reply_text(repos_message, parse_mode="Markdown")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        message_text = update.message.text.lower()
        
        if "github.com" in message_text and ("http" in message_text or "https" in message_text):
            # User sent a GitHub URL, suggest using /analyze
            await update.message.reply_text(
                "🔗 I detected a GitHub repository URL!\n"
                f"Use `/analyze {update.message.text}` to analyze this repository.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "👋 Hello! Use /help to see available commands or /analyze to analyze a GitHub repository."
            )
    
    def _format_analysis_result(self, result):
        """Format analysis results for Telegram message"""
        if not result.get("success"):
            error_msg = result.get("error", "Unknown error")
            return f"❌ Analysis failed: {error_msg}"
        
        data = result.get("data", {})
        repo_info = data.get("repository", {})
        issues = data.get("issues", [])
        suggestions = data.get("suggestions", [])
        
        message = f"✅ *Analysis Complete*\n\n"
        message += f"📦 *Repository:* {repo_info.get( name ,  Unknown )}\n"
        message += f"👤 *Owner:* {repo_info.get( owner ,  Unknown )}\n"
        message += f"🌟 *Stars:* {repo_info.get( stars ,  N/A )}\n"
        message += f"📝 *Language:* {repo_info.get( language ,  N/A )}\n\n"
        
        if issues:
            message += f"⚠️ *Issues Found ({len(issues)}):*\n"
            for i, issue in enumerate(issues[:5], 1):  # Limit to 5 issues
                message += f"{i}. {issue.get( type ,  unknown )}: {issue.get( description ,  No description )}\n"
            
            if len(issues) > 5:
                message += f"... and {len(issues) - 5} more issues\n"
            message += "\n"
        else:
            message += "✅ *No critical issues found!*\n\n"
        
        if suggestions:
            message += f"💡 *Suggestions ({len(suggestions)}):*\n"
            for i, suggestion in enumerate(suggestions[:3], 1):  # Limit to 3 suggestions
                message += f"{i}. {suggestion}\n"
            message += "\n"
        
        message += "📊 Use /status for more details"
        
        return message
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        if not self.application:
            return
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("analyze", self.analyze_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("repos", self.repos_command))
        
        # Message handler for regular text messages
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    def start_polling(self):
        """Start the bot in polling mode"""
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
            
            logger.info("Starting Telegram bot polling...")
            self.running = True
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
            
        except Exception as e:
            logger.error(f"Error starting bot polling: {str(e)}")
            self.running = False
            raise
    
    def process_update(self, update_data):
        """Process webhook update from Telegram"""
        try:
            if not self.application:
                self.application = Application.builder().token(self.token).build()
                self.setup_handlers()
            
            # Create Update object from webhook data
            update = Update.de_json(update_data, self.bot)
            
            # Process the update
            asyncio.run(self.application.process_update(update))
            
        except Exception as e:
            logger.error(f"Error processing Telegram update: {str(e)}")
            raise
