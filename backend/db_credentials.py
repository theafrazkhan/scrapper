#!/usr/bin/env python3
"""
Utility to fetch Lululemon credentials from the frontend database.
This allows the backend scraping scripts to use credentials stored in the database
instead of relying on .env files.
"""

import sys
import os
from pathlib import Path

# Add frontend directory to path to access database module
frontend_dir = Path(__file__).parent.parent / 'frontend'
sys.path.insert(0, str(frontend_dir))

def get_database_url():
    """Get database URL from environment or .env file"""
    # First check environment variable
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        # Try loading from .env file
        try:
            from dotenv import load_dotenv
            env_path = Path(__file__).parent.parent / '.env'
            if env_path.exists():
                load_dotenv(env_path)
                database_url = os.environ.get('DATABASE_URL')
        except ImportError:
            pass
    
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set!")
    
    # Handle postgres:// vs postgresql:// schemes
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    return database_url

def get_credentials():
    """
    Fetch active Lululemon credentials from database.
    Returns tuple: (username, password) or (None, None) if not found.
    """
    try:
        # Import Flask and database after path is set
        from flask import Flask
        from database import db, LululemonCredentials
        
        # Get database URL from environment
        database_url = get_database_url()
        
        # Create minimal Flask app to access database
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Get active credentials
            creds = LululemonCredentials.query.filter_by(is_active=True).first()
            
            if creds:
                return (creds.username, creds.password)
            else:
                return (None, None)
                
    except Exception as e:
        print(f"Error fetching credentials from database: {e}")
        import traceback
        traceback.print_exc()
        return (None, None)


def update_last_used():
    """
    Update the last_used timestamp for the active credentials.
    Call this after successfully using credentials.
    """
    try:
        from flask import Flask
        from database import db, LululemonCredentials
        from datetime import datetime
        
        database_url = get_database_url()
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        
        with app.app_context():
            creds = LululemonCredentials.query.filter_by(is_active=True).first()
            if creds:
                creds.last_used = datetime.now()
                db.session.commit()
                
    except Exception as e:
        print(f"Warning: Could not update credentials timestamp: {e}")


if __name__ == "__main__":
    """Test the credential fetching"""
    username, password = get_credentials()
    
    if username and password:
        print(f"✅ Found credentials for: {username}")
        print(f"   Password length: {len(password)} characters")
    else:
        print("❌ No active credentials found in database")
        print(f"   Database location: {frontend_dir}/instance/scraper.db")
