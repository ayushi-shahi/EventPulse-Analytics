# backend/app/api/v1/websockets.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import json

from app.database import get_db
from app.models.api_key import APIKey
from app.core.security import hash_api_key, decode_token
from app.websockets.manager import manager
from app.websockets.handlers import handle_client_message
from sqlalchemy import select

router = APIRouter()


async def get_api_key_from_token(token: str, client_id: str, db: AsyncSession) -> APIKey:
    """
    Authenticate a WebSocket connection.

    Accepts either credential, mirroring the REST dependency:

    1. **The API key secret.** Hashed and matched against the indexed
       `key_hash` column — one lookup. The previous implementation loaded every
       active key in the system and bcrypt-compared them one by one, so cost
       grew with total keys across all accounts, not with this request.

    2. **The owner's session JWT.** Keys are stored hashed and the secret is
       shown only once, so a dashboard opened in a new browser has no secret to
       present. Without this the live feed could never connect and the UI sat
       permanently on "Offline".
    """
    # --- Route 1: the secret itself ---
    result = await db.execute(
        select(APIKey).where(
            APIKey.key_hash == hash_api_key(token),
            APIKey.is_active == True,  # noqa: E712 — SQL boolean
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key is not None:
        return api_key

    # --- Route 2: a session token naming one of the user's own keys ---
    payload = decode_token(token)
    user_id = (payload or {}).get("sub")
    if user_id:
        try:
            key_uuid = uuid.UUID(client_id)
        except (ValueError, AttributeError, TypeError):
            raise Exception("Invalid client id")

        result = await db.execute(
            select(APIKey).where(
                APIKey.id == key_uuid,
                APIKey.is_active == True,  # noqa: E712
            )
        )
        api_key = result.scalar_one_or_none()
        if api_key is not None and str(api_key.user_id) == str(user_id):
            return api_key

    raise Exception("Invalid credentials")


@router.websocket("/live/{client_id}")
async def websocket_live_feed(
    websocket: WebSocket,
    client_id: str,
    token: str = Query(..., description="API key secret, or the owner's session JWT"),
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint with connection limit"""
    connection_id = str(uuid.uuid4())
    
    try:
        # Authenticate
        api_key = await get_api_key_from_token(token, client_id, db)
        
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