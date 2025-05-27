# Render Deployment Guide for YouTube Bot

## 1. Update Your GitHub Repository

Copy these files to your GitHub repository:
- `models.py` - Database models
- `database.py` - Database manager
- Updated `app.py` - With database integration
- Updated `bot.py` - With user tracking
- Updated `config.py` - Configuration

## 2. Create/Update requirements.txt in GitHub

Replace your requirements.txt with these dependencies:
```
flask==3.1.1
flask-sqlalchemy==3.1.1
gunicorn==23.0.0
requests==2.32.3
yt-dlp==2025.5.22
psycopg2-binary==2.9.10
sqlalchemy==2.0.41
```

## 3. Add PostgreSQL Database to Render

1. Go to your Render Dashboard
2. Click "New +" → "PostgreSQL"
3. Create a new database with these settings:
   - Name: `youtube-bot-db`
   - Database: `youtube_bot`
   - User: `youtube_bot_user`
   - Region: Same as your web service

## 4. Update Environment Variables in Render

In your web service settings, add these environment variables:

**Required:**
- `BOT_TOKEN` = Your Telegram bot token
- `WEBHOOK_URL` = https://youtube-bot-3-1g9w.onrender.com
- `DATABASE_URL` = (Copy from your PostgreSQL database's "External Database URL")

**Optional (with defaults):**
- `MAX_FILE_SIZE` = 52428800 (50MB)
- `DOWNLOAD_TIMEOUT` = 300
- `VIDEO_QUALITY` = best[height<=720]

## 5. Verify Build & Start Commands

Ensure your Render service has:
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300`

## 6. Deploy & Test

1. Push all changes to your GitHub repository
2. Render will automatically rebuild your service
3. Once deployed, visit: `https://youtube-bot-3-1g9w.onrender.com/set_webhook`
4. Test your bot in Telegram

## 7. Monitor Your Bot

Use these endpoints to monitor your bot:
- `/health` - Bot status and database stats
- `/stats` - Detailed usage analytics
- `/webhook_info` - Webhook status

## Troubleshooting

**If you get 404 errors:**
- Check that your GitHub repository has all the updated files
- Verify the build completed successfully in Render logs
- Ensure the start command is correct

**If database connection fails:**
- Verify DATABASE_URL is set correctly
- Check that PostgreSQL database is running
- Ensure your service and database are in the same region

**If webhook fails:**
- Run `/set_webhook` endpoint after deployment
- Check that WEBHOOK_URL matches your Render service URL
- Verify BOT_TOKEN is correct

## What's New in This Version

✅ Complete user tracking and analytics
✅ Download history with success/failure tracking
✅ Platform usage statistics (YouTube, Instagram, TikTok, etc.)
✅ Performance monitoring (download times, file sizes)
✅ Daily statistics dashboard
✅ Enhanced error handling and logging

Your bot will now track every user interaction and provide detailed analytics!