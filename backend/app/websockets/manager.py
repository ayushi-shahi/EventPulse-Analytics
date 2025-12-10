# backend/app/websockets/manager.py
from typing import Dict, Set, List
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections for real-time updates.
    
    Supports:
    - Per-client connections (isolated by client_id)
    - Broadcasting to all connections for a client
    - Channel subscriptions (events, metrics, alerts)
    """
    
    def __init__(self):
        # Structure: {client_id: {connection_id: WebSocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}
        
        # Track which channels each connection is subscribed to
        # Structure: {connection_id: Set[channel_names]}
        self.subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata
        # Structure: {connection_id: {client_id, connected_at, user_info}}
        self.connection_metadata: Dict[str, dict] = {}
    
    async def connect(
        self, 
        websocket: WebSocket, 
        client_id: str, 
        connection_id: str,
        user_info: dict = None
    ):
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
            client_id: API key client ID
            connection_id: Unique connection identifier
            user_info: Optional metadata about the connection
        """
        await websocket.accept()
        
        # Initialize client connections if first connection
        if client_id not in self.active_connections:
            self.active_connections[client_id] = {}
        
        # Register connection
        self.active_connections[client_id][connection_id] = websocket
        
        # Initialize subscriptions (default: all channels)
        self.subscriptions[connection_id] = {"events", "metrics", "alerts"}
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "client_id": client_id,
            "connected_at": datetime.utcnow().isoformat(),
            "user_info": user_info or {}
        }
        
        print(f"✅ WebSocket connected: {connection_id} for client {client_id}")
    
    def disconnect(self, client_id: str, connection_id: str):
        """
        Remove a WebSocket connection.
        
        Args:
            client_id: API key client ID
            connection_id: Unique connection identifier
        """
        # Remove from active connections
        if client_id in self.active_connections:
            if connection_id in self.active_connections[client_id]:
                del self.active_connections[client_id][connection_id]
            
            # Clean up empty client entries
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        # Clean up subscriptions
        if connection_id in self.subscriptions:
            del self.subscriptions[connection_id]
        
        # Clean up metadata
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        print(f"❌ WebSocket disconnected: {connection_id}")
    
    async def send_personal_message(
        self, 
        message: dict, 
        client_id: str, 
        connection_id: str
    ):
        """
        Send message to a specific connection.
        
        Args:
            message: Dict to send as JSON
            client_id: Client ID
            connection_id: Specific connection ID
        """
        if client_id in self.active_connections:
            if connection_id in self.active_connections[client_id]:
                websocket = self.active_connections[client_id][connection_id]
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"Error sending to {connection_id}: {e}")
                    self.disconnect(client_id, connection_id)
    
    async def broadcast_to_client(
        self, 
        message: dict, 
        client_id: str,
        channel: str = "events"
    ):
        """
        Broadcast message to all connections for a specific client.
        
        Args:
            message: Dict to send as JSON
            client_id: Client ID to broadcast to
            channel: Channel name (filters by subscription)
        """
        if client_id not in self.active_connections:
            return
        
        # Get all connections for this client
        connections = self.active_connections[client_id].copy()
        
        # Send to each connection (if subscribed to channel)
        disconnected = []
        
        for connection_id, websocket in connections.items():
            # Check if connection is subscribed to this channel
            if connection_id in self.subscriptions:
                if channel not in self.subscriptions[connection_id]:
                    continue  # Skip if not subscribed
            
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Error broadcasting to {connection_id}: {e}")
                disconnected.append(connection_id)
        
        # Clean up disconnected clients
        for connection_id in disconnected:
            self.disconnect(client_id, connection_id)
    
    async def broadcast_to_all(self, message: dict, channel: str = "events"):
        """
        Broadcast message to ALL active connections (all clients).
        
        Args:
            message: Dict to send as JSON
            channel: Channel name (filters by subscription)
        """
        for client_id in list(self.active_connections.keys()):
            await self.broadcast_to_client(message, client_id, channel)
    
    def update_subscriptions(
        self, 
        connection_id: str, 
        channels: List[str]
    ):
        """
        Update channel subscriptions for a connection.
        
        Args:
            connection_id: Connection to update
            channels: List of channel names to subscribe to
        """
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id] = set(channels)
    
    def get_stats(self) -> dict:
        """
        Get connection statistics.
        
        Returns:
            Dict with connection counts and details
        """
        total_connections = sum(
            len(conns) for conns in self.active_connections.values()
        )
        
        return {
            "total_connections": total_connections,
            "clients_connected": len(self.active_connections),
            "connections_per_client": {
                client_id: len(conns)
                for client_id, conns in self.active_connections.items()
            }
        }


# Global connection manager instance
manager = ConnectionManager()