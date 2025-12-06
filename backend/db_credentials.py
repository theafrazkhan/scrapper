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

def get_credentials():
    """
    Fetch active Lululemon credentials from database.
    Returns tuple: (username, password) or (None, None) if not found.
    """
    try:
        # Import Flask and database after path is set
        from flask import Flask
        from database import db, LululemonCredentials
        
        # Create minimal Flask app to access database
        app = Flask(__name__)
        # Use the instance folder database path (Flask default)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{frontend_dir}/instance/scraper.db'
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
        
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{frontend_dir}/instance/scraper.db'
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
