# backend/app/services/metrics_service.py
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.dialects.postgresql import insert

from app.models.event import Event
from app.models.aggregate import Aggregate


class MetricsService:
    """
    Service for computing and retrieving metrics.
    
    Computes:
    - Events per minute/hour
    - Active users in time windows
    - Top events by count
    - Event distribution
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def compute_events_per_minute(
        self, 
        client_id: str,
        interval_start: datetime,
        interval_end: datetime
    ) -> Dict[str, Any]:
        """
        Compute events per minute for a client in a time range.
        
        Args:
            client_id: Client UUID
            interval_start: Start of time window
            interval_end: End of time window
            
        Returns:
            Dict with count and rate
        """
        # Count events in the interval
        result = await self.db.execute(
            select(func.count(Event.id))
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= interval_start,
                    Event.event_time < interval_end
                )
            )
        )
        
        event_count = result.scalar() or 0
        
        # Calculate duration in minutes
        duration_minutes = (interval_end - interval_start).total_seconds() / 60
        
        if duration_minutes > 0:
            rate = event_count / duration_minutes
        else:
            rate = 0.0
        
        return {
            "count": event_count,
            "rate": round(rate, 2),
            "interval_start": interval_start,
            "interval_end": interval_end
        }
    
    async def compute_active_users(
        self,
        client_id: str,
        window_start: datetime,
        window_end: datetime
    ) -> int:
        """
        Count unique active users in a time window.
        
        Args:
            client_id: Client UUID
            window_start: Start of window
            window_end: End of window
            
        Returns:
            Count of unique users
        """
        result = await self.db.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= window_start,
                    Event.event_time < window_end,
                    Event.user_id.isnot(None)
                )
            )
        )
        
        return result.scalar() or 0
    
    async def compute_top_events(
        self,
        client_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top events by count in a time range.
        
        Args:
            client_id: Client UUID
            start_time: Start of range
            end_time: End of range
            limit: Number of top events to return
            
        Returns:
            List of dicts with event_name and count
        """
        result = await self.db.execute(
            select(
                Event.event_name,
                func.count(Event.id).label('count')
            )
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time
                )
            )
            .group_by(Event.event_name)
            .order_by(desc('count'))
            .limit(limit)
        )
        
        rows = result.all()
        total_events = sum(row.count for row in rows)
        
        return [
            {
                "event_name": row.event_name,
                "count": row.count,
                "percentage": round((row.count / total_events * 100), 2) if total_events > 0 else 0
            }
            for row in rows
        ]
    
    async def get_overview_metrics(
        self,
        client_id: str,
        period: str = "last_hour"
    ) -> Dict[str, Any]:
        """
        Get overview dashboard metrics.
        
        Args:
            client_id: Client UUID
            period: Time period (last_hour, last_24h, last_7d)
            
        Returns:
            Dict with overview metrics
        """
        # Calculate time range based on period
        end_time = datetime.now(timezone.utc)
        
        if period == "last_hour":
            start_time = end_time - timedelta(hours=1)
        elif period == "last_24h":
            start_time = end_time - timedelta(hours=24)
        elif period == "last_7d":
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(hours=1)
        
        # Compute metrics in parallel would be ideal, but for simplicity:
        
        # Total events
        total_result = await self.db.execute(
            select(func.count(Event.id))
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time
                )
            )
        )
        total_events = total_result.scalar() or 0
        
        # Events per minute
        duration_minutes = (end_time - start_time).total_seconds() / 60
        events_per_minute = round(total_events / duration_minutes, 2) if duration_minutes > 0 else 0
        
        # Active users
        active_users = await self.compute_active_users(client_id, start_time, end_time)
        
        # Unique event types
        unique_result = await self.db.execute(
            select(func.count(func.distinct(Event.event_name)))
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time
                )
            )
        )
        unique_event_types = unique_result.scalar() or 0
        
        # Top events
        top_events = await self.compute_top_events(client_id, start_time, end_time, limit=5)
        
        return {
            "client_id": str(client_id),
            "period": period,
            "total_events": total_events,
            "events_per_minute": events_per_minute,
            "active_users": active_users,
            "unique_event_types": unique_event_types,
            "top_events": top_events,
            "start_time": start_time,
            "end_time": end_time
        }
    
    async def save_aggregate(
        self,
        client_id: str,
        metric_name: str,
        interval_start: datetime,
        interval_end: datetime,
        value: float,
        meta_data: Optional[Dict[str, Any]] = None
    ):
        """
        Save or update an aggregate metric.
        
        Uses UPSERT to avoid duplicates.
        
        Args:
            client_id: Client UUID
            metric_name: Name of metric
            interval_start: Start of interval
            interval_end: End of interval
            value: Computed value
            meta_data: Optional additional data
        """
        stmt = insert(Aggregate).values(
            client_id=client_id,
            metric_name=metric_name,
            interval_start=interval_start,
            interval_end=interval_end,
            value=value,
            meta_data=meta_data
        )
        
        # On conflict, update the value
        stmt = stmt.on_conflict_do_update(
            constraint='uq_client_metric_interval',
            set_={
                'value': value,
                'meta_data': meta_data,
                'updated_at': datetime.now(timezone.utc)
            }
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def get_time_series(
        self,
        client_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get time series data for a metric.
        
        Args:
            client_id: Client UUID
            metric_name: Metric to retrieve
            start_time: Start of range
            end_time: End of range
            limit: Max data points
            
        Returns:
            List of data points
        """
        result = await self.db.execute(
            select(Aggregate)
            .where(
                and_(
                    Aggregate.client_id == client_id,
                    Aggregate.metric_name == metric_name,
                    Aggregate.interval_start >= start_time,
                    Aggregate.interval_start < end_time
                )
            )
            .order_by(Aggregate.interval_start)
            .limit(limit)
        )
        
        aggregates = result.scalars().all()
        
        return [
            {
                "timestamp": agg.interval_start,
                "value": agg.value,
                "metadata": agg.meta_data
            }
            for agg in aggregates
        ]