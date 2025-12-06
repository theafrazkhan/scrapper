#!/usr/bin/env python3
"""
Lululemon Scraper - Enterprise Edition
With User Management, Scheduling, and Email Automation
"""

import os
import sys
import threading
import subprocess
import glob
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file, redirect, url_for, flash
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

# Import our modules
from database import db, User, ScrapingHistory, EmailRecipient, Schedule, EmailSettings, LululemonCredentials, init_db
from auth import create_default_admin
from email_service import send_excel_email, send_test_email, get_email_config

# Add backend directory to path
backend_dir = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_dir))

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///scraper.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Initialize extensions
db.init_app(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Setup Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Global state
scraping_active = False
scraping_process = None
scraping_stats = {
    'status': 'idle',
    'progress': 0,
    'current_category': '',
    'products_scraped': 0,
    'total_products': 0,
    'excel_file': None,
    'error': None
}


def parse_log_to_user_message(log_line):
    """
    Convert technical log messages to user-friendly messages.
    Returns tuple: (user_message, should_display)
    """
    line = log_line.strip()
    
    # Skip technical/verbose logs
    if not line:
        return None, False
    
    # Skip timestamp lines at the start
    if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', line):
        return None, False
    
    # Skip separator lines
    if re.match(r'^[=\-]{20,}$', line):
        return None, False
    
    # Extract message from logging format (2025-12-06 18:26:53,368 - INFO - message)
    log_match = re.match(r'^[\d\-: ,]+ - (?:INFO|ERROR|WARNING|DEBUG) - (.+)$', line)
    if log_match:
        line = log_match.group(1).strip()
    
    # Map technical messages to user-friendly ones
    friendly_mappings = {
        # Pipeline stages
        'LULULEMON WHOLESALE SCRAPER PIPELINE': '🍋 Starting Lululemon scraper...',
        'Pipeline started': '✨ Initializing scraper...',
        'STEP 1:': '🔐 Logging into Lululemon wholesale portal...',
        'STEP 2:': '🔗 Finding product links...',
        'STEP 3:': '📥 Downloading product information...',
        'STEP 4:': '📊 Creating your Excel report...',
        
        # Login phase
        '✓ Login successful': '✅ Successfully logged in!',
        'Login successful': '✅ Successfully logged in!',
        '✓ Cookies saved': '🍪 Session saved',
        'Cookies saved': '🍪 Session saved',
        'Setting up Chrome': '🌐 Preparing browser...',
        'Installing/updating ChromeDriver': '🔧 Setting up browser driver...',
        '✓ Chrome WebDriver initialized': '✅ Browser ready',
        'Navigating to': '🔐 Accessing login page...',
        'Looking for email': '⏳ Waiting for login form...',
        'Entering email': '📧 Entering credentials...',
        'Entering password': '🔑 Authenticating...',
        'Clicking login': '🔐 Logging in...',
        
        # Category extraction
        'Extracting product count': '🔢 Counting products...',
        'Category page loaded': '✅ Category loaded',
        
        # Product links
        'Extracting links': '🔍 Scanning for products...',
        'Downloading category page': '📄 Loading category...',
        'Found product links': '✓ Products found',
        
        # Download phase
        'Downloading HTML': '📥 Fetching product details...',
        'Downloaded page': '✓ Product downloaded',
        
        # Excel generation
        'Generating Excel': '📊 Building your report...',
        'Extracting product data': '📋 Processing products...',
        'Excel report generated': '✅ Report ready!',
        '✅ PIPELINE COMPLETED': '🎉 All done! Your data is ready.',
        'PIPELINE COMPLETED': '🎉 All done! Your data is ready.',
        '🎉 All done': '🎉 All done! Your data is ready.',
    }
    
    # Check for friendly mappings
    for pattern, message in friendly_mappings.items():
        if pattern in line:
            return message, True
    
    # Handle download progress with numbers
    if 'Downloaded' in line and '/' in line:
        match = re.search(r'(\d+)/(\d+)', line)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            return f'📥 Downloaded {current} of {total} products...', True
    
    # Handle category mentions
    if any(cat in line.lower() for cat in ['women', 'men', 'accessories', 'supplies']):
        for cat in ['women', 'men', 'accessories', 'supplies']:
            if cat in line.lower() and 'category' in line.lower():
                return f'🔍 Scanning {cat.title()} category...', True
    
    # Skip technical/verbose patterns
    skip_patterns = [
        'Log file:',
        'Full path:',
        'site-packages',
        'DeprecationWarning',
        'FutureWarning',
        '/home/',
        '/usr/',
        'python3',
        '.py:',
        'Traceback',
        '__main__',
    ]
    
    for pattern in skip_patterns:
        if pattern in line:
            return None, False
    
    # If line has checkmarks or emojis, it's user-friendly - show it
    if any(char in line for char in ['✓', '✅', '❌', '⚠️', '📊', '📥', '🔍', '🔐', '🌐', '🍋', '🎉', '🔧', '📧', '🔑', '🍪', '📄', '🔢']):
        return line, True
    
    # Show short informative messages (but skip very technical ones)
    if len(line) < 80 and not any(x in line for x in ['http://', 'https://', '.py', '(', ')', '{', '}', '[', ']']):
        # This might be a useful message, show it
        return f'ℹ️ {line}', True
    
    # Default: skip
    return None, False


def run_backend_pipeline(user_id):
    """Run the existing backend pipeline script"""
    global scraping_active, scraping_process, scraping_stats
    
    with app.app_context():
        try:
            # Create scraping history record
            history = ScrapingHistory(
                trigger_type='manual',
                triggered_by=user_id,
                status='running',
                started_at=datetime.now()
            )
            db.session.add(history)
            db.session.commit()
            
            # Run the existing run_pipeline.py script
            pipeline_script = backend_dir / 'run_pipeline.py'
            
            scraping_process = subprocess.Popen(
                [sys.executable, str(pipeline_script)],
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            # Stream output and parse progress
            for line in scraping_process.stdout:
                # Check if process should stop
                if not scraping_active:
                    break
                    
                line = line.strip()
                if line:
                    # Convert technical log to user-friendly message
                    user_message, should_display = parse_log_to_user_message(line)
                    
                    # Only emit user-friendly messages
                    if should_display and user_message:
                        socketio.emit('scraping_progress', {
                            'message': user_message,
                            'type': 'info'
                        })
                    
                    # Parse specific progress messages
                    if 'Downloaded' in line and '/' in line:
                        try:
                            # Extract numbers like "Downloaded 50/531 pages"
                            match = re.search(r'(\d+)/(\d+)', line)
                            if match:
                                current = int(match.group(1))
                                total = int(match.group(2))
                                scraping_stats['products_scraped'] = current
                                scraping_stats['total_products'] = total
                                scraping_stats['progress'] = int((current / total) * 100) if total > 0 else 0
                                
                                socketio.emit('scraping_progress', {
                                    'downloaded': current,
                                    'total': total,
                                    'percentage': scraping_stats['progress']
                                })
                        except:
                            pass
                    
                    # Track category progress
                    if 'Downloading' in line or any(cat in line.lower() for cat in ['women', 'men', 'accessories', 'supplies']):
                        for category in ['men', 'women', 'accessories', 'supplies']:
                            if category in line.lower():
                                scraping_stats['current_category'] = category.title()
                                socketio.emit('scraping_progress', {
                                    'category': category.title()
                                })
            
            scraping_process.wait()
            
            # Check if process was stopped by user
            if not scraping_active:
                # Update history as cancelled
                try:
                    history.status = 'cancelled'
                    history.completed_at = datetime.now()
                    history.error_message = 'Stopped by user'
                    db.session.commit()
                except:
                    pass
                
                socketio.emit('scraping_stopped', {
                    'message': 'Scraping was stopped by user'
                })
                return
            
            if scraping_process.returncode == 0:
                # Find the generated Excel file in data/results/
                results_dir = backend_dir / "data" / "results"
                excel_files = glob.glob(str(results_dir / "all_products_*.xlsx"))
                if excel_files:
                    latest_excel = max(excel_files, key=os.path.getctime)
                    excel_filename = os.path.basename(latest_excel)
                    file_size = os.path.getsize(latest_excel)
                    
                    scraping_stats['excel_file'] = excel_filename
                    
                    # Update history
                    history.status = 'completed'
                    history.completed_at = datetime.now()
                    history.excel_filename = excel_filename
                    history.file_size = file_size
                    history.total_products = scraping_stats['total_products']
                    db.session.commit()
                    
                    # Emit completion
                    socketio.emit('scraping_complete', {
                        'total_products': scraping_stats['total_products'],
                        'excel_file': excel_filename
                    })
                    
                    socketio.emit('scraping_progress', {
                        'message': '✅ Scraping completed successfully!',
                        'type': 'success'
                    })
                    
                    # Auto-send email to active recipients
                    try:
                        recipients = EmailRecipient.query.filter_by(is_active=True).all()
                        if recipients:
                            recipient_emails = [r.email for r in recipients]
                            
                            # Prepare stats for email
                            elapsed = None
                            if history.started_at and history.completed_at:
                                delta = history.completed_at - history.started_at
                                elapsed = f"{delta.seconds // 60}m {delta.seconds % 60}s"
                            
                            email_stats = {
                                'total_products': history.total_products or 'N/A',
                                'categories': 'All Categories',
                                'elapsed_time': elapsed or 'N/A',
                                'started_at': history.started_at.strftime("%B %d, %Y at %I:%M %p"),
                                'completed_at': history.completed_at.strftime("%B %d, %Y at %I:%M %p")
                            }
                            
                            # Send email in background
                            socketio.emit('scraping_progress', {
                                'message': f'📧 Sending results to {len(recipient_emails)} recipient(s)...',
                                'type': 'info'
                            })
                            
                            email_result = send_excel_email(recipient_emails, latest_excel, email_stats)
                            
                            if email_result['success']:
                                socketio.emit('scraping_progress', {
                                    'message': f'✅ Email sent successfully to {len(email_result["sent"])} recipient(s)',
                                    'type': 'success'
                                })
                            else:
                                socketio.emit('scraping_progress', {
                                    'message': f'⚠️ Email sending failed: {email_result.get("error", "Unknown error")}',
                                    'type': 'warning'
                                })
                    except Exception as email_error:
                        print(f"Email sending error: {email_error}")
                        socketio.emit('scraping_progress', {
                            'message': f'⚠️ Email error: {str(email_error)}',
                            'type': 'warning'
                        })
            else:
                # Process failed with non-zero exit code
                raise Exception(f"Pipeline failed with exit code {scraping_process.returncode}")
            
        except Exception as e:
            print(f"Scraping error: {e}")
            
            # Don't log as error if it was cancelled by user
            if not scraping_active:
                return
            
            # Update history
            try:
                history.status = 'failed'
                history.completed_at = datetime.now()
                history.error_message = str(e)
                db.session.commit()
            except:
                pass
            
            socketio.emit('scraping_error', {
                'message': str(e)
            })
        
        finally:
            scraping_active = False
            scraping_process = None
            scraping_stats['status'] = 'idle'


# Routes
@app.route('/')
def index():
    """Serve the main page - shows login or dashboard based on auth status"""
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.now()
            db.session.commit()
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'redirect': url_for('index')
                })
            return redirect(url_for('index'))
        
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'Invalid email or password'
            }), 401
        
        flash('Invalid email or password', 'error')
    
    # Redirect to index page which has the themed login section
    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    return redirect(url_for('login'))


