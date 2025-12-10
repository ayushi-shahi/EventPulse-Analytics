# backend/app/websockets/handlers.py
from fastapi import WebSocket
from typing import Dict, Any
import json


async def handle_client_message(
    websocket: WebSocket,
    message: dict,
    client_id: str,
    connection_id: str,
    manager
):
    """
    Handle incoming messages from WebSocket clients.
    
    Supported message types:
    - subscribe: Update channel subscriptions
    - ping: Keep-alive check
    - unsubscribe: Remove channel subscriptions
    
    Args:
        websocket: WebSocket connection
        message: Parsed message dict
        client_id: Client ID
        connection_id: Connection ID
        manager: ConnectionManager instance
    """
    message_type = message.get("type")
    
    if message_type == "ping":
        # Respond to ping with pong
        await manager.send_personal_message(
            {"type": "pong", "timestamp": message.get("timestamp")},
            client_id,
            connection_id
        )
    
    elif message_type == "subscribe":
        # Update subscriptions
        channels = message.get("channels", [])
        if channels:
            manager.update_subscriptions(connection_id, channels)
            await manager.send_personal_message(
                {
                    "type": "subscribed",
                    "channels": channels,
                    "message": f"Subscribed to {len(channels)} channel(s)"
                },
                client_id,
                connection_id
            )
    
    elif message_type == "unsubscribe":
        # Remove subscriptions
        channels = message.get("channels", [])
        current_subs = manager.subscriptions.get(connection_id, set())
        new_subs = current_subs - set(channels)
        manager.update_subscriptions(connection_id, list(new_subs))
        
        await manager.send_personal_message(
            {
                "type": "unsubscribed",
                "channels": channels,
                "message": f"Unsubscribed from {len(channels)} channel(s)"
            },
            client_id,
            connection_id
        )
    
    elif message_type == "get_stats":
        # Send connection statistics
        stats = manager.get_stats()
        await manager.send_personal_message(
            {
                "type": "stats",
                "data": stats
            },
            client_id,
            connection_id
        )
    
    else:
        # Unknown message type
        await manager.send_personal_message(
            {
                "type": "error",
                "message": f"Unknown message type: {message_type}"
            },
            client_id,
            connection_id
        )


def format_event_message(event_data: Dict[str, Any]) -> dict:
    """
    Format an event for WebSocket transmission.
    
    Args:
        event_data: Event data from database or queue
        
    Returns:
        Formatted message dict
    """
    return {
        "type": "event",
        "data": event_data,
        "timestamp": event_data.get("received_at")
    }


def format_metric_message(metric_name: str, value: Any, metadata: dict = None) -> dict:
    """
    Format a metric update for WebSocket transmission.
    
    Args:
        metric_name: Name of the metric
        value: Metric value
        metadata: Additional metadata
        
    Returns:
        Formatted message dict
    """
    return {
        "type": "metric",
        "metric": metric_name,
        "value": value,
        "metadata": metadata or {},
        "timestamp": metadata.get("timestamp") if metadata else None
    }


def format_alert_message(alert_data: dict) -> dict:
    """
    Format an alert for WebSocket transmission.
    
    Args:
        alert_data: Alert information
        
    Returns:
        Formatted message dict
    """
    return {
        "type": "alert",
        "data": alert_data,
        "severity": alert_data.get("severity", "info"),
        "timestamp": alert_data.get("timestamp")
    }