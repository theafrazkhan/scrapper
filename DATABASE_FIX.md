# Quick Fix for Database Permission Error

## 🚨 The Problem
The Flask app cannot write to the database. This happens when:
- Database file has wrong permissions
- Database directory is not writable
- Flask is running as a different user

## ✅ Quick Fix (Run on Server)

### **Option 1: Single Command Fix**
```bash
cd /srv/scrapper && chmod 775 frontend/instance && chmod 666 frontend/instance/scraper.db && ls -lh frontend/instance/scraper.db
```

### **Option 2: Complete Fix Script**
```bash
cd /srv/scrapper
bash setup_server_complete.sh
```

### **Option 3: Manual Step-by-Step**
```bash
# 1. Navigate to project
cd /srv/scrapper

# 2. Stop Flask app
pkill -f "python.*app.py"

# 3. Fix directory permissions
chmod 775 frontend/instance

# 4. Fix database file permissions
chmod 666 frontend/instance/scraper.db

# 5. Fix ownership (if needed)
sudo chown -R $USER:$USER frontend/instance

# 6. Verify permissions
ls -lh frontend/instance/scraper.db
# Should show: -rw-rw-rw- or similar

# 7. Restart Flask app
cd frontend
python3 app.py
```

## 🔍 Verify It's Fixed

Run this on your server:
```bash
python3 -c "
import sqlite3
db = sqlite3.connect('/srv/scrapper/frontend/instance/scraper.db')
db.execute('SELECT 1')
db.execute('CREATE TABLE IF NOT EXISTS test (id INTEGER)')
db.commit()
print('✅ Database is writable!')
"
```

## 🐛 If Still Not Working

### Check current permissions:
```bash
ls -lh /srv/scrapper/frontend/instance/scraper.db
ls -ld /srv/scrapper/frontend/instance
```

### Nuclear option (most permissive):
```bash
cd /srv/scrapper
sudo chown -R $USER:$USER .
chmod -R 775 frontend/instance
chmod 666 frontend/instance/scraper.db
chmod 666 frontend/instance/*.db* 2>/dev/null || true
```

### Check who's running Flask:
```bash
ps aux | grep "python.*app.py"
```

If Flask is running as root or different user, either:
1. Run Flask as your user: `python3 frontend/app.py`
2. Or fix ownership: `sudo chown root:root frontend/instance/scraper.db`

## 📝 What Each Permission Means

- **775** on directory: Owner and group can read/write/execute
- **666** on database: Everyone can read/write (needed for SQLite)
- **664** on database: Owner and group can read/write (more secure)

## 🎯 Recommended Setup

For production server:
```bash
# Directory: rwxrwxr-x (775)
chmod 775 /srv/scrapper/frontend/instance

# Database: rw-rw-rw- (666) - or rw-rw-r-- (664) if same user
chmod 666 /srv/scrapper/frontend/instance/scraper.db
```

## ⚡ Copy-Paste Solution

**Run these 3 commands on your server:**
```bash
cd /srv/scrapper && chmod 775 frontend/instance && chmod 666 frontend/instance/scraper.db && echo "✅ Permissions fixed!"
```

Then restart your Flask app and try again.

---

**If this still doesn't work, send me:**
```bash
ls -lh /srv/scrapper/frontend/instance/scraper.db
ls -ld /srv/scrapper/frontend/instance
whoami
ps aux | grep python.*app.py
```