@app.route('/history')
@login_required
def history():
    """View scraping history"""
    if current_user.role == 'admin':
        history_records = ScrapingHistory.query.order_by(ScrapingHistory.started_at.desc()).all()
    else:
        history_records = ScrapingHistory.query.filter_by(triggered_by=current_user.id).order_by(ScrapingHistory.started_at.desc()).all()
    
    return render_template('history.html', history=history_records, user=current_user)


@app.route('/settings')
@login_required
def settings():
    """Settings page - includes user management, email & schedule configuration"""
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    users = User.query.all()
    email_recipients = EmailRecipient.query.filter_by(is_active=True).all()
    schedules = Schedule.query.all()
    
    return render_template('settings.html', 
                         users=users,
                         recipients=email_recipients,
                         schedules=schedules,
                         user=current_user)


# API Routes
@app.route('/api/status')
def api_status():
    """Get current scraping status and login status"""
    return jsonify({
        'active': scraping_active,
        'stats': scraping_stats,
        'logged_in': current_user.is_authenticated,
        'user': {
            'email': current_user.email,
            'role': current_user.role
        } if current_user.is_authenticated else None
    })


@app.route('/api/login', methods=['POST'])
def api_login():
    """Handle API login - validates user credentials"""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400
    
    # Validate against database
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        # Log the user in with Flask-Login
        login_user(user, remember=True)
        
        return jsonify({
            'success': True,
            'message': 'Login successful',
            'user': {
                'email': user.email,
                'role': user.role
            }
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Handle API logout"""
    logout_user()
    return jsonify({'success': True})


@app.route('/api/start_scraping', methods=['POST'])
def start_scraping():
    """Start the scraping process"""
    global scraping_active
    
    if scraping_active:
        return jsonify({'success': False, 'message': 'Scraping already in progress'}), 400
    
    scraping_active = True
    
    # Reset stats
    scraping_stats.update({
        'status': 'running',
        'progress': 0,
        'current_category': '',
        'products_scraped': 0,
        'total_products': 0,
        'excel_file': None,
        'error': None
    })
    
    # Start scraping in background thread
    # Use a dummy user_id=1 for now (will track in future)
    thread = threading.Thread(target=run_backend_pipeline, args=(1,))
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'message': 'Scraping started'})


@app.route('/api/stop_scraping', methods=['POST'])
def stop_scraping():
    """Stop the scraping process"""
    global scraping_active, scraping_process
    
    if not scraping_active and not scraping_process:
        return jsonify({'success': False, 'message': 'No scraping process is running'}), 400
    
    scraping_active = False
    
    if scraping_process:
        try:
            # Send SIGTERM to gracefully stop the process
            scraping_process.terminate()
            
            # Wait a bit for graceful shutdown
            try:
                scraping_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't stop gracefully
                scraping_process.kill()
                scraping_process.wait()
            
            scraping_process = None
            
            socketio.emit('scraping_progress', {
                'message': '⚠️ Scraping stopped by user',
                'type': 'warning'
            })
            
            socketio.emit('scraping_stopped', {
                'message': 'Scraping process has been stopped'
            })
            
        except Exception as e:
            print(f"Error stopping process: {e}")
            return jsonify({'success': False, 'message': f'Error stopping process: {str(e)}'}), 500
    
    return jsonify({'success': True, 'message': 'Scraping stopped successfully'})


@app.route('/api/download_excel')
def download_excel():
    """Download the latest generated Excel file"""
    excel_file = request.args.get('file', scraping_stats.get('excel_file'))
    
    results_dir = backend_dir / "data" / "results"
    
    if not excel_file:
        # Get latest file from results directory
        excel_files = glob.glob(str(results_dir / "all_products_*.xlsx"))
        if not excel_files:
            return jsonify({'error': 'No Excel file available'}), 404
        latest_excel = max(excel_files, key=os.path.getctime)
        excel_file = os.path.basename(latest_excel)
    
    file_path = results_dir / excel_file
    
    if not file_path.exists():
        return jsonify({'error': 'Excel file not found'}), 404
    
    return send_file(
        str(file_path),
        as_attachment=True,
        download_name=excel_file
    )


@app.route('/api/history/recent')
def get_recent_history():
    """Get recent scraping history"""
    try:
        limit = request.args.get('limit', 5, type=int)
        history = ScrapingHistory.query.order_by(ScrapingHistory.started_at.desc()).limit(limit).all()
        
        return jsonify({
            'success': True,
            'history': [{
                'id': h.id,
                'trigger_type': h.trigger_type,
                'status': h.status,
                'started_at': h.started_at.isoformat() if h.started_at else None,
                'completed_at': h.completed_at.isoformat() if h.completed_at else None,
                'excel_filename': h.excel_filename,
                'total_products': h.total_products,
                'file_size': h.file_size
            } for h in history]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Email API Routes
@app.route('/api/email/config')
def email_config():
    """Get email configuration"""
    try:
        config = get_email_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/test', methods=['POST'])
@login_required
def test_email():
    """Send test email"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'success': False, 'error': 'Email address required'}), 400
        
        result = send_test_email(email)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/email/send-results', methods=['POST'])
@login_required
def send_scraping_results():
    """Send latest scraping results via email"""
    try:
        data = request.get_json()
        emails = data.get('emails', [])
        
        if not emails:
            # Get active recipients from database
            recipients = EmailRecipient.query.filter_by(is_active=True).all()
            emails = [r.email for r in recipients]
        
        if not emails:
            return jsonify({
                'success': False,
                'error': 'No recipient emails provided or configured'
            }), 400
        
        # Get the latest Excel file from results directory
        results_dir = backend_dir / 'data' / 'results'
        excel_files = glob.glob(str(results_dir / 'all_products_*.xlsx'))
        if not excel_files:
            return jsonify({
                'success': False,
                'error': 'No Excel file found to send'
            }), 404
        
        latest_file = max(excel_files, key=os.path.getctime)
        
        # Get latest scraping history for stats
        history = ScrapingHistory.query.order_by(ScrapingHistory.started_at.desc()).first()
        
        scraping_stats = None
        if history:
            elapsed = None
            if history.started_at and history.completed_at:
                delta = history.completed_at - history.started_at
                elapsed = f"{delta.seconds // 60}m {delta.seconds % 60}s"
            
            scraping_stats = {
                'total_products': history.total_products or 'N/A',
                'categories': 'All Categories',
                'elapsed_time': elapsed or 'N/A',
                'started_at': history.started_at.strftime("%B %d, %Y at %I:%M %p") if history.started_at else 'N/A',
                'completed_at': history.completed_at.strftime("%B %d, %Y at %I:%M %p") if history.completed_at else 'N/A'
            }
        
        # Send email
        result = send_excel_email(emails, latest_file, scraping_stats)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# Admin API Routes
@app.route('/api/admin/users', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_users():
    """Manage users - admin only"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        users = User.query.all()
        return jsonify([{
            'id': u.id,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'last_login': u.last_login.isoformat() if u.last_login else None
        } for u in users])
    
    elif request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        role = data.get('role', 'user')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User already exists'}), 400
        
        user = User(email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'User created',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role
            }
        })
    
    elif request.method == 'DELETE':
        data = request.get_json()
        user_id = data.get('id')
        
        if not user_id:
            return jsonify({'error': 'User ID required'}), 400
        
        # Can't delete yourself or the main admin
        if user_id == current_user.id:
            return jsonify({'error': 'Cannot delete your own account'}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if user.email == 'Joe@aureaclubs.com':
            return jsonify({'error': 'Cannot delete main admin'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'User deleted'})


@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """Delete a user"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    # Can't delete yourself or the main admin
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': 'Cannot delete your own account'}), 400
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    if user.email == 'Joe@aureaclubs.com':
        return jsonify({'success': False, 'error': 'Cannot delete main admin'}), 400
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'User deleted'})


@app.route('/api/admin/email_recipients', methods=['GET', 'POST', 'DELETE'])
@login_required
def manage_email_recipients():
    """Manage email recipients - admin only"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        recipients = EmailRecipient.query.filter_by(is_active=True).all()
        return jsonify([{
            'id': r.id,
            'email': r.email,
            'added_at': r.added_at.isoformat() if r.added_at else None
        } for r in recipients])
    
    elif request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email required'}), 400
        
        recipient = EmailRecipient(
            email=email,
            added_by=current_user.id
        )
        db.session.add(recipient)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Email recipient added'})
    
    elif request.method == 'DELETE':
        data = request.get_json()
        recipient_id = data.get('id')
        
        if not recipient_id:
            return jsonify({'error': 'Recipient ID required'}), 400
        
        recipient = EmailRecipient.query.get(recipient_id)
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404
        
        recipient.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Email recipient removed'})


@app.route('/api/admin/recipients', methods=['POST'])
@login_required
def add_recipient():
    """Add email recipient"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    email = data.get('email')
    
    if not email:
        return jsonify({'success': False, 'error': 'Email required'}), 400
    
    # Check if already exists
    existing = EmailRecipient.query.filter_by(email=email).first()
    if existing:
        return jsonify({'success': False, 'error': 'Email already exists'}), 400
    
    recipient = EmailRecipient(
        email=email,
        added_by=current_user.id,
        is_active=True
    )
    db.session.add(recipient)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Email recipient added'})


@app.route('/api/admin/recipients/<int:recipient_id>', methods=['PUT', 'DELETE'])
@login_required
def manage_recipient(recipient_id):
    """Update or delete email recipient"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    recipient = EmailRecipient.query.get(recipient_id)
    if not recipient:
        return jsonify({'success': False, 'error': 'Recipient not found'}), 404
    
    if request.method == 'PUT':
        data = request.get_json()
        is_active = data.get('is_active')
        
        if is_active is not None:
            recipient.is_active = is_active
            db.session.commit()
            return jsonify({'success': True, 'message': 'Recipient updated'})
        
        return jsonify({'success': False, 'error': 'No update data provided'}), 400
    
    elif request.method == 'DELETE':
        db.session.delete(recipient)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Recipient deleted'})


# ============================================================================
# LULULEMON CREDENTIALS MANAGEMENT
# ============================================================================

@app.route('/api/admin/env-credentials', methods=['GET'])
@login_required
def get_env_credentials():
    """Get Lululemon credentials from .env file (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        env_path = Path(__file__).parent.parent / '.env'
        
        email = None
        password = None
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('WHOLESALE_EMAIL='):
                        email = line.split('=', 1)[1]
                    elif line.startswith('WHOLESALE_PASSWORD='):
                        password = line.split('=', 1)[1]
        
        return jsonify({
            'success': True,
            'credentials': {
                'email': email,
                'password': password
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/env-credentials', methods=['POST'])
@login_required
def update_env_credentials():
    """Update Lululemon credentials in .env file (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({
                'success': False,
                'error': 'Email and password are required'
            }), 400
        
        env_path = Path(__file__).parent.parent / '.env'
        
        # Read existing content
        lines = []
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        
        # Update or add credentials
        email_found = False
        password_found = False
        updated_lines = []
        
        for line in lines:
            if line.strip().startswith('WHOLESALE_EMAIL='):
                updated_lines.append(f'WHOLESALE_EMAIL={email}\n')
                email_found = True
            elif line.strip().startswith('WHOLESALE_PASSWORD='):
                updated_lines.append(f'WHOLESALE_PASSWORD={password}\n')
                password_found = True
            else:
                updated_lines.append(line)
        
        # Add if not found
        if not email_found:
            updated_lines.append(f'WHOLESALE_EMAIL={email}\n')
        if not password_found:
            updated_lines.append(f'WHOLESALE_PASSWORD={password}\n')
        
        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)
        
        # Update environment variables for current process
        os.environ['WHOLESALE_EMAIL'] = email
        os.environ['WHOLESALE_PASSWORD'] = password
        
        return jsonify({
            'success': True,
            'message': 'Credentials updated successfully in .env file'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/lululemon-credentials', methods=['GET'])
@login_required
def get_lululemon_credentials():
    """Get Lululemon credentials (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    creds = LululemonCredentials.query.filter_by(is_active=True).first()
    if creds:
        return jsonify({
            'success': True,
            'credentials': {
                'id': creds.id,
                'username': creds.username,
                'password': creds.password,  # Return actual password for editing
                'last_used': creds.last_used.isoformat() if creds.last_used else None,
                'updated_at': creds.updated_at.isoformat() if creds.updated_at else None
            }
        })
    return jsonify({
        'success': True,
        'credentials': None
    })

@app.route('/api/admin/lululemon-credentials', methods=['POST', 'PUT'])
@login_required
def update_lululemon_credentials():
    """Update Lululemon credentials (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Get or create credentials in database
        creds = LululemonCredentials.query.filter_by(is_active=True).first()
        
        if creds:
            # Update existing
            creds.username = username
            creds.password = password
            creds.updated_by = current_user.id
            creds.updated_at = datetime.now()
        else:
            # Create new
            creds = LululemonCredentials(
                username=username,
                password=password,
                updated_by=current_user.id
            )
            db.session.add(creds)
        
        db.session.commit()
        
        # Also update .env file for backend script compatibility
        try:
            env_path = Path(__file__).parent.parent / '.env'
            
            # Read existing content
            lines = []
            if env_path.exists():
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            
            # Update or add credentials
            email_found = False
            password_found = False
            updated_lines = []
            
            for line in lines:
                if line.strip().startswith('WHOLESALE_EMAIL='):
                    updated_lines.append(f'WHOLESALE_EMAIL={username}\n')
                    email_found = True
                elif line.strip().startswith('WHOLESALE_PASSWORD='):
                    updated_lines.append(f'WHOLESALE_PASSWORD={password}\n')
                    password_found = True
                else:
                    updated_lines.append(line)
            
            # Add if not found
            if not updated_lines or updated_lines[0].strip() != '# Environment variables for Lululemon Wholesale Scraper':
                updated_lines.insert(0, '# Environment variables for Lululemon Wholesale Scraper\n')
            
            if not email_found:
                updated_lines.append(f'WHOLESALE_EMAIL={username}\n')
            if not password_found:
                updated_lines.append(f'WHOLESALE_PASSWORD={password}\n')
            
            # Write back to file
            with open(env_path, 'w') as f:
                f.writelines(updated_lines)
            
            # Update environment variables for current process
            os.environ['WHOLESALE_EMAIL'] = username
            os.environ['WHOLESALE_PASSWORD'] = password
            
        except Exception as env_error:
            # Log the error but don't fail the request
            print(f"Warning: Failed to update .env file: {env_error}")
        
        return jsonify({
            'success': True,
            'message': 'Credentials saved successfully'
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Email Configuration Management Routes
@app.route('/api/admin/email-config', methods=['GET', 'POST'])
@login_required
def manage_email_config():
    """Get or update email configuration (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    if request.method == 'GET':
        try:
            # Try to get from EmailSettings table
            email_settings = EmailSettings.query.first()
            
            if email_settings:
                return jsonify({
                    'success': True,
                    'config': {
                        'provider': 'Resend',
                        'api_key': email_settings.smtp_password,  # Using smtp_password field for API key
                        'from_email': email_settings.from_email,
                        'from_name': 'Lululemon Scraper',  # Default
                        'domain': email_settings.from_email.split('@')[1] if email_settings.from_email and '@' in email_settings.from_email else ''
                    }
                })
            else:
                # Return current hardcoded config if no DB entry
                from email_service import RESEND_API_KEY, FROM_EMAIL, FROM_NAME, DOMAIN
                return jsonify({
                    'success': True,
                    'config': {
                        'provider': 'Resend',
                        'api_key': RESEND_API_KEY,
                        'from_email': FROM_EMAIL,
                        'from_name': FROM_NAME,
                        'domain': DOMAIN
                    }
                })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            api_key = data.get('api_key')
            from_email = data.get('from_email')
            from_name = data.get('from_name')
            domain = data.get('domain')
            
            if not all([api_key, from_email, from_name, domain]):
                return jsonify({
                    'success': False,
                    'error': 'All fields are required'
                }), 400
            
            # Check if settings exist
            email_settings = EmailSettings.query.first()
            
            if email_settings:
                # Update existing
                email_settings.smtp_password = api_key
                email_settings.from_email = from_email
                email_settings.is_enabled = True
            else:
                # Create new
                email_settings = EmailSettings(
                    smtp_host='api.resend.com',
                    smtp_port=587,
                    smtp_username='resend',
                    smtp_password=api_key,
                    from_email=from_email,
                    is_enabled=True
                )
                db.session.add(email_settings)
            
            db.session.commit()
            
            # Update email_service.py file to use these values
            try:
                email_service_path = os.path.join(os.path.dirname(__file__), 'email_service.py')
                
                if os.path.exists(email_service_path):
                    with open(email_service_path, 'r') as f:
                        content = f.read()
                    
                    # Update the constants
                    import re
                    content = re.sub(
                        r'RESEND_API_KEY\s*=\s*["\'].*?["\']',
                        f'RESEND_API_KEY = "{api_key}"',
                        content
                    )
                    content = re.sub(
                        r'FROM_EMAIL\s*=\s*["\'].*?["\']',
                        f'FROM_EMAIL = "{from_email}"',
                        content
                    )
                    content = re.sub(
                        r'FROM_NAME\s*=\s*["\'].*?["\']',
                        f'FROM_NAME = "{from_name}"',
                        content
                    )
                    content = re.sub(
                        r'DOMAIN\s*=\s*["\'].*?["\']',
                        f'DOMAIN = "{domain}"',
                        content
                    )
                    
                    with open(email_service_path, 'w') as f:
                        f.write(content)
            
            except Exception as file_error:
                print(f"Warning: Failed to update email_service.py: {file_error}")
            
            return jsonify({
                'success': True,
                'message': 'Email configuration updated successfully'
            })
        
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500


@app.route('/api/admin/lululemon-credentials/test', methods=['POST'])
@login_required
def test_lululemon_credentials():
    """Test Lululemon credentials by attempting login (admin only)"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Test by running the login script
        result = subprocess.run(
            ['python3', str(backend_dir / 'login_and_save_cookies.py'), username, password],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Update last_used timestamp
            creds = LululemonCredentials.query.filter_by(username=username, is_active=True).first()
            if creds:
                creds.last_used = datetime.now()
                db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Credentials verified successfully! Login cookies saved.'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Login failed: {result.stderr or result.stdout}'
            }), 400
    
    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Login test timed out after 30 seconds'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# WEBSOCKET EVENTS
# ============================================================================

# WebSocket events
@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')


# Initialize database and create default admin
with app.app_context():
    init_db(app)
    create_default_admin()


if __name__ == '__main__':
    print("🚀 Starting Lululemon Scraper - Enterprise Edition")
    print("📍 Server running at: http://localhost:5000")
    print("👤 Default admin: Joe@aureaclubs.com / admin123")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

