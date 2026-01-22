# backend/app/services/email_service.py (NEW FILE)
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from datetime import datetime

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Service for sending emails via SMTP.
    
    Supports:
    - Alert notifications
    - System notifications
    - HTML and plain text emails
    """
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.smtp_from = settings.SMTP_FROM or settings.SMTP_USER
        
        # Check if email is configured
        self.is_configured = all([
            self.smtp_host,
            self.smtp_port,
            self.smtp_user,
            self.smtp_password
        ])
    
    async def send_alert_email(
        self,
        to_addresses: List[str],
        alert_name: str,
        severity: str,
        message: str,
        context: Optional[dict] = None
    ) -> bool:
        """
        Send an alert notification email.
        
        Args:
            to_addresses: List of recipient email addresses
            alert_name: Name of the alert
            severity: Alert severity (info, warning, error, critical)
            message: Alert message
            context: Additional context data
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning("Email not configured, skipping email notification")
            return False
        
        try:
            # Severity emoji mapping
            severity_emoji = {
                "info": "ℹ️",
                "warning": "⚠️",
                "error": "❌",
                "critical": "🚨"
            }
            emoji = severity_emoji.get(severity, "📊")
            
            # Prepare email
            subject = f"{emoji} [EventPulse] {severity.upper()}: {alert_name}"
            
            # HTML body
            html_body = self._create_alert_html(
                alert_name=alert_name,
                severity=severity,
                message=message,
                context=context
            )
            
            # Plain text fallback
            plain_body = f"""
EventPulse Alert Notification

Alert: {alert_name}
Severity: {severity.upper()}
Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{message}

Context:
{context if context else 'N/A'}

---
This is an automated notification from EventPulse Analytics Platform.
            """.strip()
            
            # Send email
            success = await self._send_email(
                to_addresses=to_addresses,
                subject=subject,
                html_body=html_body,
                plain_body=plain_body
            )
            
            if success:
                logger.info(f"Alert email sent to {len(to_addresses)} recipient(s)")
            
            return success
        
        except Exception as e:
            logger.error(f"Failed to send alert email: {e}", exc_info=True)
            return False
    
    def _create_alert_html(
        self,
        alert_name: str,
        severity: str,
        message: str,
        context: Optional[dict]
    ) -> str:
        """Create HTML email template for alerts"""
        
        # Color coding by severity
        colors = {
            "info": "#3b82f6",      # Blue
            "warning": "#f59e0b",   # Orange
            "error": "#ef4444",     # Red
            "critical": "#dc2626"   # Dark red
        }
        color = colors.get(severity, "#6b7280")
        
        context_html = ""
        if context:
            context_html = "<h3>Context:</h3><ul>"
            for key, value in context.items():
                context_html += f"<li><strong>{key}:</strong> {value}</li>"
            context_html += "</ul>"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: {color}; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background-color: #f9fafb; padding: 20px; border-radius: 0 0 8px 8px; }}
        .severity {{ display: inline-block; padding: 4px 12px; background-color: {color}; color: white; border-radius: 4px; font-weight: bold; }}
        .message {{ background-color: white; padding: 15px; border-left: 4px solid {color}; margin: 15px 0; }}
        .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">EventPulse Alert</h1>
        </div>
        <div class="content">
            <h2>{alert_name}</h2>
            <p><span class="severity">{severity.upper()}</span></p>
            <p><strong>Time:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            
            <div class="message">
                <h3>Message:</h3>
                <p>{message}</p>
            </div>
            
            {context_html}
        </div>
        <div class="footer">
            <p>This is an automated notification from EventPulse Analytics Platform.</p>
        </div>
    </div>
</body>
</html>
        """.strip()
    
    async def _send_email(
        self,
        to_addresses: List[str],
        subject: str,
        html_body: str,
        plain_body: str
    ) -> bool:
        """
        Send email via SMTP.
        
        Args:
            to_addresses: List of recipients
            subject: Email subject
            html_body: HTML version
            plain_body: Plain text version
            
        Returns:
            True if successful
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.smtp_from
            msg['To'] = ', '.join(to_addresses)
            msg['Subject'] = subject
            
            # Attach both plain and HTML versions
            part1 = MIMEText(plain_body, 'plain')
            part2 = MIMEText(html_body, 'html')
            msg.attach(part1)
            msg.attach(part2)
            
            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                # Use TLS if port 587
                if self.smtp_port == 587:
                    server.starttls()
                
                # Login
                server.login(self.smtp_user, self.smtp_password)
                
                # Send
                server.send_message(msg)
            
            return True
        
        except Exception as e:
            logger.error(f"SMTP error: {e}", exc_info=True)
            return False


# Global email service instance
email_service = EmailService()