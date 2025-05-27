import os
import logging
from datetime import datetime, date
from sqlalchemy import func
from models import db, User, Download, BotStats
from utils import extract_video_id

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Database manager for bot operations"""
    
    @staticmethod
    def get_or_create_user(telegram_user_data):
        """Get existing user or create new one"""
        try:
            telegram_id = telegram_user_data.get('id')
            if not telegram_id:
                return None
            
            user = User.query.filter_by(telegram_id=telegram_id).first()
            
            if not user:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=telegram_user_data.get('username'),
                    first_name=telegram_user_data.get('first_name'),
                    last_name=telegram_user_data.get('last_name'),
                    language_code=telegram_user_data.get('language_code'),
                    is_bot=telegram_user_data.get('is_bot', False)
                )
                db.session.add(user)
                logger.info(f"Created new user: {telegram_id}")
            else:
                # Update existing user info
                user.username = telegram_user_data.get('username', user.username)
                user.first_name = telegram_user_data.get('first_name', user.first_name)
                user.last_name = telegram_user_data.get('last_name', user.last_name)
                user.language_code = telegram_user_data.get('language_code', user.language_code)
                user.last_activity = datetime.utcnow()
                user.updated_at = datetime.utcnow()
            
            db.session.commit()
            return user
            
        except Exception as e:
            logger.error(f"Error managing user: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def create_download_record(telegram_id, url, video_info=None):
        """Create a new download record"""
        try:
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                logger.error(f"User not found for telegram_id: {telegram_id}")
                return None
            
            # Extract platform information
            platform_info = extract_video_id(url)
            platform = platform_info.get('platform', 'unknown')
            
            download = Download(
                user_id=user.id,
                telegram_id=telegram_id,
                original_url=url,
                video_platform=platform,
                status='pending'
            )
            
            # Add video info if available
            if video_info:
                download.video_title = video_info.get('title')
                download.video_duration = video_info.get('duration')
                download.video_uploader = video_info.get('uploader')
            
            db.session.add(download)
            db.session.commit()
            
            logger.info(f"Created download record {download.id} for user {telegram_id}")
            return download
            
        except Exception as e:
            logger.error(f"Error creating download record: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_download_status(download_id, status, **kwargs):
        """Update download status and related information"""
        try:
            download = Download.query.get(download_id)
            if not download:
                logger.error(f"Download record not found: {download_id}")
                return False
            
            download.status = status
            
            # Update additional fields
            if 'error_message' in kwargs:
                download.error_message = kwargs['error_message']
            
            if 'file_size' in kwargs:
                download.file_size = kwargs['file_size']
            
            if 'file_format' in kwargs:
                download.file_format = kwargs['file_format']
            
            if 'download_quality' in kwargs:
                download.download_quality = kwargs['download_quality']
            
            if 'download_time' in kwargs:
                download.download_time = kwargs['download_time']
            
            if status == 'completed':
                download.completed_at = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Updated download {download_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating download status: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_user_stats(telegram_id):
        """Get user download statistics"""
        try:
            user = User.query.filter_by(telegram_id=telegram_id).first()
            if not user:
                return None
            
            total_downloads = Download.query.filter_by(telegram_id=telegram_id).count()
            successful_downloads = Download.query.filter_by(
                telegram_id=telegram_id, 
                status='completed'
            ).count()
            failed_downloads = Download.query.filter_by(
                telegram_id=telegram_id, 
                status='failed'
            ).count()
            
            # Calculate total bytes downloaded
            total_bytes = db.session.query(func.sum(Download.file_size)).filter_by(
                telegram_id=telegram_id,
                status='completed'
            ).scalar() or 0
            
            return {
                'user': user.to_dict(),
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'failed_downloads': failed_downloads,
                'total_bytes_downloaded': total_bytes,
                'success_rate': (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return None
    
    @staticmethod
    def update_daily_stats():
        """Update daily bot statistics"""
        try:
            today = date.today()
            
            # Get or create today's stats record
            stats = BotStats.query.filter_by(date=today).first()
            if not stats:
                stats = BotStats(date=today)
                db.session.add(stats)
            
            # Calculate stats
            stats.total_users = User.query.count()
            stats.new_users = User.query.filter(
                func.date(User.created_at) == today
            ).count()
            stats.active_users = User.query.filter(
                func.date(User.last_activity) == today
            ).count()
            
            # Download stats
            today_downloads = Download.query.filter(
                func.date(Download.requested_at) == today
            )
            
            stats.total_downloads = today_downloads.count()
            stats.successful_downloads = today_downloads.filter_by(status='completed').count()
            stats.failed_downloads = today_downloads.filter_by(status='failed').count()
            
            # Platform breakdown
            stats.youtube_downloads = today_downloads.filter_by(
                video_platform='youtube', status='completed'
            ).count()
            stats.instagram_downloads = today_downloads.filter_by(
                video_platform='instagram', status='completed'
            ).count()
            stats.tiktok_downloads = today_downloads.filter_by(
                video_platform='tiktok', status='completed'
            ).count()
            stats.twitter_downloads = today_downloads.filter_by(
                video_platform='twitter', status='completed'
            ).count()
            stats.other_downloads = today_downloads.filter(
                ~Download.video_platform.in_(['youtube', 'instagram', 'tiktok', 'twitter']),
                Download.status == 'completed'
            ).count()
            
            # File size stats
            total_bytes = db.session.query(func.sum(Download.file_size)).filter(
                func.date(Download.requested_at) == today,
                Download.status == 'completed'
            ).scalar() or 0
            
            stats.total_bytes_downloaded = total_bytes
            if stats.successful_downloads > 0:
                stats.average_file_size = total_bytes / stats.successful_downloads
            
            stats.updated_at = datetime.utcnow()
            db.session.commit()
            
            logger.info(f"Updated daily stats for {today}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating daily stats: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_recent_downloads(limit=10):
        """Get recent downloads for monitoring"""
        try:
            downloads = Download.query.order_by(
                Download.requested_at.desc()
            ).limit(limit).all()
            
            return [download.to_dict() for download in downloads]
            
        except Exception as e:
            logger.error(f"Error getting recent downloads: {str(e)}")
            return []
    
    @staticmethod
    def get_bot_overview():
        """Get overall bot statistics"""
        try:
            total_users = User.query.count()
            active_users_today = User.query.filter(
                func.date(User.last_activity) == date.today()
            ).count()
            
            total_downloads = Download.query.count()
            successful_downloads = Download.query.filter_by(status='completed').count()
            
            # Platform breakdown (all time)
            platform_stats = db.session.query(
                Download.video_platform,
                func.count(Download.id).label('count')
            ).filter_by(status='completed').group_by(Download.video_platform).all()
            
            platform_breakdown = {platform: count for platform, count in platform_stats}
            
            return {
                'total_users': total_users,
                'active_users_today': active_users_today,
                'total_downloads': total_downloads,
                'successful_downloads': successful_downloads,
                'success_rate': (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0,
                'platform_breakdown': platform_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error getting bot overview: {str(e)}")
            return {}