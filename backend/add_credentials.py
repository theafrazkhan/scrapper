#!/usr/bin/env python3
"""
Add or update Lululemon credentials in the database.
This script can be run standalone to add credentials without using the web interface.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Add frontend directory to path
frontend_dir = Path(__file__).parent.parent / 'frontend'
sys.path.insert(0, str(frontend_dir))

def add_or_update_credentials(username, password):
    """
    Add or update Lululemon credentials in the database.
    """
    try:
        from flask import Flask
        from database import db, LululemonCredentials
        from datetime import datetime
        
        # Get database URL from environment
        DATABASE_URL = os.environ.get('DATABASE_URL')
        if not DATABASE_URL:
            print("❌ ERROR: DATABASE_URL environment variable is not set!")
            print("   Please set DATABASE_URL in your .env file")
            return False
        
        # Handle postgres:// vs postgresql:// schemes
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
        # Create minimal Flask app
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Initialize database
        db.init_app(app)
        
        with app.app_context():
            # Check if credentials already exist
            creds = LululemonCredentials.query.filter_by(is_active=True).first()
            
            if creds:
                print(f"Found existing credentials for: {creds.username}")
                print("Updating...")
                creds.username = username
                creds.password = password
                creds.updated_at = datetime.now()
                action = "Updated"
            else:
                print("No existing credentials found. Creating new...")
                creds = LululemonCredentials(
                    username=username,
                    password=password,
                    is_active=True
                )
                db.session.add(creds)
                action = "Added"
            
            db.session.commit()
            
            print(f"\n✅ {action} credentials successfully!")
            print(f"   Username: {creds.username}")
            print(f"   Password: {'*' * len(creds.password)}")
            
            return True
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function for interactive credential entry"""
    print("="*70)
    print("Lululemon Credentials Manager")
    print("="*70)
    print()
    
    if len(sys.argv) == 3:
        # Command line arguments provided
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        # Interactive mode
        print("This will add/update Lululemon wholesale credentials in the database.")
        print()
        
        username = input("Enter Lululemon wholesale email: ").strip()
        if not username:
            print("❌ Username cannot be empty")
            sys.exit(1)
        
        password = input("Enter Lululemon wholesale password: ").strip()
        if not password:
            print("❌ Password cannot be empty")
            sys.exit(1)
        
        print()
    
    # Add or update credentials
    success = add_or_update_credentials(username, password)
    
    if success:
        print("\n" + "="*70)
        print("You can now run the scraper!")
        print("="*70)
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
