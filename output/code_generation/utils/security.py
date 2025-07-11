import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings
from models import User, UserRole
from exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token", scopes={
    UserRole.ADMIN.value: "Admin privileges",
    UserRole.PROCESS_MANAGER.value: "Process Manager privileges",
    UserRole.TEAM_LEAD.value: "Team Lead privileges"
})

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a password."""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes a JWT access token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise UnauthorizedException("Invalid token or token expired.")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Dependency to get the current authenticated user from the token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    from services import UserService # Import here to avoid circular dependency
    from database import get_db

    credentials_exception = UnauthorizedException("Could not validate credentials.")
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
    except JWTError:
        raise credentials_exception

    # Get a database session to fetch the user
    async for db_session in get_db(): # Manually iterate the async generator
        user_service = UserService(db_session)
        user = await user_service.get_user_by_username(username)
        if user is None:
            raise credentials_exception
        
        # Basic scope validation (can be more granular)
        if user.role.value not in token_scopes:
            logger.warning(f"User {user.username} token scopes {token_scopes} do not match actual role {user.role.value}.")
            raise UnauthorizedException("Token scopes do not match user role.")
        
        return user