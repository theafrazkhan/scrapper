#!/bin/bash
# Docker initialization script
# This runs when the container starts

echo "================================================"
echo "Lululemon Scraper - Docker Container Starting"
echo "================================================"

# Create necessary directories
mkdir -p /app/frontend/instance
mkdir -p /app/backend/data/results
mkdir -p /app/backend/logs

# Check if database exists
if [ ! -f "/app/frontend/instance/scraper.db" ]; then
    echo "📦 Initializing database..."
    cd /app/frontend
    python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
    echo "✅ Database initialized"
else
    echo "✅ Database already exists"
fi

# Check if credentials exist
cd /app/backend
python3 -c "
import sys
sys.path.insert(0, '/app/frontend')
from database import db, LululemonCredentials
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////app/frontend/instance/scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    if not creds:
        print('⚠️  No Lululemon credentials found!')
        print('   Please add them via the web interface at http://localhost:5000/settings')
        print('   Or use environment variables LULULEMON_USERNAME and LULULEMON_PASSWORD')
    else:
        print(f'✅ Found credentials for: {creds.username}')
" 2>/dev/null || echo "⚠️  Could not check credentials (database may not be initialized yet)"

echo ""
echo "🚀 Starting Flask application..."
echo "================================================"
cd /app/frontend
exec python3 app.py
