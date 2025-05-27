# GitHub Code Analyzer Bot - Deployment Instructions

## Files to Upload to Your GitHub Repository

Upload these files to your GitHub repository at `https://github.com/mohd73638/youtube-bot.com`:

### Core Application Files
- `main.py` - Main entry point for the application
- `app.py` - Flask web application with webhook endpoints
- `bot.py` - Telegram bot implementation
- `github_analyzer.py` - GitHub repository analysis engine
- `code_analyzer.py` - Code quality and security analyzer
- `webhook_handler.py` - GitHub webhook event processor

### Templates and Static Files
- `templates/index.html` - Main dashboard page
- `templates/webhook_info.html` - Webhook configuration page
- `static/style.css` - Custom styling

### Configuration Files
- `requirements_github.txt` - Python dependencies (rename to `requirements.txt` on GitHub)
- `runtime.txt` - Python runtime version
- `Procfile` - Process configuration for deployment
- `render.yaml` - Render deployment configuration
- `.gitignore` - Files to exclude from Git
- `README.md` - Project documentation
- `LICENSE` - MIT license file

## Render Deployment Steps

1. **Connect GitHub Repository**
   - Go to Render dashboard
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `mohd73638/youtube-bot.com`

2. **Configure Environment Variables**
   Set these in Render dashboard:
   ```
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   GITHUB_TOKEN=your_github_token (optional)
   WEBHOOK_URL=https://youtube-bot-3-1g9w.onrender.com
   SESSION_SECRET=random_secret_key
   FLASK_ENV=production
   ```

3. **Build Settings**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT main:app`

4. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy your bot

## GitHub Webhook Setup

1. Go to your repository settings
2. Click "Webhooks" → "Add webhook"
3. Set Payload URL: `https://youtube-bot-3-1g9w.onrender.com/webhook/github`
4. Content type: `application/json`
5. Select events: Push, Pull requests, Issues
6. Click "Add webhook"

## Bot Usage

Your bot will be available on Telegram with these commands:
- `/start` - Start the bot
- `/analyze <repo_url>` - Analyze a GitHub repository
- `/status` - Check bot status
- `/help` - Show help message

## Troubleshooting

- Check Render logs for deployment issues
- Verify environment variables are set correctly
- Test webhook with GitHub s webhook testing feature
- Use `/status` command to check bot health
