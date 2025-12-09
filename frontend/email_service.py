"""
Email Service for Lululemon Scraper
Uses Resend API to send Excel files to recipients
"""

import os
import resend
from pathlib import Path
from datetime import datetime

# Configure Resend API
RESEND_API_KEY = "re_dzPPEveX_B9rbrrcKa3usGcqErFFqiZ5P"
FROM_EMAIL = "scraper@testing.afrazkhan.dev"
FROM_NAME = "Lululemon Scraper"

# Initialize Resend
resend.api_key = RESEND_API_KEY


def send_excel_email(to_emails, excel_path, scraping_stats=None):
    """
    Send Excel file via email to specified recipients
    
    Args:
        to_emails (list): List of recipient email addresses
        excel_path (str): Path to the Excel file to attach
        scraping_stats (dict): Optional stats about the scraping run
        
    Returns:
        dict: Response with success status and details
    """
    try:
        # Validate inputs
        if not to_emails:
            return {
                'success': False,
                'error': 'No recipient emails provided'
            }
        
        if not os.path.exists(excel_path):
            return {
                'success': False,
                'error': f'Excel file not found: {excel_path}'
            }
        
        # Get file info
        file_name = Path(excel_path).name
        file_size = os.path.getsize(excel_path)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        
        # Build email subject and body
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        subject = f"Lululemon Report - {timestamp}"
        
        # Build minimal HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    color: #333;
                    background: #f5f5f5;
                    padding: 20px;
                }}
                .email-container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .header {{ 
                    background: linear-gradient(135deg, #FF6B35 0%, #FFB84D 100%);
                    padding: 30px 20px;
                    text-align: center;
                }}
                .header h1 {{ 
                    color: white;
                    font-size: 24px;
                    font-weight: 600;
                    margin: 0;
                }}
                .content {{ 
                    padding: 30px 20px;
                }}
                .message {{
                    font-size: 16px;
                    color: #555;
                    margin-bottom: 20px;
                }}
                .file-info {{ 
                    background: #f9f9f9;
                    border-left: 4px solid #FF6B35;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 20px 0;
                }}
                .file-name {{
                    font-weight: 600;
                    color: #333;
                    font-size: 14px;
                    margin-bottom: 5px;
                }}
                .file-size {{
                    color: #777;
                    font-size: 13px;
                }}
        """
        
        # Add stats styling only if stats provided
        if scraping_stats:
            html_body += """
                .stats {{
                    margin: 20px 0;
                }}
                .stat-item {{
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #eee;
                    font-size: 14px;
                }}
                .stat-item:last-child {{ border-bottom: none; }}
                .stat-label {{ color: #666; }}
                .stat-value {{ color: #FF6B35; font-weight: 600; }}
            """
        
        html_body += """
                .footer {{ 
                    background: #f9f9f9;
                    text-align: center; 
                    color: #999; 
                    font-size: 12px; 
                    padding: 20px;
                    border-top: 1px solid #eee;
                }}
                .footer a {{
                    color: #FF6B35;
                    text-decoration: none;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <h1>🍋 Lululemon Report</h1>
                </div>
                <div class="content">
                    <div class="message">
                        Your Lululemon product scraping has completed successfully. The Excel file is attached below.
                    </div>
        """
        
        # Add stats if provided (minimal version)
        if scraping_stats:
            html_body += """
                    <div class="stats">
            """
            
            # Only show essential stats
            if scraping_stats.get('total_products'):
                html_body += f"""
                        <div class="stat-item">
                            <span class="stat-label">Products</span>
                            <span class="stat-value">{scraping_stats['total_products']}</span>
                        </div>
                """
            
            if scraping_stats.get('elapsed_time'):
                html_body += f"""
                        <div class="stat-item">
                            <span class="stat-label">Time</span>
                            <span class="stat-value">{scraping_stats['elapsed_time']}</span>
                        </div>
                """
            
            html_body += """
                    </div>
            """
        
        # File info
        html_body += f"""
                    <div class="file-info">
                        <div class="file-name">📎 {file_name}</div>
                        <div class="file-size">Size: {file_size_mb} MB</div>
                    </div>
                </div>
                <div class="footer">
                    <p>Lululemon Scraper</p>
                    <p style="margin-top: 8px;">Built at <a href="https://afrazkhan.dev" target="_blank">afrazkhan.dev</a></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Read the Excel file
        with open(excel_path, 'rb') as f:
            excel_content = f.read()
        
        # Prepare attachments
        attachments = [
            {
                "filename": file_name,
                "content": list(excel_content)  # Resend expects list of bytes
            }
        ]
        
        # Send email to each recipient
        sent_emails = []
        failed_emails = []
        
        for recipient in to_emails:
            try:
                response = resend.Emails.send({
                    "from": f"{FROM_NAME} <{FROM_EMAIL}>",
                    "to": [recipient],
                    "subject": subject,
                    "html": html_body,
                    "attachments": attachments
                })
                
                sent_emails.append({
                    'email': recipient,
                    'id': response.get('id', 'unknown')
                })
                
            except Exception as e:
                failed_emails.append({
                    'email': recipient,
                    'error': str(e)
                })
        
        # Prepare response
        if len(sent_emails) == len(to_emails):
            return {
                'success': True,
                'message': f'Email sent successfully to {len(sent_emails)} recipient(s)',
                'sent': sent_emails,
                'failed': []
            }
        elif len(sent_emails) > 0:
            return {
                'success': True,
                'message': f'Email sent to {len(sent_emails)} out of {len(to_emails)} recipients',
                'sent': sent_emails,
                'failed': failed_emails
            }
        else:
            return {
                'success': False,
                'error': 'Failed to send email to any recipients',
                'failed': failed_emails
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': f'Email sending failed: {str(e)}'
        }


def send_test_email(to_email):
    """
    Send a test email to verify configuration
    
    Args:
        to_email (str): Email address to send test to
        
    Returns:
        dict: Response with success status
    """
    try:
        html_content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
            <style>
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { 
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    line-height: 1.6; 
                    color: #212121;
                    background: #FAFAFA;
                    padding: 40px 20px;
                }
                .email-wrapper { 
                    max-width: 650px; 
                    margin: 0 auto; 
                    background: white;
                    border-radius: 16px;
                    overflow: hidden;
                    box-shadow: 0 20px 60px -15px rgba(0, 0, 0, 0.15);
                }
                .header { 
                    background: linear-gradient(135deg, #FF6B35 0%, #FFB84D 100%);
                    padding: 50px 40px;
                    text-align: center;
                    position: relative;
                    overflow: hidden;
                }
                .header::before {
                    content: '';
                    position: absolute;
                    top: -50%;
                    right: -50%;
                    width: 200%;
                    height: 200%;
                    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
                }
                .header-icon {
                    font-size: 64px;
                    margin-bottom: 16px;
                    display: inline-block;
                    animation: pulse 2s infinite;
                }
                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }
                .header h1 { 
                    color: white;
                    font-size: 28px;
                    font-weight: 800;
                    margin: 0;
                    letter-spacing: -0.5px;
                    position: relative;
                    z-index: 1;
                }
                .header-subtitle {
                    color: rgba(255, 255, 255, 0.95);
                    font-size: 15px;
                    margin-top: 8px;
                    font-weight: 500;
                }
                .content { 
                    padding: 40px;
                    background: white;
                }
                .success-badge {
                    text-align: center;
                    margin: 32px 0;
                }
                .success-icon {
                    font-size: 72px;
                    animation: bounce 1s ease-in-out;
                }
                @keyframes bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-20px); }
                }
                .success-title {
                    font-size: 24px;
                    font-weight: 700;
                    background: linear-gradient(135deg, #10B981 0%, #34D399 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                    margin-top: 16px;
                }
                .message {
                    font-size: 15px;
                    color: #616161;
                    margin: 24px 0;
                    line-height: 1.7;
                    text-align: center;
                }
                .checklist {
                    background: linear-gradient(180deg, #FAFAFA 0%, #F5F5F5 100%);
                    border-radius: 12px;
                    padding: 28px;
                    margin: 32px 0;
                    border: 1px solid #EEEEEE;
                }
                .checklist-title {
                    font-size: 16px;
                    font-weight: 600;
                    color: #212121;
                    margin-bottom: 16px;
                    text-align: center;
                }
                .checklist-items {
                    list-style: none;
                    padding: 0;
                }
                .checklist-items li {
                    padding: 12px 0;
                    padding-left: 32px;
                    position: relative;
                    color: #616161;
                    font-size: 14px;
                }
                .checklist-items li::before {
                    content: '✓';
                    position: absolute;
                    left: 0;
                    color: #10B981;
                    font-weight: 700;
                    font-size: 18px;
                }
                .cta {
                    text-align: center;
                    margin: 32px 0;
                }
                .cta-text {
                    font-size: 15px;
                    color: #616161;
                    font-weight: 500;
                }
                .footer { 
                    background: #FAFAFA;
                    text-align: center; 
                    color: #9E9E9E; 
                    font-size: 13px; 
                    padding: 32px 40px;
                    border-top: 1px solid #EEEEEE;
                }
                .footer-logo {
                    font-size: 24px;
                    margin-bottom: 12px;
                }
                .footer p {
                    margin: 8px 0;
                    line-height: 1.5;
                }
            </style>
        </head>
        <body>
            <div class="email-wrapper">
                <div class="header">
                    <div class="header-icon">🚀</div>
                    <h1>Email Configuration Test</h1>
                    <div class="header-subtitle">Testing your email delivery system</div>
                </div>
                <div class="content">
                    <div class="success-badge">
                        <div class="success-icon">✅</div>
                        <div class="success-title">All Systems Operational!</div>
                    </div>
                    
                    <div class="message">
                        Congratulations! This test email confirms that your Lululemon Scraper email 
                        configuration is working perfectly. You're all set to receive automated scraping reports.
                    </div>
                    
                    <div class="checklist">
                        <div class="checklist-title">✓ Configuration Verified</div>
                        <ul class="checklist-items">
                            <li>Email server connection established</li>
                            <li>Authentication credentials validated</li>
                            <li>Email delivery confirmed successfully</li>
                            <li>HTML rendering working correctly</li>
                            <li>Ready to receive scraping reports</li>
                        </ul>
                    </div>
                    
                    <div class="cta">
                        <div class="cta-text">🎉 You're ready to start scraping!</div>
                    </div>
                </div>
                <div class="footer">
                    <div class="footer-logo">⚡</div>
                    <p><strong>Lululemon Scraper Enterprise Edition</strong></p>
                    <p>This is an automated test email</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        response = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": "✓ Email Configuration Test - Success!",
            "html": html_content
        })
        
        return {
            'success': True,
            'message': f'Test email sent successfully to {to_email}',
            'id': response.get('id', 'unknown')
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f'Test email failed: {str(e)}'
        }


def get_email_config():
    """
    Get current email configuration (without exposing API key)
    
    Returns:
        dict: Email configuration details
    """
    return {
        'provider': 'Resend',
        'from_email': FROM_EMAIL,
        'from_name': FROM_NAME,
        'api_configured': bool(RESEND_API_KEY),
        'domain': 'testing.afrazkhan.dev'
    }
