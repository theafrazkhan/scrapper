#!/usr/bin/env python3
"""
Authentication utilities for Lululemon Scraper - Enterprise Edition
Creates default admin user and provides helper functions
"""

from database import db, User, EmailRecipient


def create_default_admin():
    """Create default admin user if it doesn't exist"""
    admin_email = 'Joe@aureaclubs.com'
    
    # Check if admin exists
    admin = User.query.filter_by(email=admin_email).first()
    
    if not admin:
        admin = User(
            email=admin_email,
            role='admin'
        )
        admin.set_password('admin123')  # Default password - should be changed!
        
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ Created default admin user: {admin_email}")
        print("⚠️  Default password is 'admin123' - PLEASE CHANGE IT!")
    else:
        print(f"ℹ️  Admin user already exists: {admin_email}")
    
    # Get admin user (either just created or existing)
    admin = User.query.filter_by(email=admin_email).first()
    
    # Create default email recipient
    recipient = EmailRecipient.query.filter_by(email=admin_email).first()
    if not recipient and admin:
        recipient = EmailRecipient(
            email=admin_email,
            is_active=True,
            added_by=admin.id
        )
        db.session.add(recipient)
        db.session.commit()
        print(f"✅ Added {admin_email} as default email recipient")

