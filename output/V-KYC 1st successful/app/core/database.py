### FILE: app/core/security.py
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for Bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY.get_secret_value(), algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """Decodes a JWT access token."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY.get_secret_value(), algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.error(f"JWT decoding error: {e}")
        raise UnauthorizedException(detail="Could not validate credentials")

# --- User Management (Simplified for this example) ---
# In a real application, this would involve a database model for users
# and a service to interact with it.
class User:
    def __init__(self, username: str, hashed_password: str, disabled: bool = False):
        self.username = username
        self.hashed_password = hashed_password
        self.disabled = disabled

    def __repr__(self):
        return f"<User username={self.username}>"

# Mock user database (for demonstration)
# In a real app, users would be fetched from a DB
mock_users_db = {
    settings.ADMIN_USERNAME: User(
        username=settings.ADMIN_USERNAME,
        hashed_password=get_password_hash(settings.ADMIN_PASSWORD.get_secret_value())
    )
}

async def get_user(username: str) -> Optional[User]:
    """Fetches a user from the mock database."""
    # Simulate async DB call
    await asyncio.sleep(0.01)
    return mock_users_db.get(username)

async def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticates a user against the mock database."""
    user = await get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Dependency to get the current authenticated user."""
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise UnauthorizedException(detail="Could not validate credentials")
    user = await get_user(username)
    if user is None:
        raise UnauthorizedException(detail="User not found")
    if user.disabled:
        raise UnauthorizedException(detail="User is inactive")
    return user

# This import is needed for `asyncio.sleep` in `get_user`
import asyncio