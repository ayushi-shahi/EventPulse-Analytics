# backend/app/services/alert_service.py
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from app.models.alert import Alert, AlertHistory
from app.models.aggregate import Aggregate
from app.services.metrics_service import MetricsService


class AlertService:
    """
    Service for managing and evaluating alerts.
    
    Responsibilities:
    - Evaluate alert conditions against current metrics
    - Trigger alerts when conditions are met
    - Respect cooldown periods
    - Record alert history
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.metrics_service = MetricsService(db)
    
    async def evaluate_alert(self, alert: Alert) -> Dict[str, Any]:
        """
        Evaluate a single alert against current metrics.
        
        Args:
            alert: Alert object to evaluate
            
        Returns:
            Dict with evaluation results
        """
        # Parse expression
        expression = alert.expression
        metric_name = expression.get("metric")
        operator = expression.get("operator")
        threshold = expression.get("threshold")
        window = expression.get("window", "1m")
        
        # Get current metric value
        current_value = await self._get_current_metric_value(
            client_id=str(alert.client_id),
            metric_name=metric_name,
            window=window
        )
        
        # Evaluate condition
        should_trigger = self._evaluate_condition(
            current_value,
            operator,
            threshold
        )
        
        # Check cooldown
        if should_trigger and alert.last_triggered:
            time_since_last = datetime.now(timezone.utc) - alert.last_triggered
            if time_since_last.total_seconds() < alert.cooldown_seconds:
                should_trigger = False
                reason = f"In cooldown (last triggered {int(time_since_last.total_seconds())}s ago)"
            else:
                reason = "Condition met, cooldown expired"
        elif should_trigger:
            reason = "Condition met"
        else:
            reason = "Condition not met"
        
        return {
            "alert_id": str(alert.id),
            "alert_name": alert.name,
            "should_trigger": should_trigger,
            "current_value": current_value,
            "threshold": threshold,
            "operator": operator,
            "reason": reason
        }
    
    async def _get_current_metric_value(
        self,
        client_id: str,
        metric_name: str,
        window: str
    ) -> float:
        """
        Get the most recent value for a metric.
        
        Args:
            client_id: Client UUID
            metric_name: Name of metric
            window: Time window (e.g., "1m", "1h")
            
        Returns:
            Current metric value
        """
        # Calculate lookback time
        now = datetime.now(timezone.utc)
        
        if window == "1m":
            lookback = timedelta(minutes=2)
        elif window == "5m":
            lookback = timedelta(minutes=10)
        elif window == "1h":
            lookback = timedelta(hours=2)
        else:
            lookback = timedelta(minutes=2)
        
        start_time = now - lookback
        
        # Query most recent aggregate
        result = await self.db.execute(
            select(Aggregate)
            .where(
                and_(
                    Aggregate.client_id == client_id,
                    Aggregate.metric_name == metric_name,
                    Aggregate.interval_start >= start_time
                )
            )
            .order_by(desc(Aggregate.interval_start))
            .limit(1)
        )
        
        aggregate = result.scalar_one_or_none()
        
        if aggregate:
            return aggregate.value or 0.0
        
        # If no aggregate found, compute real-time
        if metric_name == "events_per_minute":
            end_time = now
            start_time = now - timedelta(minutes=1)
            data = await self.metrics_service.compute_events_per_minute(
                client_id, start_time, end_time
            )
            return data["rate"]
        
        elif metric_name == "active_users_1h":
            end_time = now
            start_time = now - timedelta(hours=1)
            count = await self.metrics_service.compute_active_users(
                client_id, start_time, end_time
            )
            return float(count)
        
        return 0.0
    
    def _evaluate_condition(
        self,
        current_value: float,
        operator: str,
        threshold: float
    ) -> bool:
        """
        Evaluate a condition.
        
        Args:
            current_value: Current metric value
            operator: Comparison operator
            threshold: Threshold value
            
        Returns:
            True if condition is met
        """
        if operator == ">":
            return current_value > threshold
        elif operator == "<":
            return current_value < threshold
        elif operator == ">=":
            return current_value >= threshold
        elif operator == "<=":
            return current_value <= threshold
        elif operator == "==":
            return abs(current_value - threshold) < 0.01  # Float comparison
        elif operator == "!=":
            return abs(current_value - threshold) >= 0.01
        else:
            return False
    
    async def trigger_alert(
        self,
        alert: Alert,
        current_value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> AlertHistory:
        """
        Trigger an alert and create history record.
        
        Args:
            alert: Alert object
            current_value: Current metric value
            context: Additional context data
            
        Returns:
            AlertHistory record
        """
        # Create message
        expression = alert.expression
        message = (
            f"Alert '{alert.name}' triggered: "
            f"{expression['metric']} {expression['operator']} {expression['threshold']} "
            f"(current: {current_value:.2f})"
        )
        
        # Create history record
        history = AlertHistory(
            alert_id=alert.id,
            client_id=alert.client_id,
            triggered_at=datetime.now(timezone.utc),
            severity=alert.severity,
            message=message,
            context=context or {
                "metric": expression["metric"],
                "current_value": current_value,
                "threshold": expression["threshold"],
                "operator": expression["operator"]
            },
            notification_sent=False  # Will update after sending
        )
        
        self.db.add(history)
        
        # Update alert
        alert.last_triggered = datetime.now(timezone.utc)
        alert.trigger_count += 1
        
        await self.db.commit()
        await self.db.refresh(history)
        
        return history
    
    async def evaluate_all_alerts(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Evaluate all enabled alerts for a client.
        
        Args:
            client_id: Client UUID
            
        Returns:
            List of evaluation results
        """
        # Get all enabled alerts for client
        result = await self.db.execute(
            select(Alert)
            .where(
                and_(
                    Alert.client_id == client_id,
                    Alert.enabled == True
                )
            )
        )
        
        alerts = result.scalars().all()
        
        evaluation_results = []
        
        for alert in alerts:
            try:
                eval_result = await self.evaluate_alert(alert)
                evaluation_results.append(eval_result)
                
                # If should trigger, create history
                if eval_result["should_trigger"]:
                    await self.trigger_alert(
                        alert,
                        eval_result["current_value"],
                        context=eval_result
                    )
            
            except Exception as e:
                print(f"Error evaluating alert {alert.name}: {e}")
                evaluation_results.append({
                    "alert_id": str(alert.id),
                    "alert_name": alert.name,
                    "error": str(e)
                })
        
        return evaluation_results
    
    async def get_alert_history(
        self,
        alert_id: str,
        limit: int = 50
    ) -> List[AlertHistory]:
        """
        Get history for a specific alert.
        
        Args:
            alert_id: Alert UUID
            limit: Max records to return
            
        Returns:
            List of AlertHistory records
        """
        result = await self.db.execute(
            select(AlertHistory)
            .where(AlertHistory.alert_id == alert_id)
            .order_by(desc(AlertHistory.triggered_at))
            .limit(limit)
        )
        
        return result.scalars().all()