"""Email service for validation requests."""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import Dict, Optional
from src.config import Config


def create_validation_email_html(
    recipient_name: str,
    question: str,
    current_info: Dict,
    entity_name: str,
    response_url: str
) -> str:
    """
    Create professional HTML email with validation form.
    
    Args:
        recipient_name: Name of the recipient
        question: Validation question
        current_info: Current information about the entity
        entity_name: Name of the entity being validated
        response_url: URL for the validation response form
        
    Returns:
        HTML email content
    """
    # Build current info table
    info_rows = ""
    for key, value in current_info.items():
        if key not in ['id', 'tenant_id', 'embedding', 'search_vector']:
            info_rows += f"""
                <tr>
                    <td style="padding: 8px; font-weight: bold; color: #555;">
                        {key.replace('_', ' ').title()}
                    </td>
                    <td style="padding: 8px; color: #333;">
                        {value}
                    </td>
                </tr>
            """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px 10px 0 0;">
            <h1 style="margin: 0; font-size: 24px;">Resource Validation Request</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">Regarding: {entity_name}</p>
        </div>
        
        <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd; border-top: none;">
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                Hi {recipient_name},
            </p>
            
            <p style="font-size: 16px; margin-bottom: 20px;">
                {question}
            </p>
            
            <div style="background: white; border: 1px solid #ddd; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #667eea;">Current Information:</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    {info_rows}
                </table>
            </div>
            
            <p style="font-size: 14px; color: #666; margin: 20px 0;">
                Please review the information above and confirm its accuracy or provide corrections.
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{response_url}" 
                   style="display: inline-block; background: #667eea; color: white; padding: 15px 40px; 
                          text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    Respond to Validation Request
                </a>
            </div>
            
            <p style="font-size: 12px; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
                This validation request will expire in 7 days. If you need more time, please contact the proposal team.
            </p>
            
        </div>
        
    </body>
    </html>
    """
    
    return html


def send_html_email(to_email: str, subject: str, html_body: str) -> None:
    """
    Send HTML email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email body
    """
    if not Config.SMTP_HOST:
        raise ValueError("SMTP configuration not available")
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = Config.EMAIL_FROM or "proposals@example.com"
    msg['To'] = to_email
    
    # Attach HTML body
    msg.attach(MIMEText(html_body, 'html'))
    
    # Send via SMTP
    with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
        if Config.SMTP_USER and Config.SMTP_PASSWORD:
            server.starttls()
            server.login(Config.SMTP_USER, Config.SMTP_PASSWORD)
        server.send_message(msg)


def generate_validation_token(validation_id: str) -> str:
    """
    Generate secure token for validation response URL.
    
    Args:
        validation_id: ID of the validation request
        
    Returns:
        Secure token string
    """
    import secrets
    import hashlib
    
    token = secrets.token_urlsafe(32)
    
    # In production, store token mapping in database or cache
    # validation_id -> token (expires in 7 days)
    
    return token
