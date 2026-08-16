# backend/tests/integration/test_api_keys.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_api_key_creation_and_usage(client: AsyncClient, db_session):
    """Test API key creation and using it for authentication."""
    
    # 1. Register and login first
    register_data = {
        "email": "apikey_test@example.com",
        "password": "password123",
        "role": "user"
    }
    await client.post("/api/v1/auth/register", json=register_data)
    
    login_response = await client.post("/api/v1/auth/login", json={
        "email": "apikey_test@example.com",
        "password": "password123"
    })
    access_token = login_response.json()["access_token"]
    
    # 2. Create API key
    headers = {"Authorization": f"Bearer {access_token}"}
    key_data = {
        "client_name": "Test App",
        "rate_limit": 1000
    }
    
    response = await client.post(
        "/api/v1/api-keys/",
        json=key_data,
        headers=headers
    )
    assert response.status_code == 201
    key_response = response.json()
    assert "api_key" in key_response
    api_key = key_response["api_key"]
    assert api_key.startswith("ep_live_")
    
    # 3. Use API key to access protected endpoint
    response = await client.get(
        "/api/v1/health/protected",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
    assert response.json()["client_name"] == "Test App"