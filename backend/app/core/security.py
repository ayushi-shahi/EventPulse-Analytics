# backend/app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings


# -----------------------------------
# Password Hashing (bcrypt)
# -----------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against its bcrypt hashed version.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    """
    return pwd_context.hash(password)


# -----------------------------------
# Token Creation (JWT)
# -----------------------------------
def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a short-lived JWT access token.
    
    Args:
        data: Claims to encode (example: {"sub": user_id})
        expires_delta: Custom expiry timeout (optional)
    """
    to_encode = data.copy()

    expire = (
        datetime.now(timezone.utc) + expires_delta
        if expires_delta
        else datetime.now(timezone.utc) + settings.access_token_expire
    )

    to_encode.update({
        "exp": expire,
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a long-lived refresh token.
    """
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + settings.refresh_token_expire

    to_encode.update({
        "exp": expire,
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


# -----------------------------------
# Decode Token
# -----------------------------------
def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode & validate a JWT token. 
    Returns payload if valid, else None.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
