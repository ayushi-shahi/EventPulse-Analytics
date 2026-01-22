# backend/app/services/websocket_broadcaster.py

import redis.asyncio as redis
import json
import asyncio
from typing import Dict, Any

from redis.exceptions import ConnectionError

from app.config import settings
from app.websockets.manager import manager
from app.websockets.handlers import format_event_message
from app.logging_config import get_logger

logger = get_logger(__name__)


class WebSocketBroadcaster:
    """
    Broadcasts Redis Pub/Sub messages to WebSocket clients.
    Designed to be resilient to Redis restarts and network failures.
    """

    def __init__(self):
        self.redis_client: redis.Redis | None = None
        self.pubsub = None
        self.running = False

        # Reconnect backoff
        self.reconnect_delay = 1
        self.max_reconnect_delay = 60

    async def initialize(self):
        """Initialize Redis connection and PubSub."""
        if self.redis_client is not None:
            return

        self.redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )

        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        logger.info("✅ WebSocket broadcaster Redis initialized")

    async def close(self):
        """Close Redis connections safely."""
        self.running = False

        if self.pubsub:
            try:
                await self.pubsub.close()
            except Exception:
                pass
            finally:
                self.pubsub = None

        if self.redis_client:
            try:
                await self.redis_client.close()
            except Exception:
                pass
            finally:
                self.redis_client = None

    async def _reconnect(self):
        """Reconnect to Redis with exponential backoff."""
        logger.warning(f"Reconnecting in {self.reconnect_delay}s...")
        await asyncio.sleep(self.reconnect_delay)

        self.reconnect_delay = min(
            self.reconnect_delay * 2, self.max_reconnect_delay
        )

        await self.close()
        await self.initialize()

        # IMPORTANT: recreate pubsub and re-subscribe
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        await self.pubsub.psubscribe("events:*", "metrics:*", "alerts:*")

        self.reconnect_delay = 1
        logger.info("✅ Redis reconnected and resubscribed")

    # -------------------- PUBLISH METHODS --------------------

    async def publish_event(self, client_id: str, event_data: Dict[str, Any]):
        try:
            if self.redis_client is None:
                await self.initialize()

            await self.redis_client.publish(
                f"events:{client_id}",
                json.dumps({"client_id": client_id, "event": event_data}),
            )
        except Exception as e:
            logger.error(f"Failed to publish event: {e}", exc_info=True)

    async def publish_metric(
        self,
        client_id: str,
        metric_name: str,
        value: Any,
        metadata: dict | None = None,
    ):
        try:
            if self.redis_client is None:
                await self.initialize()

            await self.redis_client.publish(
                f"metrics:{client_id}",
                json.dumps(
                    {
                        "client_id": client_id,
                        "metric": metric_name,
                        "value": value,
                        "metadata": metadata or {},
                    }
                ),
            )
        except Exception as e:
            logger.error(f"Failed to publish metric: {e}", exc_info=True)

    async def publish_alert(self, client_id: str, alert_data: Dict[str, Any]):
        try:
            if self.redis_client is None:
                await self.initialize()

            await self.redis_client.publish(
                f"alerts:{client_id}",
                json.dumps({"client_id": client_id, "alert": alert_data}),
            )
        except Exception as e:
            logger.error(f"Failed to publish alert: {e}", exc_info=True)

    # -------------------- SUBSCRIBE & BROADCAST --------------------

    async def subscribe_and_broadcast(self):
        """Main broadcaster loop."""
        await self.initialize()
        await self.pubsub.psubscribe("events:*", "metrics:*", "alerts:*")

        logger.info("✅ WebSocket broadcaster listening to Redis")
        self.running = True
        consecutive_errors = 0

        while self.running:
            try:
                message = await self.pubsub.get_message(timeout=1.0)

                if message and message["type"] == "pmessage":
                    await self._handle_redis_message(message)
                    consecutive_errors = 0

                await asyncio.sleep(0.01)

            except asyncio.CancelledError:
                logger.info("Broadcaster task cancelled")
                break

            except ConnectionError:
                consecutive_errors += 1
                logger.error(
                    f"Redis connection error ({consecutive_errors}/10)"
                )

                if consecutive_errors >= 10:
                    logger.critical("Too many Redis errors, stopping broadcaster")
                    break

                await self._reconnect()

            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Unexpected broadcaster error ({consecutive_errors}/10): {e}",
                    exc_info=True,
                )

                if consecutive_errors >= 10:
                    logger.critical("Too many errors, stopping broadcaster")
                    break

                await asyncio.sleep(1)

        await self.close()
        logger.info("Broadcaster stopped")

    # -------------------- MESSAGE HANDLER --------------------

    async def _handle_redis_message(self, message: dict):
        try:
            channel = message["channel"]
            payload = json.loads(message["data"])
            client_id = payload.get("client_id")

            if not client_id:
                logger.warning("Received message without client_id")
                return

            if channel.startswith("events:"):
                await manager.broadcast_to_client(
                    format_event_message(payload.get("event", {})),
                    client_id,
                    channel="events",
                )

            elif channel.startswith("metrics:"):
                await manager.broadcast_to_client(
                    {
                        "type": "metric",
                        "metric": payload.get("metric"),
                        "value": payload.get("value"),
                        "metadata": payload.get("metadata", {}),
                    },
                    client_id,
                    channel="metrics",
                )

            elif channel.startswith("alerts:"):
                alert = payload.get("alert", {})
                await manager.broadcast_to_client(
                    {
                        "type": "alert",
                        "alert_id": alert.get("alert_id"),
                        "alert_name": alert.get("alert_name"),
                        "severity": alert.get("severity"),
                        "message": alert.get("message"),
                        "context": alert.get("context"),
                        "triggered_at": alert.get("triggered_at"),
                        "timestamp": alert.get("timestamp"),
                    },
                    client_id,
                    channel="alerts",
                )

        except json.JSONDecodeError:
            logger.error("Invalid JSON received from Redis")

        except Exception as e:
            logger.error(f"Error handling Redis message: {e}", exc_info=True)


# Global singleton
broadcaster = WebSocketBroadcaster()
