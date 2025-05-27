import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext

# --- Configuration ---
# JWT settings for internal user authentication (e.g., Admin Portal users)
# It's crucial to set this via environment variables in production.
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-please-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# API Key for external integrations (e.g., Insta/E-aggregators)
# This key should be securely managed (e.g., environment variable, secrets manager).
EXTERNAL_API_KEY = os.getenv("EXTERNAL_API_KEY", "default-external-api-key-for-dev")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for token-based authentication (for Admin Portal users)
# The `tokenUrl` should point to your login endpoint where tokens are issued.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# APIKeyHeader for external API key authentication
# `auto_error=False` allows custom error handling for missing/invalid keys.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# --- Password Hashing Functions ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

# --- JWT Token Functions ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.

    Args:
        data (dict): The data to encode into the token (e.g., {"sub": username}).
        expires_delta (Optional[timedelta]): Optional timedelta for token expiration.
                                             If None, uses ACCESS_TOKEN_EXPIRE_MINUTES.

    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    """
    Decodes a JWT access token.

    Args:
        token (str): The JWT token string.

    Returns:
        dict: The decoded payload of the token.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- FastAPI Dependencies for User Authentication (Admin Portal) ---

# Placeholder for a User model/schema. In a real application, this would be
# a Pydantic model or an ORM model (e.g., from app.models.user).
class User:
    """A simple representation of a user for authentication purposes."""
    def __init__(self, username: str, is_active: bool = True):
        self.username = username
        self.is_active = is_active

    def __repr__(self):
        return f"User(username='{self.username}', is_active={self.is_active})"

# This function would typically fetch the user from the database based on the username.
# For this security module, we'll use a simple mock.
async def get_user_from_db(username: str) -> Optional[User]:
    """
    Simulates fetching a user from a database.
    In a real application, this would query your PostgreSQL database.
    """
    # Example mock user for demonstration
    if username == "admin":
        return User(username="admin", is_active=True)
    # Add other mock users if needed for testing
    # if username == "analyst":
    #     return User(username="analyst", is_active=True)
    return None

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    FastAPI dependency to get the current authenticated user from a JWT token.
    This function is used to protect routes that require a logged-in user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_from_db(username) # Simulate fetching user from DB
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency to get the current active authenticated user.
    Ensures the user is not marked as inactive.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

# --- FastAPI Dependency for External API Key Authentication ---
async def verify_external_api_key(api_key: str = Depends(api_key_header)):
    """
    FastAPI dependency to verify an external API key provided in the 'X-API-Key' header.
    This is used for securing endpoints exposed to external systems like Insta/E-aggregators.
    """
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing in X-API-Key header",
        )
    if api_key != EXTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API Key",
        )
    return True # Return True or a specific identifier if the key represents a client ID