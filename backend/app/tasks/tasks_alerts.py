# backend/app/tasks/tasks_alerts.py
"""
Alert evaluation Celery task.

The Celery task is a synchronous entry point.
All async DB work runs inside asyncio.run() — a clean, isolated event loop
per task invocation. No get_event_loop() used anywhere.
"""
import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.tasks.celery_app import celery_app
from app.models.api_key import APIKey
from app.models.alert import Alert
from app.services.alert_service import AlertService
from app.services.alert_notification import alert_notification_service
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# evaluate_alerts
# ---------------------------------------------------------------------------

@celery_app.task(
    name="app.tasks.tasks_alerts.evaluate_alerts",
    bind=True,
)
def evaluate_alerts(self):
    """
    Evaluate all enabled alerts for every active client.
    Scheduled every 60 seconds via Celery Beat.

    For each alert:
    1. Check the condition against current metrics
    2. If triggered (and not in cooldown), create a history record
    3. Send notifications via configured channels (WebSocket / email)
    """
    return asyncio.run(_evaluate_alerts_async())


async def _evaluate_alerts_async():
    logger.info(f"🔔 Evaluating alerts at {datetime.now(timezone.utc).isoformat()}")

    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clients_checked": 0,
        "alerts_evaluated": 0,
        "alerts_triggered": 0,
        "errors": [],
    }

    async with AsyncSessionLocal() as db:
        try:
            # Get all active API keys (one per client)
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()

            if not api_keys:
                logger.info("No active clients found — skipping alert evaluation")
                return {**results, "message": "No active clients found"}

            service = AlertService(db)

            for api_key in api_keys:
                client_id = str(api_key.id)
                try:
                    # Fetch all enabled alerts for this client
                    alert_result = await db.execute(
                        select(Alert).where(
                            Alert.client_id == client_id,
                            Alert.enabled == True,
                        )
                    )
                    alerts = alert_result.scalars().all()

                    if not alerts:
                        continue

                    results["clients_checked"] += 1

                    for alert in alerts:
                        results["alerts_evaluated"] += 1
                        try:
                            # Evaluate condition + cooldown check
                            eval_result = await service.evaluate_alert(alert)

                            if not eval_result["should_trigger"]:
                                continue

                            # Create history record and update alert counters
                            history = await service.trigger_alert(
                                alert,
                                eval_result["current_value"],
                                context=eval_result,
                            )

                            # Send notifications (WebSocket / email)
                            await alert_notification_service.send_alert_notification(
                                alert, history
                            )

                            # Mark notification as sent
                            history.notification_sent = True
                            await db.commit()

                            results["alerts_triggered"] += 1

                            logger.info(
                                f"🚨 Alert triggered: '{alert.name}' — "
                                f"value={eval_result['current_value']:.2f}, "
                                f"threshold={eval_result['threshold']}"
                            )

                        except Exception as e:
                            msg = f"Error evaluating alert '{alert.name}': {e}"
                            logger.error(msg, exc_info=True)
                            results["errors"].append(msg)

                except Exception as e:
                    msg = f"Error processing client '{api_key.client_name}': {e}"
                    logger.error(msg, exc_info=True)
                    results["errors"].append(msg)

        except Exception as e:
            msg = f"Fatal error in alert evaluation: {e}"
            logger.error(msg, exc_info=True)
            results["errors"].append(msg)

    logger.info(
        f"✅ Alert evaluation complete — "
        f"{results['alerts_triggered']} triggered / "
        f"{results['alerts_evaluated']} evaluated"
    )
    return results