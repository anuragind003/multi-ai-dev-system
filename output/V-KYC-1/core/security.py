from datetime import datetime, timedelta, timezone
from typing import Optional, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from schemas import TokenData
from config import settings
from models import UserRole
from loguru import logger

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction from Authorization header
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
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> TokenData:
    """Decodes and validates a JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return TokenData(username=username, roles=[UserRole(role) for role in roles])
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency to get the current authenticated user from the token."""
    from crud import user_crud # Import locally to avoid circular dependency
    from database import get_db
    from sqlalchemy.orm import Session

    token_data = decode_access_token(token)
    
    # Get a DB session for this dependency
    db_gen = get_db()
    db: Session = next(db_gen) # Get the session
    
    try:
        user = user_crud.get_user_by_username(db, token_data.username)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return user
    finally:
        db_gen.close() # Ensure the session is closed

async def get_current_active_user(current_user: dict = Depends(get_current_user)):
    """Dependency to get the current active authenticated user."""
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

def require_roles(roles: List[UserRole]):
    """
    Dependency factory to enforce role-based access control.
    Usage: Depends(require_roles([UserRole.ADMIN, UserRole.AUDITOR]))
    """
    async def role_checker(current_user: dict = Depends(get_current_active_user)):
        if current_user.role not in roles:
            logger.warning(f"User '{current_user.username}' (Role: {current_user.role.value}) attempted to access restricted resource. Required roles: {[r.value for r in roles]}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required roles: {[role.value for role in roles]}"
            )
        return current_user
    return role_checker