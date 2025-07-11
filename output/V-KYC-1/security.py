from datetime import datetime, timedelta, timezone
from typing import Optional, List

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, status

from config import settings
from utils.exceptions import UnauthorizedException, ForbiddenException
from models import UserRole
from schemas import TokenData
from utils.logger import logger

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

def decode_access_token(token: str) -> TokenData:
    """Decodes a JWT access token and returns its payload."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        roles: List[str] = payload.get("roles", [])
        if username is None:
            raise UnauthorizedException(message="Could not validate credentials: Username missing.")
        
        # Convert string roles back to UserRole enum
        enum_roles = [UserRole(role) for role in roles if role in [e.value for e in UserRole]]
        
        return TokenData(username=username, roles=enum_roles)
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise UnauthorizedException(message="Could not validate credentials: Invalid token.")
    except ValueError as e: # For UserRole conversion errors
        logger.warning(f"Role conversion error: {e}")
        raise UnauthorizedException(message="Could not validate credentials: Invalid role in token.")

def require_role(required_roles: List[UserRole]):
    """
    Dependency to check if the current user has one of the required roles.
    """
    def _require_role(current_user_token_data: TokenData = Depends(oauth2_scheme)):
        token_data = decode_access_token(current_user_token_data) # Decode the token provided by OAuth2PasswordBearer
        
        if not token_data.username:
            raise UnauthorizedException(message="Not authenticated.")

        user_roles = set(token_data.roles)
        if not user_roles.intersection(set(required_roles)):
            logger.warning(f"User '{token_data.username}' with roles {list(user_roles)} attempted to access resource requiring roles {list(required_roles)}")
            raise ForbiddenException(message="Insufficient permissions.")
        return token_data
    return _require_role