import datetime
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.models import User, UserRole
from app.schemas import TokenData

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """Creates a JWT refresh token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(datetime.timezone.utc) + expires_delta
    else:
        expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    """Decodes a JWT token and returns its payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        roles: list = payload.get("roles", [])
        if email is None or user_id is None:
            raise UnauthorizedException("Could not validate credentials.")
        return TokenData(email=email, user_id=user_id, roles=roles)
    except JWTError:
        logger.warning("Invalid token provided.")
        raise UnauthorizedException("Could not validate credentials.")

# --- Dependency Functions for Current User ---
def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Dependency to get the current user's token data."""
    return decode_token(token)

def get_current_active_user(current_user_data: TokenData = Depends(get_current_user)) -> TokenData:
    """Dependency to get the current active user's token data."""
    # In a real app, you'd fetch the user from DB and check is_active
    # For simplicity, we assume token implies active user for now.
    # If user.is_active is False:
    #    raise UnauthorizedException("Inactive user")
    return current_user_data

def get_current_admin_user(current_user_data: TokenData = Depends(get_current_active_user)) -> TokenData:
    """Dependency to get the current active admin user's token data."""
    if UserRole.ADMIN not in current_user_data.roles:
        raise ForbiddenException("Not enough permissions. Admin role required.")
    return current_user_data

def get_current_user_with_roles(required_roles: list[UserRole]):
    """
    Dependency factory to check if the current user has any of the required roles.
    Usage: Depends(get_current_user_with_roles([UserRole.ADMIN, UserRole.USER]))
    """
    def _get_current_user_with_roles(current_user_data: TokenData = Depends(get_current_active_user)) -> TokenData:
        if not any(role in current_user_data.roles for role in required_roles):
            raise ForbiddenException(f"Not enough permissions. One of {required_roles} roles required.")
        return current_user_data
    return _get_current_user_with_roles