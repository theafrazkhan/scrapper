"""
Migration script to make email_recipients.added_by nullable
and add ON DELETE SET NULL constraint
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend'))

from database import db
from sqlalchemy import text

def migrate():
    """Apply migration"""
    try:
        # Drop the existing foreign key constraint
        db.session.execute(text("""
            ALTER TABLE email_recipients 
            DROP CONSTRAINT IF EXISTS email_recipients_added_by_fkey;
        """))
        
        # Make the column nullable
        db.session.execute(text("""
            ALTER TABLE email_recipients 
            ALTER COLUMN added_by DROP NOT NULL;
        """))
        
        # Re-add the foreign key constraint with ON DELETE SET NULL
        db.session.execute(text("""
            ALTER TABLE email_recipients 
            ADD CONSTRAINT email_recipients_added_by_fkey 
            FOREIGN KEY (added_by) 
            REFERENCES users(id) 
            ON DELETE SET NULL;
        """))
        
        db.session.commit()
        print("✅ Migration completed successfully!")
        print("   - made email_recipients.added_by nullable")
        print("   - added ON DELETE SET NULL constraint")
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    from app import app
    with app.app_context():
        migrate()
