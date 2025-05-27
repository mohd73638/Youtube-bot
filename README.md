# YouTube Video Downloader Telegram Bot

A powerful Telegram bot that can download videos from YouTube and 100+ other platforms using yt-dlp. The bot is designed to run on Render with webhook integration for optimal performance.

## Features

- 📹 Download videos from YouTube, Instagram, TikTok, Twitter, Facebook, and many more
- 🎯 High-quality downloads up to 720p
- ⚡ Fast processing with webhook integration
- 🔄 Automatic file size optimization for Telegram limits
- 🛡️ Robust error handling and user feedback
- 📱 User-friendly interface with helpful commands
- 🌐 Web interface for bot status monitoring

## Supported Platforms

- YouTube (youtube.com, youtu.be)
- Instagram (instagram.com)
- TikTok (tiktok.com)
- Twitter/X (twitter.com, x.com)
- Facebook (facebook.com)
- Vimeo (vimeo.com)
- Reddit (reddit.com)
- And 100+ more platforms supported by yt-dlp

## Setup Instructions

### 1. Create a Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command to create a new bot
3. Follow the instructions and get your bot token
4. Save the token - you'll need it for deployment

### 2. Deploy on Render

1. Fork this repository to your GitHub account
2. Create a new Web Service on [Render](https://render.com)
3. Connect your GitHub repository
4. Configure the following:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT`
   - **Environment Variables**:
     - `BOT_TOKEN`: Your Telegram bot token from BotFather
     - `WEBHOOK_URL`: Your Render app URL (e.g., `https://your-app.onrender.com`)

### 3. Set Up Webhook

After deployment, visit `https://your-app.onrender.com/set_webhook` to configure the webhook automatically.

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Yes | - |
| `WEBHOOK_URL` | Your Render app URL | Yes | - |
| `MAX_FILE_SIZE` | Maximum file size in bytes | No | 50MB |
| `DOWNLOAD_TIMEOUT` | Download timeout in seconds | No | 300 |
| `VIDEO_QUALITY` | Video quality setting | No | `best[height<=720]` |

## Bot Commands

- `/start` - Start the bot and get welcome message
- `/help` - Show detailed help and instructions
- Send any video URL - Bot will download and send the video

## Usage

1. Start a chat with your bot
2. Send `/start` to initialize
3. Send any video URL from supported platforms
4. Wait for the bot to process and send your video

## File Structure

