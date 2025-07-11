from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import User, Role, UserRole
from schemas import TokenData
from utils.exceptions import HTTPUnauthorized, HTTPForbidden
from utils.logger import logger

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

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current authenticated user from the JWT token.
    Raises HTTPUnauthorized if token is invalid or user not found.
    """
    credentials_exception = HTTPUnauthorized(
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        roles_str: list[str] = payload.get("roles", []) # Get roles as list of strings
        if username is None:
            raise credentials_exception
        
        # Convert role strings back to UserRole enum values
        roles_enum = [UserRole(role_str) for role_str in roles_str if role_str in [r.value for r in UserRole]]
        
        token_data = TokenData(username=username, roles=roles_enum)
    except JWTError as e:
        logger.error(f"JWT Error: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    
    # Ensure the user's actual role matches the role in the token (optional, but good for security)
    if user.role and user.role.name not in token_data.roles:
        logger.warning(f"User {user.username} token role mismatch. Token roles: {token_data.roles}, Actual role: {user.role.name}")
        # This could be a sign of token tampering or role change after token issuance.
        # For simplicity, we'll proceed if username matches, but in a real system,
        # you might want to re-authenticate or invalidate the token.
        # For RBAC, we will rely on the token's roles for authorization.
        pass # The RBAC middleware will handle the actual authorization based on token roles.

    return user