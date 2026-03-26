"""
app/tasks/tasks_alerts.py

Alert evaluation task — runs as an APScheduler async job every 60 seconds.
No Celery, no asyncio.run().
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.models.api_key import APIKey
from app.models.alert import Alert
from app.services.alert_service import AlertService
from app.services.alert_notification import alert_notification_service
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def evaluate_alerts():
    """Evaluate all enabled alerts for every active client."""
    logger.info(f"Evaluating alerts at {datetime.now(timezone.utc).isoformat()}")
    triggered = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(APIKey).where(APIKey.is_active == True))
        api_keys = result.scalars().all()
        if not api_keys:
            return

        service = AlertService(db)
        for api_key in api_keys:
            client_id = str(api_key.id)
            try:
                alert_result = await db.execute(
                    select(Alert).where(Alert.client_id == client_id, Alert.enabled == True)
                )
                alerts = alert_result.scalars().all()

                for alert in alerts:
                    try:
                        eval_result = await service.evaluate_alert(alert)
                        if not eval_result["should_trigger"]:
                            continue

                        history = await service.trigger_alert(
                            alert, eval_result["current_value"], context=eval_result
                        )
                        await alert_notification_service.send_alert_notification(alert, history)
                        history.notification_sent = True
                        await db.commit()
                        triggered += 1
                        logger.info(f"Alert triggered: '{alert.name}'")
                    except Exception as e:
                        logger.error(f"Error evaluating alert '{alert.name}': {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error processing client '{api_key.client_name}': {e}", exc_info=True)

    logger.info(f"Alert evaluation complete — {triggered} triggered")