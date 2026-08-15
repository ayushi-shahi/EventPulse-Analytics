# backend/app/services/metrics_service.py

import base64
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.dialects.postgresql import insert

from app.models.event import Event
from app.models.aggregate import Aggregate
from app.logging_config import get_logger

logger = get_logger(__name__)


class MetricsService:
    """
    Service for computing and retrieving metrics.
    Includes cursor-based and offset-based pagination.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # =====================================================
    # INTERNAL HELPERS
    # =====================================================

    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate condition like '100 > 50' (used by alerts)."""
        try:
            value = float(value)
            threshold = float(threshold)

            match operator:
                case ">":
                    return value > threshold
                case "<":
                    return value < threshold
                case "==":
                    return value == threshold
                case ">=":
                    return value >= threshold
                case "<=":
                    return value <= threshold
                case _:
                    return False
        except (ValueError, TypeError):
            return False

    # =====================================================
    # CORE METRICS
    # =====================================================

    async def compute_events_per_minute(
        self,
        client_id: str,
        interval_start: datetime,
        interval_end: datetime,
    ) -> Dict[str, Any]:
        """Compute events per minute for a client."""

        result = await self.db.execute(
            select(func.count(Event.id)).where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= interval_start,
                    Event.event_time < interval_end,
                )
            )
        )

        event_count = result.scalar() or 0
        duration_minutes = (interval_end - interval_start).total_seconds() / 60

        rate = event_count / duration_minutes if duration_minutes > 0 else 0.0

        return {
            "count": event_count,
            "rate": round(rate, 2),
            "interval_start": interval_start,
            "interval_end": interval_end,
        }

    async def compute_active_users(
        self,
        client_id: str,
        window_start: datetime,
        window_end: datetime,
    ) -> int:
        """Count unique active users in a time window."""

        result = await self.db.execute(
            select(func.count(func.distinct(Event.user_id))).where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= window_start,
                    Event.event_time < window_end,
                    Event.user_id.isnot(None),
                )
            )
        )

        return result.scalar() or 0

    async def compute_top_events(
        self,
        client_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get top events by count."""

        result = await self.db.execute(
            select(
                Event.event_name,
                func.count(Event.id).label("count"),
            )
            .where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time,
                )
            )
            .group_by(Event.event_name)
            .order_by(desc("count"))
            .limit(limit)
        )

        rows = result.all()
        total = sum(row.count for row in rows)

        return [
            {
                "event_name": row.event_name,
                "count": row.count,
                "percentage": round((row.count / total) * 100, 2) if total > 0 else 0,
            }
            for row in rows
        ]

    # =====================================================
    # DASHBOARD METRICS
    # =====================================================

    async def get_overview_metrics(
        self,
        client_id: str,
        period: str = "last_hour",
    ) -> Dict[str, Any]:
        """Get overview dashboard metrics."""

        end_time = datetime.now(timezone.utc)

        if period == "last_hour":
            start_time = end_time - timedelta(hours=1)
        elif period == "last_24h":
            start_time = end_time - timedelta(hours=24)
        elif period == "last_7d":
            start_time = end_time - timedelta(days=7)
        else:
            start_time = end_time - timedelta(hours=1)

        # Total events
        total_result = await self.db.execute(
            select(func.count(Event.id)).where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time,
                )
            )
        )
        total_events = total_result.scalar() or 0

        # Events per minute
        duration_minutes = (end_time - start_time).total_seconds() / 60
        events_per_minute = (
            round(total_events / duration_minutes, 2) if duration_minutes > 0 else 0
        )

        active_users = await self.compute_active_users(client_id, start_time, end_time)

        unique_result = await self.db.execute(
            select(func.count(func.distinct(Event.event_name))).where(
                and_(
                    Event.client_id == client_id,
                    Event.event_time >= start_time,
                    Event.event_time < end_time,
                )
            )
        )
        unique_event_types = unique_result.scalar() or 0

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
            "end_time": end_time,
        }

    # =====================================================
    # AGGREGATES
    # =====================================================

    async def save_aggregate(
        self,
        client_id: str,
        metric_name: str,
        interval_start: datetime,
        interval_end: datetime,
        value: float,
        meta_data: Optional[Dict[str, Any]] = None,
    ):
        """Insert or update aggregate metric (UPSERT)."""

        stmt = insert(Aggregate).values(
            client_id=client_id,
            metric_name=metric_name,
            interval_start=interval_start,
            interval_end=interval_end,
            value=value,
            meta_data=meta_data,
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_client_metric_interval",
            set_={
                "value": value,
                "meta_data": meta_data,
                "updated_at": datetime.now(timezone.utc),
            },
        )

        await self.db.execute(stmt)
        await self.db.commit()

    # =====================================================
    # TIME SERIES (AGGREGATES)
    # =====================================================

    async def get_time_series(
        self,
        client_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Return a simple list of time-series data points for a metric.

        This is a thin wrapper over the cursor-based implementation, used by
        the non-paginated `/metrics/time-series/{metric_name}` endpoint.
        """
        data_points, _next_cursor, _has_next = await self.get_time_series_paginated(
            client_id=client_id,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            cursor=None,
            limit=limit,
        )
        return data_points

    async def get_time_series_paginated(
        self,
        client_id: str,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        cursor: Optional[str] = None,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], Optional[str], bool]:
        """
        Cursor-based pagination for time series data.
        """

        cursor_time = start_time
        if cursor:
            try:
                decoded = json.loads(base64.b64decode(cursor))
                cursor_time = datetime.fromisoformat(decoded["timestamp"])
            except Exception as e:
                logger.warning(f"Invalid cursor ignored: {e}")

        query = (
            select(Aggregate)
            .where(
                and_(
                    Aggregate.client_id == client_id,
                    Aggregate.metric_name == metric_name,
                    Aggregate.interval_start > cursor_time,  # CRITICAL FIX
                    Aggregate.interval_start < end_time,
                )
            )
            .order_by(Aggregate.interval_start)
            .limit(limit + 1)
        )

        result = await self.db.execute(query)
        aggregates = result.scalars().all()

        has_next = len(aggregates) > limit
        if has_next:
            aggregates = aggregates[:limit]

        data_points = [
            {
                "timestamp": agg.interval_start,
                "value": agg.value,
                "meta_data": agg.meta_data,  # FIXED
            }
            for agg in aggregates
        ]

        next_cursor = None
        if has_next and aggregates:
            last_ts = aggregates[-1].interval_start
            payload = {"timestamp": last_ts.isoformat()}
            next_cursor = base64.b64encode(json.dumps(payload).encode()).decode()

        return data_points, next_cursor, has_next

    # =====================================================
    # OFFSET PAGINATION (EVENTS)
    # =====================================================

    async def get_events_paginated(
        self,
        client_id: str,
        start_time: datetime,
        end_time: datetime,
        event_name: Optional[str] = None,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 100,
    ) -> Tuple[List[Event], int]:
        """Offset pagination for event browsing."""

        conditions = [
            Event.client_id == client_id,
            Event.event_time >= start_time,
            Event.event_time < end_time,
        ]

        if event_name:
            conditions.append(Event.event_name == event_name)
        if user_id:
            conditions.append(Event.user_id == user_id)

        count_result = await self.db.execute(
            select(func.count(Event.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size

        result = await self.db.execute(
            select(Event)
            .where(and_(*conditions))
            .order_by(desc(Event.event_time))
            .offset(offset)
            .limit(page_size)
        )

        return result.scalars().all(), total

    # =====================================================
    # PROPERTY BREAKDOWN + FUNNEL
    # =====================================================

    # Only these JSONB keys may be grouped on. The property name is
    # interpolated into SQL (JSONB key access cannot be parameterised the same
    # way as a value), so it must never come straight from user input.
    ALLOWED_BREAKDOWN_PROPERTIES = {
        "device", "browser", "os", "country", "city", "plan", "path",
        "referrer", "utm_source", "utm_campaign", "feature", "surface",
        "error_type", "severity", "endpoint", "method", "status_code",
        "billing_period", "payment_method", "reason", "role", "format",
    }

    @staticmethod
    def _window(period: str) -> timedelta:
        return {
            "last_hour": timedelta(hours=1),
            "last_24h": timedelta(hours=24),
            "last_7d": timedelta(days=7),
            "last_30d": timedelta(days=30),
        }.get(period, timedelta(hours=24))

    async def get_breakdown(
        self,
        client_id: str,
        prop: str,
        period: str = "last_24h",
        event_name: str | None = None,
        limit: int = 12,
    ) -> Dict[str, Any]:
        """
        Group events by one JSONB property — the basis of every
        "top countries / devices / plans" view.
        """
        if prop not in self.ALLOWED_BREAKDOWN_PROPERTIES:
            raise ValueError(f"property '{prop}' is not available for breakdown")

        end_time = datetime.now(timezone.utc)
        start_time = end_time - self._window(period)

        # `properties ->> 'key' IS NOT NULL` rather than the `?` containment
        # operator: a bare `?` inside a text() statement is ambiguous with
        # parameter placeholders and is not worth the risk for an equivalent test.
        filters = ["client_id = :client_id", "event_time >= :start", "event_time < :end",
                   f"properties ->> '{prop}' IS NOT NULL"]
        params: Dict[str, Any] = {
            "client_id": client_id, "start": start_time, "end": end_time, "limit": limit,
        }
        if event_name:
            filters.append("event_name = :event_name")
            params["event_name"] = event_name

        sql = text(f"""
            SELECT properties ->> '{prop}' AS label,
                   count(*)                AS count,
                   count(DISTINCT user_id) AS users
            FROM events
            WHERE {' AND '.join(filters)}
            GROUP BY 1
            ORDER BY count DESC
            LIMIT :limit
        """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        total = sum(r["count"] for r in rows) or 1

        return {
            "property": prop,
            "period": period,
            "event_name": event_name,
            "total": sum(r["count"] for r in rows),
            "items": [
                {
                    "label": r["label"],
                    "count": r["count"],
                    "users": r["users"],
                    "percentage": round(r["count"] / total * 100, 2),
                }
                for r in rows
            ],
        }

    async def get_funnel(
        self,
        client_id: str,
        steps: List[str],
        period: str = "last_7d",
    ) -> Dict[str, Any]:
        """
        Conversion funnel over distinct users.

        A user counts at step N only if they also reached every earlier step,
        so the series is monotonically non-increasing — otherwise a later step
        with more users than the one before it produces a nonsense funnel.
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - self._window(period)

        results: List[Dict[str, Any]] = []
        previous_users: Optional[set] = None
        first_count = 0

        for index, step in enumerate(steps):
            rows = await self.db.execute(
                text("""
                    SELECT DISTINCT user_id
                    FROM events
                    WHERE client_id = :client_id
                      AND event_name = :event_name
                      AND event_time >= :start AND event_time < :end
                      AND user_id IS NOT NULL
                """),
                {"client_id": client_id, "event_name": step,
                 "start": start_time, "end": end_time},
            )
            users = {r[0] for r in rows.fetchall()}
            if previous_users is not None:
                users &= previous_users
            previous_users = users

            count = len(users)
            if index == 0:
                first_count = count

            results.append({
                "step": step,
                "users": count,
                "conversion_from_start": round(count / first_count * 100, 2) if first_count else 0.0,
                "conversion_from_previous": (
                    100.0 if index == 0
                    else round(count / results[index - 1]["users"] * 100, 2)
                    if results[index - 1]["users"] else 0.0
                ),
                "dropped": 0 if index == 0 else results[index - 1]["users"] - count,
            })

        return {
            "period": period,
            "steps": results,
            "overall_conversion": (
                round(results[-1]["users"] / first_count * 100, 2)
                if results and first_count else 0.0
            ),
        }
