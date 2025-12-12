# backend/app/services/alert_notification.py
from typing import Dict, Any, List
import json
from datetime import datetime

from app.models.alert import Alert, AlertHistory
from app.services.websocket_broadcaster import broadcaster


class AlertNotificationService:
    """
    Service for sending alert notifications.
    
    Supports:
    - WebSocket notifications (real-time)
    - Email notifications (future)
    """
    
    async def send_alert_notification(
        self,
        alert: Alert,
        history: AlertHistory
    ):
        """
        Send notification for a triggered alert.
        
        Args:
            alert: Alert that triggered
            history: AlertHistory record
        """
        notification_channels = alert.notification_channels or {}
        
        # Prepare notification payload
        notification = {
            "type": "alert",
            "alert_id": str(alert.id),
            "alert_name": alert.name,
            "severity": history.severity,
            "message": history.message,
            "context": history.context,
            "triggered_at": history.triggered_at.isoformat(),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send via WebSocket
        if notification_channels.get("websocket", True):
            await self._send_websocket_notification(
                client_id=str(alert.client_id),
                notification=notification
            )
        
        # Send via Email (if configured)
        email_addresses = notification_channels.get("email")
        if email_addresses and isinstance(email_addresses, list):
            await self._send_email_notification(
                email_addresses=email_addresses,
                notification=notification
            )
    
    async def _send_websocket_notification(
        self,
        client_id: str,
        notification: Dict[str, Any]
    ):
        """
        Send alert via WebSocket.
        
        Args:
            client_id: Client UUID
            notification: Notification payload
        """
        try:
            # Publish to Redis (broadcaster will pick it up)
            await broadcaster.publish_alert(client_id, notification)
            print(f"🚨 Alert notification sent via WebSocket: {notification['alert_name']}")
        
        except Exception as e:
            print(f"❌ Failed to send WebSocket notification: {e}")
    
    async def _send_email_notification(
        self,
        email_addresses: List[str],
        notification: Dict[str, Any]
    ):
        """
        Send alert via email.
        
        TODO: Implement actual email sending (SMTP, SendGrid, etc.)
        
        Args:
            email_addresses: List of recipient emails
            notification: Notification payload
        """
        # For now, just log (we'll implement email in post-launch)
        print(f"📧 Email notification would be sent to: {', '.join(email_addresses)}")
        print(f"   Subject: [EventPulse] Alert: {notification['alert_name']}")
        print(f"   Message: {notification['message']}")
        
        # TODO: Implement using SMTP or email service
        # Example with SMTP:
        # import smtplib
        # from email.mime.text import MIMEText
        # ...


# Global instance
alert_notification_service = AlertNotificationService()