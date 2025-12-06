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
        subject = f"Lululemon Product Scraping Results - {timestamp}"
        
        # Build HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .stats {{ background: white; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .stat-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .stat-row:last-child {{ border-bottom: none; }}
                .stat-label {{ font-weight: 600; color: #666; }}
                .stat-value {{ color: #ff6b35; font-weight: bold; }}
                .file-info {{ background: #fff4e6; border-left: 4px solid #ff6b35; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .footer {{ text-align: center; color: #999; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
                .icon {{ color: #ff6b35; margin-right: 8px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚡ Lululemon Product Scraping Complete</h1>
                </div>
                <div class="content">
                    <p>Hello,</p>
                    <p>Your Lululemon wholesale product scraping has completed successfully. The results are attached as an Excel file.</p>
        """
        
        # Add stats if provided
        if scraping_stats:
            html_body += """
                    <div class="stats">
                        <h3 style="margin-top: 0; color: #333;">📊 Scraping Statistics</h3>
            """
            
            stats_items = [
                ('Total Products', scraping_stats.get('total_products', 'N/A')),
                ('Categories Scraped', scraping_stats.get('categories', 'N/A')),
                ('Time Taken', scraping_stats.get('elapsed_time', 'N/A')),
                ('Started At', scraping_stats.get('started_at', 'N/A')),
                ('Completed At', scraping_stats.get('completed_at', 'N/A'))
            ]
            
            for label, value in stats_items:
                html_body += f"""
                        <div class="stat-row">
                            <span class="stat-label">{label}:</span>
                            <span class="stat-value">{value}</span>
                        </div>
                """
            
            html_body += """
                    </div>
            """
        
        # File info
        html_body += f"""
                    <div class="file-info">
                        <strong>📎 Attachment Details</strong><br>
                        <span class="icon">📄</span> File Name: {file_name}<br>
                        <span class="icon">💾</span> File Size: {file_size_mb} MB
                    </div>
                    
                    <p>The Excel file contains detailed product information including:</p>
                    <ul>
                        <li>Product names and SKUs</li>
                        <li>Prices and wholesale rates</li>
                        <li>Colors and sizes available</li>
                        <li>Product categories</li>
                        <li>Direct product links</li>
                    </ul>
                    
                    <p>If you have any questions or need assistance, please don't hesitate to reach out.</p>
                    
                    <p>Best regards,<br>
                    <strong>Lululemon Scraper Team</strong></p>
                    
                    <div class="footer">
                        <p>This is an automated email from Lululemon Scraper Enterprise Edition.</p>
                        <p>© {datetime.now().year} Lululemon Scraper. All rights reserved.</p>
                    </div>
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
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 30px; border-radius: 10px; text-align: center; }
                .content { padding: 30px 0; }
                .success-icon { font-size: 48px; text-align: center; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚡ Email Configuration Test</h1>
                </div>
                <div class="content">
                    <div class="success-icon">✅</div>
                    <h2 style="text-align: center; color: #ff6b35;">Success!</h2>
                    <p>This is a test email from Lululemon Scraper Enterprise Edition.</p>
                    <p>If you're reading this, your email configuration is working correctly!</p>
                    <ul>
                        <li>✓ SMTP connection established</li>
                        <li>✓ Authentication successful</li>
                        <li>✓ Email delivery confirmed</li>
                    </ul>
                    <p>You can now receive automated scraping reports.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        response = resend.Emails.send({
            "from": f"{FROM_NAME} <{FROM_EMAIL}>",
            "to": [to_email],
            "subject": "Lululemon Scraper - Email Test ✓",
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
