# How to Add Lululemon Credentials to Database

There are **3 ways** to add your Lululemon wholesale credentials to the database.

---

## ✅ Method 1: Command Line (Easiest)

### Interactive Mode
```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 add_credentials.py
```

Then enter your credentials when prompted:
```
Enter Lululemon wholesale email: your-email@company.com
Enter Lululemon wholesale password: your-password
```

### Non-Interactive Mode (for scripts)
```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 add_credentials.py "your-email@company.com" "your-password"
```

**Output:**
```
======================================================================
Lululemon Credentials Manager
======================================================================

No existing credentials found. Creating new...

✅ Added credentials successfully!
   Username: your-email@company.com
   Password: ************
   Database: /home/theafrazkhan/Desktop/scrappin/frontend/instance/scraper.db
```

---

## 🌐 Method 2: Web Interface (Most User-Friendly)

### Step 1: Start the Flask Web Server
```bash
cd /home/theafrazkhan/Desktop/scrappin/frontend
python3 app.py
```

### Step 2: Open Browser
Navigate to: `http://localhost:5000`

### Step 3: Login
- **Default Admin Credentials:**
  - Email: `admin@scraper.local`
  - Password: `admin123`

### Step 4: Go to Settings
1. Click on **"Settings"** in the navigation menu
2. Scroll down to **"Lululemon Credentials"** section
3. Enter your credentials:
   - **Username:** your-email@company.com
   - **Password:** your-password
4. Click **"Save Credentials"**
5. Optionally click **"Test Credentials"** to verify they work

**Features:**
- ✅ Test credentials before saving
- ✅ Visual feedback
- ✅ Easy to update later
- ✅ Admin-only access

---

## 🐍 Method 3: Python Script (For Automation)

Create a file `setup_credentials.py`:

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# Add frontend directory to path
frontend_dir = Path(__file__).parent / 'frontend'
sys.path.insert(0, str(frontend_dir))

from flask import Flask
from database import db, LululemonCredentials

# Your credentials
USERNAME = "your-email@company.com"
PASSWORD = "your-password"

# Create minimal Flask app
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{frontend_dir}/instance/scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    # Check if credentials exist
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    
    if creds:
        print(f"Updating existing credentials for: {creds.username}")
        creds.username = USERNAME
        creds.password = PASSWORD
    else:
        print("Creating new credentials...")
        creds = LululemonCredentials(
            username=USERNAME,
            password=PASSWORD,
            is_active=True
        )
        db.session.add(creds)
    
    db.session.commit()
    print(f"✅ Credentials saved for: {USERNAME}")
```

Then run:
```bash
python3 setup_credentials.py
```

---

## 📋 Verification

### Check if credentials are in database:
```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / 'frontend'))

from flask import Flask
from database import db, LululemonCredentials

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../frontend/instance/scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    if creds:
        print(f'✅ Credentials found:')
        print(f'   Username: {creds.username}')
        print(f'   Password: {\"*\" * len(creds.password)}')
        print(f'   Active: {creds.is_active}')
    else:
        print('❌ No credentials found in database')
"
```

### Test credentials work:
```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 login_and_save_cookies.py
```

If successful, you'll see:
```
✓ Login successful
✓ Cookies saved to: data/cookie/cookie.json
```

---

## 🔄 Update Existing Credentials

To update credentials, just run any of the above methods again. The script will:
1. Detect existing credentials
2. Update them with new values
3. Keep the same database record

---

## 🗑️ Remove Credentials

```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd().parent / 'frontend'))

from flask import Flask
from database import db, LululemonCredentials

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../frontend/instance/scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

with app.app_context():
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    if creds:
        db.session.delete(creds)
        db.session.commit()
        print('✅ Credentials removed')
    else:
        print('⚠️  No credentials found')
"
```

---

## 📍 Database Location

Your credentials are stored in:
```
/home/theafrazkhan/Desktop/scrappin/frontend/instance/scraper.db
```

**Database Table:** `lululemon_credentials`

**Schema:**
```sql
CREATE TABLE lululemon_credentials (
    id INTEGER PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_used TIMESTAMP
);
```

---

## 🔐 Security Notes

1. **Permissions:** Make sure only you can read the database file
   ```bash
   chmod 600 /home/theafrazkhan/Desktop/scrappin/frontend/instance/scraper.db
   ```

2. **Passwords:** Stored in plain text (consider encrypting in production)

3. **Access:** Only admin users can view/edit credentials via web interface

4. **Backup:** Keep a backup of your credentials securely

---

## ❓ Troubleshooting

### "No module named 'database'"
```bash
cd /home/theafrazkhan/Desktop/scrappin/backend
# Make sure you're in the backend folder
python3 add_credentials.py
```

### "Database not found"
```bash
# Create the database first
cd /home/theafrazkhan/Desktop/scrappin/frontend
python3 migrate_db.py
```

### "Credentials not working"
```bash
# Test with login script
cd /home/theafrazkhan/Desktop/scrappin/backend
python3 login_and_save_cookies.py
```

If login fails, check:
- Username is correct (full email)
- Password has no extra spaces
- Account is active on Lululemon wholesale site
- You can login manually at https://wholesale.lululemon.com/

---

## 📚 Related Files

- **Add/Update:** `backend/add_credentials.py`
- **Database Utils:** `backend/db_credentials.py`
- **Database Models:** `frontend/database.py`
- **Web Interface:** `frontend/app.py`
- **Login Script:** `backend/login_and_save_cookies.py`

---

**Last Updated:** December 9, 2025
