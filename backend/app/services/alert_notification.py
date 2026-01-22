from typing import Dict, Any, List
from datetime import datetime, timezone

from app.models.alert import Alert, AlertHistory
from app.services.websocket_broadcaster import broadcaster
from app.services.email_service import email_service
from app.logging_config import get_logger

logger = get_logger(__name__)


class AlertNotificationService:
    """Service for sending alert notifications via multiple channels"""

    async def send_alert_notification(
        self,
        alert: Alert,
        history: AlertHistory
    ):
        """Send notification via configured channels"""
        notification_channels = alert.notification_channels or {}

        notification = {
            "type": "alert",
            "alert_id": str(alert.id),
            "alert_name": alert.name,
            "severity": history.severity,
            "message": history.message,
            "context": history.context,
            "triggered_at": history.triggered_at.isoformat(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # WebSocket notification (default: enabled)
        if notification_channels.get("websocket", True):
            await self._send_websocket_notification(
                client_id=str(alert.client_id),
                notification=notification,
            )

        # Email notification (optional)
        email_addresses = notification_channels.get("email")
        if email_addresses and isinstance(email_addresses, list):
            await self._send_email_notification(
                email_addresses=email_addresses,
                alert=alert,
                notification=notification,
            )

    async def _send_websocket_notification(
        self,
        client_id: str,
        notification: Dict[str, Any],
    ):
        """Send alert via WebSocket"""
        try:
            await broadcaster.publish_alert(client_id, notification)
            logger.info(f"🚨 Alert sent via WebSocket: {notification['alert_name']}")
        except Exception as e:
            logger.error(
                f"Failed to send WebSocket notification: {e}",
                exc_info=True,
            )

    async def _send_email_notification(
        self,
        email_addresses: List[str],
        alert: Alert,
        notification: Dict[str, Any],
    ):
        """Send alert via email"""
        try:
            success = await email_service.send_alert_email(
                to_addresses=email_addresses,
                alert_name=notification["alert_name"],
                severity=notification["severity"],
                message=notification["message"],
                context=notification.get("context"),
            )

            if success:
                logger.info(f"📧 Alert email sent: {notification['alert_name']}")
            else:
                logger.warning("📧 Email sending failed (check SMTP config)")

        except Exception as e:
            logger.error(
                f"Email notification error: {e}",
                exc_info=True,
            )


# Global instance
alert_notification_service = AlertNotificationService()
