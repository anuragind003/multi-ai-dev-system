from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import TokenData
from app.crud import user_crud
from app.models import User
from app.db import get_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.core.logging import get_logger

logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for JWT token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")

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
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"JWT token created, expires at: {expire}")
    return encoded_jwt

def decode_access_token(token: str) -> TokenData:
    """Decodes a JWT access token and returns its payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            logger.warning("Invalid token payload: missing email or user_id.")
            raise UnauthorizedException(detail="Could not validate credentials")
        token_data = TokenData(email=email, user_id=user_id)
        logger.debug(f"Token decoded for user: {email}")
        return token_data
    except JWTError as e:
        logger.error(f"JWT decoding error: {e}")
        raise UnauthorizedException(detail="Could not validate credentials")

async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    token_data = decode_access_token(token)
    user = await user_crud.get_user_by_id(db, token_data.user_id)
    if user is None:
        logger.warning(f"Authenticated user ID {token_data.user_id} not found in DB.")
        raise UnauthorizedException(detail="User not found")
    logger.debug(f"Current user retrieved: {user.email}")
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the current active authenticated user.
    Raises ForbiddenException if user is inactive.
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user {current_user.email} attempted to access protected resource.")
        raise ForbiddenException(detail="Inactive user")
    return current_user

async def get_current_active_superuser(current_user: User = Depends(get_current_active_user)) -> User:
    """
    Dependency to get the current active authenticated superuser.
    Raises ForbiddenException if user is not a superuser.
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser {current_user.email} attempted to access superuser resource.")
        raise ForbiddenException(detail="The user doesn't have enough privileges")
    return current_user