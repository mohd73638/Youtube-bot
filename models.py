"""
Database models for the Telegram video downloader bot
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    """User model to track bot users"""
    __tablename__ = "users"
    
    id = db.Column(db.BigInteger, primary_key=True)  # Telegram user ID
    username = db.Column(db.String(255), nullable=True)
    first_name = db.Column(db.String(255), nullable=True)
    last_name = db.Column(db.String(255), nullable=True)
    language_code = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_active = db.Column(db.DateTime, default=datetime.utcnow)
    total_downloads = db.Column(db.Integer, default=0)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Relationship with downloads
    downloads = db.relationship("Download", backref="user", lazy=True)
    
    def __repr__(self):
        return f"<User {self.id}: {self.username or self.first_name}>"

class Download(db.Model):
    """Download history model"""
    __tablename__ = "downloads"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=False)
    url = db.Column(db.Text, nullable=False)
    platform = db.Column(db.String(100), nullable=False)
    title = db.Column(db.Text, nullable=True)
    file_size = db.Column(db.BigInteger, nullable=True)  # in bytes
    download_time = db.Column(db.Float, nullable=True)  # in seconds
    status = db.Column(db.String(50), nullable=False)  # success, failed, file_too_large, etc.
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<Download {self.id}: {self.platform} - {self.status}>"

class BotStats(db.Model):
    """Bot statistics model"""
    __tablename__ = "bot_stats"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, unique=True, nullable=False)
    total_users = db.Column(db.Integer, default=0)
    new_users = db.Column(db.Integer, default=0)
    total_downloads = db.Column(db.Integer, default=0)
    successful_downloads = db.Column(db.Integer, default=0)
    failed_downloads = db.Column(db.Integer, default=0)
    most_popular_platform = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<BotStats {self.date}: {self.total_downloads} downloads>"
