# backend/app/api/v1/alerts.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from typing import List, Optional

from app.database import get_db
from app.models.api_key import APIKey
from app.models.alert import Alert, AlertHistory
from app.api.deps import get_api_key
from app.schemas.alert import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertHistoryResponse,
    AlertTestResponse
)
from app.services.alert_service import AlertService
from app.services.alert_notification import alert_notification_service

router = APIRouter()


@router.post("/", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new alert.
    
    **Example Alert - High Traffic**:
```json
    {
      "name": "High Traffic Alert",
      "description": "Triggers when events per minute exceeds 1000",
      "expression": {
        "metric": "events_per_minute",
        "operator": ">",
        "threshold": 1000,
        "window": "1m"
      },
      "severity": "warning",
      "enabled": true,
      "notification_channels": {
        "websocket": true,
        "email": ["ops@example.com"]
      },
      "cooldown_seconds": 300
    }
```
    
    **Example Alert - Low Active Users**:
```json
    {
      "name": "Low Active Users",
      "expression": {
        "metric": "active_users_1h",
        "operator": "<",
        "threshold": 10
      },
      "severity": "error"
    }
```
    """
    # Create alert
    new_alert = Alert(
        client_id=api_key.id,
        name=alert_data.name,
        description=alert_data.description,
        expression=alert_data.expression.model_dump(),
        severity=alert_data.severity,
        enabled=alert_data.enabled,
        notification_channels=alert_data.notification_channels.model_dump() if alert_data.notification_channels else {"websocket": True},
        cooldown_seconds=alert_data.cooldown_seconds
    )
    
    db.add(new_alert)
    await db.commit()
    await db.refresh(new_alert)
    
    return AlertResponse(
        id=str(new_alert.id),
        client_id=str(new_alert.client_id),
        name=new_alert.name,
        description=new_alert.description,
        expression=new_alert.expression,
        severity=new_alert.severity,
        enabled=new_alert.enabled,
        last_triggered=new_alert.last_triggered,
        trigger_count=new_alert.trigger_count,
        notification_channels=new_alert.notification_channels,
        cooldown_seconds=new_alert.cooldown_seconds,
        created_at=new_alert.created_at,
        updated_at=new_alert.updated_at
    )


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    List all alerts for the current client.
    
    **Filters**:
    - `enabled`: true/false to filter by status
    """
    # Build query
    query = select(Alert).where(Alert.client_id == api_key.id)
    
    if enabled is not None:
        query = query.where(Alert.enabled == enabled)
    
    query = query.order_by(desc(Alert.created_at))
    
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return [
        AlertResponse(
            id=str(alert.id),
            client_id=str(alert.client_id),
            name=alert.name,
            description=alert.description,
            expression=alert.expression,
            severity=alert.severity,
            enabled=alert.enabled,
            last_triggered=alert.last_triggered,
            trigger_count=alert.trigger_count,
            notification_channels=alert.notification_channels,
            cooldown_seconds=alert.cooldown_seconds,
            created_at=alert.created_at,
            updated_at=alert.updated_at
        )
        for alert in alerts
    ]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific alert.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    return AlertResponse(
        id=str(alert.id),
        client_id=str(alert.client_id),
        name=alert.name,
        description=alert.description,
        expression=alert.expression,
        severity=alert.severity,
        enabled=alert.enabled,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        notification_channels=alert.notification_channels,
        cooldown_seconds=alert.cooldown_seconds,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: str,
    alert_update: AlertUpdate,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an alert.
    
    You can update any field. Only provided fields will be changed.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Update fields
    if alert_update.name is not None:
        alert.name = alert_update.name
    
    if alert_update.description is not None:
        alert.description = alert_update.description
    
    if alert_update.expression is not None:
        alert.expression = alert_update.expression.model_dump()
    
    if alert_update.severity is not None:
        alert.severity = alert_update.severity
    
    if alert_update.enabled is not None:
        alert.enabled = alert_update.enabled
    
    if alert_update.notification_channels is not None:
        alert.notification_channels = alert_update.notification_channels.model_dump()
    
    if alert_update.cooldown_seconds is not None:
        alert.cooldown_seconds = alert_update.cooldown_seconds
    
    await db.commit()
    await db.refresh(alert)
    
    return AlertResponse(
        id=str(alert.id),
        client_id=str(alert.client_id),
        name=alert.name,
        description=alert.description,
        expression=alert.expression,
        severity=alert.severity,
        enabled=alert.enabled,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        notification_channels=alert.notification_channels,
        cooldown_seconds=alert.cooldown_seconds,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an alert.
    
    ⚠️ This also deletes all history for this alert!
    Consider disabling instead if you want to keep history.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    await db.delete(alert)
    await db.commit()
    
    return None


@router.post("/{alert_id}/test", response_model=AlertTestResponse)
async def test_alert(
    alert_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Test an alert without triggering notifications.
    
    Shows whether the alert would trigger based on current metrics.
    Useful for testing alert configurations.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Evaluate alert
    service = AlertService(db)
    eval_result = await service.evaluate_alert(alert)
    
    return AlertTestResponse(
        alert_id=str(alert.id),
        would_trigger=eval_result["should_trigger"],
        current_value=eval_result["current_value"],
        threshold=eval_result["threshold"],
        operator=eval_result["operator"],
        message=eval_result["reason"]
    )


@router.get("/{alert_id}/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    alert_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Get trigger history for an alert.
    
    Shows when the alert was triggered and what values caused it.
    """
    # Verify alert belongs to client
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    # Get history
    service = AlertService(db)
    history_records = await service.get_alert_history(alert_id, limit)
    
    return [
        AlertHistoryResponse(
            id=str(h.id),
            alert_id=str(h.alert_id),
            client_id=str(h.client_id),
            triggered_at=h.triggered_at,
            severity=h.severity,
            message=h.message,
            context=h.context,
            notification_sent=h.notification_sent
        )
        for h in history_records
    ]


@router.post("/{alert_id}/enable", response_model=AlertResponse)
async def enable_alert(
    alert_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Enable an alert.
    
    Shortcut for PATCH with enabled=true.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.enabled = True
    await db.commit()
    await db.refresh(alert)
    
    return AlertResponse(
        id=str(alert.id),
        client_id=str(alert.client_id),
        name=alert.name,
        description=alert.description,
        expression=alert.expression,
        severity=alert.severity,
        enabled=alert.enabled,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        notification_channels=alert.notification_channels,
        cooldown_seconds=alert.cooldown_seconds,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )


@router.post("/{alert_id}/disable", response_model=AlertResponse)
async def disable_alert(
    alert_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: AsyncSession = Depends(get_db)
):
    """
    Disable an alert.
    
    Shortcut for PATCH with enabled=false.
    """
    result = await db.execute(
        select(Alert).where(
            and_(
                Alert.id == alert_id,
                Alert.client_id == api_key.id
            )
        )
    )
    
    alert = result.scalar_one_or_none()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.enabled = False
    await db.commit()
    await db.refresh(alert)
    
    return AlertResponse(
        id=str(alert.id),
        client_id=str(alert.client_id),
        name=alert.name,
        description=alert.description,
        expression=alert.expression,
        severity=alert.severity,
        enabled=alert.enabled,
        last_triggered=alert.last_triggered,
        trigger_count=alert.trigger_count,
        notification_channels=alert.notification_channels,
        cooldown_seconds=alert.cooldown_seconds,
        created_at=alert.created_at,
        updated_at=alert.updated_at
    )