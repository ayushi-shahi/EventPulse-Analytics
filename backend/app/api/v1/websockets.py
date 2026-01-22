# backend/app/api/v1/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import json

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import verify_api_key
from app.websockets.manager import manager
from app.websockets.handlers import handle_client_message
from sqlalchemy import select

router = APIRouter()


async def get_api_key_from_token(token: str, db: AsyncSession) -> APIKey:
    """
    Validate API key for WebSocket connection.
    
    Args:
        token: API key from query parameter
        db: Database session
        
    Returns:
        APIKey object if valid
        
    Raises:
        Exception if invalid
    """
    # Query all active API keys
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)
    )
    api_keys = result.scalars().all()
    
    # Find matching key
    for key in api_keys:
        if verify_api_key(token, key.key_hash):
            return key
    
    raise Exception("Invalid API key")


@router.websocket("/live/{client_id}")
async def websocket_live_feed(
    websocket: WebSocket,
    client_id: str,
    token: str = Query(..., description="API key for authentication"),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint with connection limit"""
    connection_id = str(uuid.uuid4())
    
    try:
        # Authenticate
        api_key = await get_api_key_from_token(token, db)
        
        if str(api_key.id) != client_id:
            await websocket.close(code=1008, reason="Client ID mismatch")
            return
        
        # Connect (with rate limit check)
        connected = await manager.connect(
            websocket, 
            client_id, 
            connection_id,
            user_info={"api_key_name": api_key.client_name}
        )
        
        if not connected:
            # Connection rejected (limit reached)
            return
        
        
        # Send welcome message
        await manager.send_personal_message(
            {
                "type": "connected",
                "connection_id": connection_id,
                "client_id": client_id,
                "message": "WebSocket connected successfully",
                "subscriptions": ["events", "metrics", "alerts"]
            },
            client_id,
            connection_id
        )
        
        # Listen for messages from client
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(
                    websocket,
                    message,
                    client_id,
                    connection_id,
                    manager
                )
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "message": "Invalid JSON"
                    },
                    client_id,
                    connection_id
                )
    
    except WebSocketDisconnect:
        manager.disconnect(client_id, connection_id)
        print(f"Client {connection_id} disconnected normally")
    
    except Exception as e:
        manager.disconnect(client_id, connection_id)
        print(f"WebSocket error for {connection_id}: {e}")
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@router.get("/connections")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.
    
    Returns info about active connections.
    """
    return manager.get_stats()