from datetime import datetime, timedelta, timezone
from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis.asyncio import Redis
from fastapi_limiter import FastAPILimiter

from config import settings, logger
from schemas import TokenData
from models import User, UserRole
from database import get_db
from sqlalchemy.orm import Session

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2PasswordBearer for token extraction from headers
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")

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

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises HTTPException if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, scopes=payload.get("scopes", []))
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to ensure the user is active (no specific 'active' field, just exists)."""
    return current_user

async def get_current_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to ensure the user has 'admin' role."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    return current_user

async def get_current_auditor_or_admin_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to ensure the user has 'auditor' or 'admin' role."""
    if current_user.role not in [UserRole.AUDITOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Auditor or Admin role required."
        )
    return current_user

# --- Rate Limiting Initialization ---
async def init_rate_limiter():
    """Initializes the FastAPI-Limiter with Redis."""
    try:
        redis_client = Redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_client)
        logger.info("FastAPI-Limiter initialized with Redis.")
    except Exception as e:
        logger.error(f"Failed to initialize FastAPI-Limiter: {e}")
        # Depending on criticality, you might want to raise the exception or degrade gracefully
        # For now, we'll just log and let the app start, but rate limiting won't work.