#!/usr/bin/env python3
"""
Database migration script to add password reset columns
"""

import sqlite3
from pathlib import Path

def migrate_database():
    """Add reset_token and reset_token_expires columns to users table"""
    
    db_path = Path(__file__).parent / 'instance' / 'scraper.db'
    
    if not db_path.exists():
        print("❌ Database not found at:", db_path)
        return False
    
    print(f"📦 Migrating database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'reset_token' in columns and 'reset_token_expires' in columns:
            print("✅ Columns already exist. No migration needed.")
            conn.close()
            return True
        
        # Add reset_token column if it doesn't exist
        if 'reset_token' not in columns:
            print("➕ Adding reset_token column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN reset_token VARCHAR(100)
            """)
            print("✅ Added reset_token column")
        
        # Add reset_token_expires column if it doesn't exist
        if 'reset_token_expires' not in columns:
            print("➕ Adding reset_token_expires column...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN reset_token_expires DATETIME
            """)
            print("✅ Added reset_token_expires column")
        
        conn.commit()
        conn.close()
        
        print("\n" + "="*60)
        print("✅ Database migration completed successfully!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("="*60)
    print("Database Migration - Add Password Reset Columns")
    print("="*60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\n✅ You can now run the application with:")
        print("   python3 app.py")
    else:
        print("\n❌ Migration failed. Please check the error above.")
    
    exit(0 if success else 1)
