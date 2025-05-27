# GitHub Code Analyzer Bot

A powerful Telegram bot that analyzes GitHub repositories for code issues, security vulnerabilities, and provides improvement suggestions.

## Features

- 🔍 **Code Analysis**: Detects security vulnerabilities and code quality issues
- 📊 **GitHub Integration**: Seamless repository analysis via GitHub API
- 🤖 **Telegram Bot**: Easy-to-use commands for repository analysis
- 🔔 **Webhook Support**: Real-time notifications for repository changes
- 🌐 **Web Dashboard**: Monitor bot status and configuration

## Quick Start

### 1. Deploy to Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

### 2. Set Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token from @BotFather
- `GITHUB_TOKEN`: GitHub personal access token (optional, for higher rate limits)
- `GITHUB_WEBHOOK_SECRET`: Secret for webhook verification (optional)
- `WEBHOOK_URL`: Your deployed application URL

### 3. Bot Commands

- `/start` - Start the bot
- `/help` - Show help message
- `/analyze <repo_url>` - Analyze a GitHub repository
- `/status` - Check bot and service status
- `/repos` - List watched repositories

## Example Usage

```
/analyze https://github.com/user/repository
```

The bot will analyze the repository and provide:
- Security vulnerability detection
- Code quality issues
- Best practice suggestions
- File structure analysis

## Supported Languages

- Python
- JavaScript/TypeScript
- Java
- C/C++
- Go
- Rust
- PHP
- Ruby
- And more...

## Webhook Configuration

1. Go to your GitHub repository settings
2. Navigate to Webhooks
3. Add webhook with URL: `https://your-app.onrender.com/webhook/github`
4. Set content type to `application/json`
5. Select events: Push, Pull requests, Issues

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_BOT_TOKEN="your_token_here"

# Run the application
python main.py
```

## License

MIT License - see LICENSE file for details