# backend/app/services/websocket_broadcaster.py
import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Any
from app.config import settings
from app.websockets.manager import manager
from app.websockets.handlers import format_event_message


class WebSocketBroadcaster:
    """
    Service to broadcast events to WebSocket clients via Redis Pub/Sub.
    
    This allows multiple API server instances to coordinate:
    - Worker processes events → publishes to Redis
    - API servers subscribe to Redis → broadcast to WebSocket clients
    """
    
    def __init__(self):
        self.redis_client: redis.Redis = None
        self.pubsub = None
        self.running = False
    
    async def initialize(self):
        """Initialize Redis connection and pub/sub"""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
    
    async def close(self):
        """Close Redis connections"""
        self.running = False
        if self.pubsub:
            await self.pubsub.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def publish_event(self, client_id: str, event_data: Dict[str, Any]):
        """
        Publish an event to Redis (to be broadcast to WebSocket clients).
        
        Args:
            client_id: Client ID to broadcast to
            event_data: Event data
        """
        if self.redis_client is None:
            await self.initialize()
        
        # Publish to client-specific channel
        channel = f"events:{client_id}"
        message = json.dumps({
            "client_id": client_id,
            "event": event_data
        })
        
        await self.redis_client.publish(channel, message)
    
    async def publish_metric(
        self, 
        client_id: str, 
        metric_name: str, 
        value: Any,
        metadata: dict = None
    ):
        """
        Publish a metric update.
        
        Args:
            client_id: Client ID
            metric_name: Metric name
            value: Metric value
            metadata: Additional metadata
        """
        if self.redis_client is None:
            await self.initialize()
        
        channel = f"metrics:{client_id}"
        message = json.dumps({
            "client_id": client_id,
            "metric": metric_name,
            "value": value,
            "metadata": metadata or {}
        })
        
        await self.redis_client.publish(channel, message)
        
    async def publish_alert(self, client_id: str, alert_data: Dict[str, Any]):
        """
        Publish an alert notification.
        
        Args:
            client_id: Client ID to send to
            alert_data: Alert notification data
        """
        if self.redis_client is None:
            await self.initialize()
        
        channel = f"alerts:{client_id}"
        message = json.dumps({
            "client_id": client_id,
            "alert": alert_data
        })
        
        await self.redis_client.publish(channel, message)
    
    async def subscribe_and_broadcast(self):
        """
        Subscribe to Redis channels and broadcast to WebSocket clients.
        
        This should run as a background task in the FastAPI app.
        """
        if self.redis_client is None:
            await self.initialize()
        
        # Subscribe to all event channels (pattern matching)
        await self.pubsub.psubscribe("events:*", "metrics:*", "alerts:*")
        
        self.running = True
        print("✅ WebSocket broadcaster listening to Redis...")
        
        try:
            while self.running:
                message = await self.pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=1.0
                )
                
                if message and message["type"] == "pmessage":
                    await self._handle_redis_message(message)
                
                await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
        
        except Exception as e:
            print(f"Error in broadcaster: {e}")
        
        finally:
            await self.close()
    
    async def _handle_redis_message(self, message: dict):
        """
        Handle a message from Redis and broadcast to appropriate WebSocket clients.
        
        Args:
            message: Redis pub/sub message
        """
        try:
            channel = message["channel"]
            data = json.loads(message["data"])
            
            client_id = data.get("client_id")
            
            if channel.startswith("events:"):
                # Broadcast event
                event_msg = format_event_message(data.get("event", {}))
                await manager.broadcast_to_client(event_msg, client_id, channel="events")
            
            elif channel.startswith("metrics:"):
                # Broadcast metric
                metric_msg = {
                    "type": "metric",
                    "metric": data.get("metric"),
                    "value": data.get("value"),
                    "metadata": data.get("metadata", {})
                }
                await manager.broadcast_to_client(metric_msg, client_id, channel="metrics")
            
            elif channel.startswith("alerts:"):
                # Broadcast alert
                alert_data = data.get("alert", {})
                alert_msg = {
                    "type": "alert",
                    "alert_id": alert_data.get("alert_id"),
                    "alert_name": alert_data.get("alert_name"),
                    "severity": alert_data.get("severity"),
                    "message": alert_data.get("message"),
                    "context": alert_data.get("context"),
                    "triggered_at": alert_data.get("triggered_at"),
                    "timestamp": alert_data.get("timestamp")
                }
                await manager.broadcast_to_client(alert_msg, client_id, channel="alerts")
        
        except Exception as e:
            print(f"Error handling Redis message: {e}")


# Global broadcaster instance
broadcaster = WebSocketBroadcaster()