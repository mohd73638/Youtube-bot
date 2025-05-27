"""
Database operations for the Telegram video downloader bot
"""
import logging
from datetime import datetime, date
from typing import Optional, List
from models import db, User, Download, BotStats

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handle database operations for the bot"""
    
    def __init__(self):
        pass
    
    def get_or_create_user(self, user_data: dict) -> User:
        """Get existing user or create a new one"""
        try:
            user_id = user_data.get('id')
            user = User.query.filter_by(id=user_id).first()
            
            if not user:
                # Create new user
                user = User(
                    id=user_id,
                    username=user_data.get('username'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    language_code=user_data.get('language_code', 'ar')
                )
                db.session.add(user)
                logger.info(f"Created new user: {user_id}")
            else:
                # Update existing user info
                user.username = user_data.get('username', user.username)
                user.first_name = user_data.get('first_name', user.first_name)
                user.last_name = user_data.get('last_name', user.last_name)
                user.last_active = datetime.utcnow()
            
            db.session.commit()
            return user
            
        except Exception as e:
            logger.error(f"Error getting/creating user: {str(e)}")
            db.session.rollback()
            return None
    
    def log_download(self, user_id: int, url: str, platform: str, title: str = None, 
                    file_size: int = None, download_time: float = None, 
                    status: str = 'success', error_message: str = None) -> bool:
        """Log a download attempt"""
        try:
            download = Download(
                user_id=user_id,
                url=url,
                platform=platform,
                title=title,
                file_size=file_size,
                download_time=download_time,
                status=status,
                error_message=error_message
            )
            
            db.session.add(download)
            
            # Update user's total downloads if successful
            if status == 'success':
                user = User.query.filter_by(id=user_id).first()
                if user:
                    user.total_downloads += 1
            
            db.session.commit()
            logger.info(f"Logged download: {platform} - {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging download: {str(e)}")
            db.session.rollback()
            return False
    
    def get_user_stats(self, user_id: int) -> dict:
        """Get statistics for a specific user"""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return {}
            
            downloads = Download.query.filter_by(user_id=user_id).all()
            successful_downloads = [d for d in downloads if d.status == 'success']
            
            platforms = {}
            total_size = 0
            
            for download in successful_downloads:
                platform = download.platform
                platforms[platform] = platforms.get(platform, 0) + 1
                if download.file_size:
                    total_size += download.file_size
            
            most_used_platform = max(platforms.items(), key=lambda x: x[1])[0] if platforms else None
            
            return {
                'total_downloads': user.total_downloads,
                'successful_downloads': len(successful_downloads),
                'failed_downloads': len(downloads) - len(successful_downloads),
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'most_used_platform': most_used_platform,
                'member_since': user.created_at.strftime('%Y-%m-%d'),
                'platforms_used': platforms
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return {}
    
    def get_bot_stats(self) -> dict:
        """Get overall bot statistics"""
        try:
            total_users = User.query.count()
            total_downloads = Download.query.count()
            successful_downloads = Download.query.filter_by(status='success').count()
            
            # Get platform statistics
            platform_query = db.session.query(
                Download.platform, 
                db.func.count(Download.id).label('count')
            ).filter_by(status='success').group_by(Download.platform).all()
            
            platforms = {platform: count for platform, count in platform_query}
            most_popular_platform = max(platforms.items(), key=lambda x: x[1])[0] if platforms else None
            
            # Get recent activity (last 7 days)
            week_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            recent_downloads = Download.query.filter(
                Download.created_at >= week_ago
            ).count()
            
            return {
                'total_users': total_users,
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': total_downloads - successful_downloads,
                'success_rate': round((successful_downloads / total_downloads * 100), 2) if total_downloads > 0 else 0,
                'most_popular_platform': most_popular_platform,
                'recent_downloads_7d': recent_downloads,
                'platforms': platforms
            }
            
        except Exception as e:
            logger.error(f"Error getting bot stats: {str(e)}")
            return {}
    
    def get_user_download_history(self, user_id: int, limit: int = 10) -> List[dict]:
        """Get recent download history for a user"""
        try:
            downloads = Download.query.filter_by(
                user_id=user_id
            ).order_by(
                Download.created_at.desc()
            ).limit(limit).all()
            
            history = []
            for download in downloads:
                history.append({
                    'platform': download.platform,
                    'title': download.title or 'Unknown',
                    'status': download.status,
                    'date': download.created_at.strftime('%Y-%m-%d %H:%M'),
                    'size_mb': round(download.file_size / (1024 * 1024), 2) if download.file_size else 0
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting download history: {str(e)}")
            return []
    
    def update_daily_stats(self):
        """Update daily statistics"""
        try:
            today = date.today()
            stats = BotStats.query.filter_by(date=today).first()
            
            if not stats:
                stats = BotStats(date=today)
                db.session.add(stats)
            
            # Update statistics
            stats.total_users = User.query.count()
            stats.new_users = User.query.filter(
                db.func.date(User.created_at) == today
            ).count()
            
            stats.total_downloads = Download.query.filter(
                db.func.date(Download.created_at) == today
            ).count()
            
            stats.successful_downloads = Download.query.filter(
                db.func.date(Download.created_at) == today,
                Download.status == 'success'
            ).count()
            
            stats.failed_downloads = stats.total_downloads - stats.successful_downloads
            
            # Get most popular platform today
            platform_query = db.session.query(
                Download.platform, 
                db.func.count(Download.id).label('count')
            ).filter(
                db.func.date(Download.created_at) == today,
                Download.status == 'success'
            ).group_by(Download.platform).order_by(db.desc('count')).first()
            
            if platform_query:
                stats.most_popular_platform = platform_query[0]
            
            db.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error updating daily stats: {str(e)}")
            db.session.rollback()
            return False