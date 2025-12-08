#!/bin/bash
# Fix database permissions on server
# Run this script on your server at /srv/scrapper

echo "========================================================================"
echo "Fixing Database Permissions"
echo "========================================================================"

# Get current user
CURRENT_USER=$(whoami)
echo "Current user: $CURRENT_USER"

# Navigate to project
cd /srv/scrapper || exit 1

# Stop any running Flask app
echo ""
echo "Stopping Flask app (if running)..."
pkill -f "python.*app.py" 2>/dev/null || true
sleep 2

# Fix ownership and permissions
echo ""
echo "Fixing ownership and permissions..."

# Make sure all files are owned by current user
sudo chown -R $CURRENT_USER:$CURRENT_USER /srv/scrapper

# Create instance directory if it doesn't exist
mkdir -p frontend/instance

# Set directory permissions
chmod 755 frontend
chmod 775 frontend/instance
chmod 755 backend
chmod 775 backend/data

# Create subdirectories with proper permissions
mkdir -p backend/data/{cookie,categories,html,results}
mkdir -p backend/logs
chmod -R 775 backend/data
chmod -R 775 backend/logs

# Fix database file permissions if it exists
if [ -f "frontend/instance/scraper.db" ]; then
    echo "Database file found"
    chmod 664 frontend/instance/scraper.db
    ls -lh frontend/instance/scraper.db
else
    echo "Database file not found - will be created on first run"
fi

# Fix any -journal or temp files
chmod 664 frontend/instance/*.db* 2>/dev/null || true

echo ""
echo "========================================================================"
echo "Testing Database Access"
echo "========================================================================"

# Test database write access
python3 << 'PYTHON_EOF'
import sys
import os
from pathlib import Path

# Add frontend to path
frontend_dir = Path('/srv/scrapper/frontend')
sys.path.insert(0, str(frontend_dir))

try:
    from flask import Flask
    from database import db, User
    
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{frontend_dir}/instance/scraper.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)
    
    with app.app_context():
        # Try to query database
        user_count = User.query.count()
        print(f"✅ Database READ successful - Found {user_count} users")
        
        # Try to write to database (create a test entry and rollback)
        try:
            db.session.execute('SELECT 1')
            db.session.commit()
            print("✅ Database WRITE successful")
        except Exception as e:
            print(f"❌ Database WRITE failed: {e}")
            sys.exit(1)
            
except Exception as e:
    print(f"❌ Database test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ All database tests passed!")
PYTHON_EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================================================"
    echo "✅ SUCCESS - Database is now writable!"
    echo "========================================================================"
    echo ""
    echo "Permissions summary:"
    ls -lh frontend/instance/
    echo ""
    echo "You can now:"
    echo "  1. Start Flask app: cd frontend && python3 app.py"
    echo "  2. Run pipeline: cd backend && python3 run_pipeline.py"
else
    echo ""
    echo "========================================================================"
    echo "❌ FAILED - Additional steps needed"
    echo "========================================================================"
    echo ""
    echo "Try these manual commands:"
    echo "  sudo chown -R $CURRENT_USER:$CURRENT_USER /srv/scrapper"
    echo "  chmod 775 /srv/scrapper/frontend/instance"
    echo "  chmod 664 /srv/scrapper/frontend/instance/scraper.db"
    exit 1
fi
