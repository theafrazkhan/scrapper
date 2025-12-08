#!/usr/bin/env python3
"""
Quick credentials setup - Just edit the values below and run this script
"""
import sys
from pathlib import Path

# ==========================================
# EDIT THESE VALUES WITH YOUR CREDENTIALS
# ==========================================
USERNAME = "Joe@aureaclubs.com"  # Change this
PASSWORD = "Joeilaspa455!"        # Change this
# ==========================================

# Add frontend directory to path
frontend_dir = Path(__file__).parent / 'frontend'
sys.path.insert(0, str(frontend_dir))

from flask import Flask
from database import db, LululemonCredentials
from datetime import datetime

print("="*70)
print("Quick Credentials Setup")
print("="*70)

# Create minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{frontend_dir}/instance/scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Check if credentials exist
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    
    if creds:
        print(f"\nFound existing credentials for: {creds.username}")
        print("Updating...")
        creds.username = USERNAME
        creds.password = PASSWORD
        creds.updated_at = datetime.now()
        action = "Updated"
    else:
        print("\nNo existing credentials found. Creating new...")
        creds = LululemonCredentials(
            username=USERNAME,
            password=PASSWORD,
            is_active=True
        )
        db.session.add(creds)
        action = "Added"
    
    db.session.commit()
    
    print(f"\n✅ {action} credentials successfully!")
    print(f"   Username: {creds.username}")
    print(f"   Password: {'*' * len(creds.password)}")
    print(f"   Database: {frontend_dir}/instance/scraper.db")
    print("\n" + "="*70)
    print("Next steps:")
    print("  1. Test credentials: python3 backend/login_and_save_cookies.py")
    print("  2. Run pipeline: python3 backend/run_pipeline.py")
    print("="*70)
