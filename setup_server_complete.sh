#!/bin/bash
# Complete server setup and permission fix
# Run this on your server: bash setup_server_complete.sh

echo "========================================================================"
echo "Lululemon Scraper - Complete Server Setup"
echo "========================================================================"

# Navigate to project
cd /srv/scrapper || {
    echo "❌ Error: /srv/scrapper directory not found"
    exit 1
}

# Get current user
CURRENT_USER=$(whoami)
echo "Running as user: $CURRENT_USER"

# Step 1: Stop Flask if running
echo ""
echo "Step 1: Stopping any running Flask app..."
pkill -f "python.*app.py" 2>/dev/null && echo "  Stopped Flask app" || echo "  No Flask app running"
sleep 2

# Step 2: Fix all ownership
echo ""
echo "Step 2: Fixing file ownership..."
if [ "$CURRENT_USER" = "root" ]; then
    echo "  Running as root - setting ownership to root"
    chown -R root:root /srv/scrapper
else
    echo "  Setting ownership to $CURRENT_USER"
    sudo chown -R $CURRENT_USER:$CURRENT_USER /srv/scrapper 2>/dev/null || {
        echo "  ⚠️  Cannot use sudo - trying without it"
        chown -R $CURRENT_USER:$CURRENT_USER /srv/scrapper
    }
fi

# Step 3: Create all necessary directories
echo ""
echo "Step 3: Creating directories..."
mkdir -p frontend/instance
mkdir -p backend/data/{cookie,categories,html,results}
mkdir -p backend/logs
echo "  ✓ Directories created"

# Step 4: Set directory permissions
echo ""
echo "Step 4: Setting directory permissions..."
chmod 755 frontend
chmod 775 frontend/instance
chmod 755 backend
chmod 775 backend/data
chmod 775 backend/data/cookie
chmod 775 backend/data/categories
chmod 775 backend/data/html
chmod 775 backend/data/results
chmod 775 backend/logs
echo "  ✓ Directory permissions set"

# Step 5: Fix database permissions
echo ""
echo "Step 5: Fixing database file permissions..."
if [ -f "frontend/instance/scraper.db" ]; then
    chmod 666 frontend/instance/scraper.db  # More permissive
    chmod 666 frontend/instance/*.db* 2>/dev/null || true
    echo "  ✓ Database file: $(ls -lh frontend/instance/scraper.db | awk '{print $1, $3, $4, $9}')"
else
    echo "  ⚠️  Database file not found - will be created on first run"
fi

# Step 6: Fix any SELinux issues (if on CentOS/RHEL)
if command -v getenforce &> /dev/null; then
    if [ "$(getenforce)" != "Disabled" ]; then
        echo ""
        echo "Step 6: Fixing SELinux context..."
        chcon -R -t httpd_sys_rw_content_t /srv/scrapper/frontend/instance 2>/dev/null || true
        echo "  ✓ SELinux context updated"
    fi
fi

# Step 7: Test database access
echo ""
echo "Step 7: Testing database access..."
python3 << 'PYTHON_EOF'
import sys
import os
import sqlite3
from pathlib import Path

db_path = Path('/srv/scrapper/frontend/instance/scraper.db')

if not db_path.exists():
    print("  Creating new database...")
    # Create database with proper permissions
    conn = sqlite3.connect(str(db_path))
    conn.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()
    os.chmod(str(db_path), 0o666)
    print(f"  ✓ Database created: {db_path}")

# Test write access
try:
    conn = sqlite3.connect(str(db_path))
    conn.execute('SELECT 1')
    conn.execute('CREATE TABLE IF NOT EXISTS write_test (id INTEGER)')
    conn.commit()
    conn.close()
    print("  ✓ Database is writable")
except Exception as e:
    print(f"  ❌ Database write failed: {e}")
    sys.exit(1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ Database test failed!"
    echo "Manual fix required:"
    echo "  sudo chmod 666 /srv/scrapper/frontend/instance/scraper.db"
    exit 1
fi

# Step 8: Install dependencies
echo ""
echo "Step 8: Checking Python dependencies..."
source venv/bin/activate 2>/dev/null || {
    echo "  ⚠️  Virtual environment not activated"
    echo "  Run: source /srv/scrapper/venv/bin/activate"
}

# Check if key packages are installed
python3 -c "import flask_sqlalchemy" 2>/dev/null || {
    echo "  Installing frontend dependencies..."
    pip install -q flask flask-sqlalchemy flask-login flask-cors flask-socketio
}

python3 -c "import playwright" 2>/dev/null || {
    echo "  Installing backend dependencies..."
    pip install -q playwright beautifulsoup4 openpyxl
}

echo "  ✓ Dependencies checked"

# Final summary
echo ""
echo "========================================================================"
echo "✅ Setup Complete!"
echo "========================================================================"
echo ""
echo "Current permissions:"
echo "  Frontend instance: $(ls -ld frontend/instance | awk '{print $1, $3, $4}')"
echo "  Database file:     $(ls -lh frontend/instance/scraper.db 2>/dev/null | awk '{print $1, $3, $4}' || echo 'Not yet created')"
echo ""
echo "Next steps:"
echo "  1. Add credentials:"
echo "     cd /srv/scrapper/backend"
echo "     python3 add_credentials.py Joe@aureaclubs.com Joeilaspa455!"
echo ""
echo "  2. Start Flask app:"
echo "     cd /srv/scrapper/frontend"
echo "     python3 app.py"
echo ""
echo "  3. Or run pipeline:"
echo "     cd /srv/scrapper/backend"
echo "     python3 run_pipeline.py"
echo ""
echo "========================================================================"
