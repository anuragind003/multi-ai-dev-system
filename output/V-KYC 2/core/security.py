from datetime import datetime, timedelta
from typing import Optional, Annotated
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import settings
from schemas import TokenData
from models import User
from database import get_db
from services.user_service import UserService
from core.exceptions import UnauthorizedException
from utils.logger import setup_logging

logger = setup_logging()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for JWT token extraction from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain password against a hashed password.
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hashes a plain password.
    """
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    """
    Creates a JWT access token.
    Args:
        data: Dictionary containing claims to be encoded in the token.
    Returns:
        The encoded JWT access token string.
    """
    to_encode = data.copy()
    # Ensure 'exp' claim is present and is a datetime object
    if "exp" not in to_encode:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
    user_service: Annotated[UserService, Depends(UserService)]
) -> User:
    """
    Dependency to get the current authenticated user from a JWT token.
    Raises UnauthorizedException if token is invalid or user not found/inactive.
    """
    credentials_exception = UnauthorizedException(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("JWT payload missing 'sub' claim.")
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise credentials_exception

    user = user_service.get_user_by_email(db, token_data.email)
    if user is None:
        logger.warning(f"User '{token_data.email}' not found in DB for authenticated token.")
        raise credentials_exception
    if not user.is_active:
        logger.warning(f"User '{token_data.email}' is inactive.")
        raise UnauthorizedException(detail="Inactive user")
    
    logger.debug(f"User '{user.email}' successfully authenticated via JWT.")
    return user