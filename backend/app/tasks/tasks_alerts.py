# backend/app/tasks/tasks_alerts.py
import asyncio
from datetime import datetime, timezone
from celery import Task

from app.tasks.celery_app import celery_app
from app.models.api_key import APIKey
from app.models.alert import Alert
from app.services.alert_service import AlertService
from app.services.alert_notification import alert_notification_service
from sqlalchemy import select


@celery_app.task(
    name="app.tasks.tasks_alerts.evaluate_alerts",
    bind=True
)
def evaluate_alerts(self):
    """
    Evaluate all enabled alerts.
    
    Scheduled to run every minute via Celery Beat.
    
    For each client:
    - Check all enabled alerts
    - Trigger if conditions are met
    - Send notifications
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_evaluate_alerts_async())


async def _evaluate_alerts_async():
    """
    Async implementation of alert evaluation.
    """
    from app.database import AsyncSessionLocal
    
    print(f"🔔 Evaluating alerts at {datetime.now(timezone.utc)}")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "clients_checked": 0,
        "alerts_evaluated": 0,
        "alerts_triggered": 0,
        "errors": []
    }
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all active API keys (clients)
            result = await db.execute(
                select(APIKey).where(APIKey.is_active == True)
            )
            api_keys = result.scalars().all()
            
            if not api_keys:
                return {
                    **results,
                    "message": "No active clients found"
                }
            
            service = AlertService(db)
            
            # Evaluate alerts for each client
            for api_key in api_keys:
                try:
                    client_id = str(api_key.id)
                    
                    # Get all enabled alerts for this client
                    alert_result = await db.execute(
                        select(Alert).where(
                            Alert.client_id == client_id,
                            Alert.enabled == True
                        )
                    )
                    alerts = alert_result.scalars().all()
                    
                    if not alerts:
                        continue
                    
                    results["clients_checked"] += 1
                    
                    # Evaluate each alert
                    for alert in alerts:
                        try:
                            results["alerts_evaluated"] += 1
                            
                            # Evaluate condition
                            eval_result = await service.evaluate_alert(alert)
                            
                            # If should trigger
                            if eval_result["should_trigger"]:
                                # Create history record
                                history = await service.trigger_alert(
                                    alert,
                                    eval_result["current_value"],
                                    context=eval_result
                                )
                                
                                # Send notification
                                await alert_notification_service.send_alert_notification(
                                    alert,
                                    history
                                )
                                
                                # Mark notification as sent
                                history.notification_sent = True
                                await db.commit()
                                
                                results["alerts_triggered"] += 1
                                
                                print(f"🚨 Alert triggered: {alert.name} "
                                      f"(value: {eval_result['current_value']:.2f}, "
                                      f"threshold: {eval_result['threshold']})")
                        
                        except Exception as e:
                            error_msg = f"Error evaluating alert {alert.name}: {str(e)}"
                            results["errors"].append(error_msg)
                            print(f"❌ {error_msg}")
                
                except Exception as e:
                    error_msg = f"Error processing client {api_key.client_name}: {str(e)}"
                    results["errors"].append(error_msg)
                    print(f"❌ {error_msg}")
            
            print(f"✅ Alert evaluation complete: {results['alerts_triggered']} triggered "
                  f"out of {results['alerts_evaluated']} evaluated")
            
            return results
        
        except Exception as e:
            results["errors"].append(f"Fatal error: {str(e)}")
            return results