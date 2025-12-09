#!/usr/bin/env python3
"""
Database models for Lululemon Scraper - Enterprise Edition
Using Flask-SQLAlchemy for ORM
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' or 'user'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_login = db.Column(db.DateTime)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    scraping_history = db.relationship('ScrapingHistory', backref='user', lazy='dynamic')
    email_recipients = db.relationship('EmailRecipient', backref='added_by_user', lazy='dynamic')
    
    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if user is an admin"""
        return self.role == 'admin'
    
    def generate_reset_token(self):
        """Generate a 6-digit OTP for password reset"""
        import secrets
        # Generate 6-digit OTP
        self.reset_token = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        # Token expires in 10 minutes (more secure than 1 hour)
        from datetime import timedelta
        self.reset_token_expires = datetime.now() + timedelta(minutes=10)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """Verify if reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if self.reset_token != token:
            return False
        if datetime.now() > self.reset_token_expires:
            return False
        return True
    
    def clear_reset_token(self):
        """Clear reset token after password reset"""
        self.reset_token = None
        self.reset_token_expires = None
    
    def __repr__(self):
        return f'<User {self.email}>'


class ScrapingHistory(db.Model):
    """History of scraping runs"""
    __tablename__ = 'scraping_history'
    
    id = db.Column(db.Integer, primary_key=True)
    trigger_type = db.Column(db.String(20), nullable=False)  # 'manual' or 'scheduled'
    triggered_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'running', 'completed', 'failed'
    started_at = db.Column(db.DateTime, default=datetime.now)
    completed_at = db.Column(db.DateTime)
    excel_filename = db.Column(db.String(255))
    file_size = db.Column(db.Integer)  # in bytes
    total_products = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ScrapingHistory {self.id} - {self.status}>'


class EmailRecipient(db.Model):
    """Email recipients for automated reports"""
    __tablename__ = 'email_recipients'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    added_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<EmailRecipient {self.email}>'


class Schedule(db.Model):
    """Scraping schedules with timezone support"""
    __tablename__ = 'schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # User-friendly schedule name
    frequency = db.Column(db.String(20), nullable=False)  # 'daily', '3-day', 'weekly', 'monthly'
    time_of_day = db.Column(db.String(5), nullable=False)  # HH:MM format (24-hour)
    timezone = db.Column(db.String(50), nullable=False, default='UTC')  # IANA timezone (e.g., 'America/New_York')
    is_enabled = db.Column(db.Boolean, default=True)
    send_email = db.Column(db.Boolean, default=True)  # Whether to send email after scraping
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    last_run = db.Column(db.DateTime)
    next_run = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<Schedule {self.name} ({self.frequency}) - {"enabled" if self.is_enabled else "disabled"}>'


class EmailSettings(db.Model):
    """SMTP email configuration"""
    __tablename__ = 'email_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    smtp_host = db.Column(db.String(255))
    smtp_port = db.Column(db.Integer)
    smtp_username = db.Column(db.String(255))
    smtp_password = db.Column(db.String(255))
    from_email = db.Column(db.String(120))
    from_name = db.Column(db.String(100))
    is_enabled = db.Column(db.Boolean, default=False)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<EmailSettings {self.smtp_host}>'


class LululemonCredentials(db.Model):
    """Lululemon account credentials for scraping"""
    __tablename__ = 'lululemon_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def __repr__(self):
        return f'<LululemonCredentials {self.username}>'


def init_db(app):
    """Initialize database and create all tables"""
    import os
    from pathlib import Path
    
    # Set umask to allow all users to read/write
    # This ensures any files created have open permissions
    old_umask = os.umask(0)
    
    try:
        with app.app_context():
            # Ensure instance directory exists with proper permissions
            try:
                db_uri = app.config['SQLALCHEMY_DATABASE_URI']
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri.replace('sqlite:///', '')
                    db_dir = os.path.dirname(db_path)
                    
                    # Create directory with full permissions if it doesn't exist
                    if not os.path.exists(db_dir):
                        os.makedirs(db_dir, mode=0o777, exist_ok=True)
                    else:
                        # Ensure directory has proper permissions
                        os.chmod(db_dir, 0o777)
            except Exception as e:
                print(f"⚠️  Warning setting directory permissions: {e}")
            
            # Create all tables
            db.create_all()
            
            # Set permissions for database and all related files
            try:
                db_uri = app.config['SQLALCHEMY_DATABASE_URI']
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri.replace('sqlite:///', '')
                    
                    # Set permissions for main database file
                    if os.path.exists(db_path):
                        os.chmod(db_path, 0o666)  # rw-rw-rw-
                        print(f"✅ Database initialized: {db_path}")
                        
                        # Set permissions for SQLite journal files if they exist
                        for suffix in ['-journal', '-wal', '-shm']:
                            journal_path = db_path + suffix
                            if os.path.exists(journal_path):
                                os.chmod(journal_path, 0o666)
                    else:
                        print(f"✅ Database will be created: {db_path}")
            except Exception as e:
                print(f"⚠️  Database initialized but could not set permissions: {e}")
    finally:
        # Restore original umask
        os.umask(old_umask)

