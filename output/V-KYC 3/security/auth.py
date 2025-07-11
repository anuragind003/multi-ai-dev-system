from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import settings
from schemas.user import TokenData, UserResponse
from services.user_service import UserService
from utils.dependencies import get_user_service
from exceptions import UnauthorizedException, ForbiddenException

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token")

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
    return encoded_jwt

async def authenticate_user_dependency(
    email: str,
    password: str,
    user_service: UserService = Depends(get_user_service)
) -> Optional[UserResponse]:
    """
    Dependency to authenticate a user. Used by the /token endpoint.
    """
    user = await user_service.authenticate_user(email, password)
    if not user:
        raise UnauthorizedException(detail="Incorrect email or password")
    return user

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_service: UserService = Depends(get_user_service)
) -> UserResponse:
    """
    Dependency to get the current user from a JWT token.
    Raises UnauthorizedException if token is invalid or user not found.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}", exc_info=True)
        raise credentials_exception

    user = await user_service.get_user_by_email(email=token_data.email)
    if user is None:
        logger.warning(f"User from token not found in DB: {token_data.email}")
        raise credentials_exception
    return user

async def get_current_active_user(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Dependency to ensure the current user is active.
    """
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise ForbiddenException(detail="Inactive user")
    return current_user

async def get_current_active_superuser(current_user: UserResponse = Depends(get_current_active_user)) -> UserResponse:
    """
    Dependency to ensure the current user is an active superuser.
    """
    if not current_user.is_superuser:
        logger.warning(f"Non-superuser attempted superuser access: {current_user.email}")
        raise ForbiddenException(detail="The user doesn't have enough privileges")
    return current_user