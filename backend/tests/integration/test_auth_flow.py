# backend/tests/integration/test_auth_flow.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    """Test complete auth flow: register -> login -> access protected endpoint."""
    
    # 1. Register user
    register_data = {
        "email": "test@example.com",
        "password": "secure_password_123",
        "role": "user"
    }
    
    response = await client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 201
    user_data = response.json()
    assert user_data["email"] == "test@example.com"
    assert "id" in user_data
    
    # 2. Login
    login_data = {
        "email": "test@example.com",
        "password": "secure_password_123"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    
    access_token = token_data["access_token"]
    
    # 3. Access protected endpoint
    headers = {"Authorization": f"Bearer {access_token}"}
    response = await client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_invalid_login(client: AsyncClient):
    """Test login with invalid credentials."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "wrong_password"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401