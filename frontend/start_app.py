#!/usr/bin/env python3
"""
Start Flask app with proper database setup and permissions
This ensures the database is created with correct permissions before starting
"""

import os
import sys
from pathlib import Path

# Get the directory paths
frontend_dir = Path(__file__).parent
instance_dir = frontend_dir / 'instance'
db_path = instance_dir / 'scraper.db'

print("="*70)
print("🚀 Lululemon Scraper - Starting Flask App")
print("="*70)

# Step 1: Create instance directory with proper permissions
print("\n1. Setting up instance directory...")
instance_dir.mkdir(exist_ok=True, mode=0o775)
os.chmod(instance_dir, 0o775)
print(f"   ✓ Instance directory: {instance_dir}")

# Step 2: Check/fix database permissions if exists
if db_path.exists():
    print("\n2. Checking database permissions...")
    try:
        current_mode = oct(os.stat(db_path).st_mode)[-3:]
        print(f"   Current permissions: {current_mode}")
        
        os.chmod(db_path, 0o666)
        print(f"   ✓ Updated to: 666 (rw-rw-rw-)")
    except Exception as e:
        print(f"   ⚠️  Could not update permissions: {e}")
else:
    print("\n2. Database will be created on first run...")

# Step 3: Import and start Flask app
print("\n3. Starting Flask application...")
print("-"*70)

sys.path.insert(0, str(frontend_dir))

try:
    from app import app, socketio
    
    print("\n✅ Flask app loaded successfully!")
    print("\n" + "="*70)
    print("🌐 Server Information")
    print("="*70)
    print(f"   URL: http://0.0.0.0:5000")
    print(f"   Database: {db_path}")
    print(f"   Admin: admin@scraper.local / admin123")
    print("="*70)
    print("\n⚡ Server is starting...\n")
    
    # Start server
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5000, 
        debug=False, 
        allow_unsafe_werkzeug=True
    )
    
except Exception as e:
    print(f"\n❌ Error starting Flask app: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
