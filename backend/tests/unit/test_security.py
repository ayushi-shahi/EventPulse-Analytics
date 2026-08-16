# backend/tests/unit/test_security.py
import pytest
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    verify_api_key
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "test_password_123"
    
    # Hash password
    hashed = get_password_hash(password)
    
    # Verify correct password
    assert verify_password(password, hashed) is True
    
    # Verify wrong password
    assert verify_password("wrong_password", hashed) is False


def test_jwt_tokens():
    """Test JWT token creation and decoding."""
    user_id = "test_user_123"
    
    # Create token
    token = create_access_token(data={"sub": user_id})
    
    # Decode token
    payload = decode_token(token)
    
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["type"] == "access"


def test_api_key_generation():
    """Test API key generation and verification."""
    # Generate key
    api_key = generate_api_key()
    
    # Check format
    assert api_key.startswith("ep_live_")
    assert len(api_key) > 20
    
    # Hash key
    key_hash = hash_api_key(api_key)
    
    # Verify
    assert verify_api_key(api_key, key_hash) is True
    assert verify_api_key("wrong_key", key_hash) is False