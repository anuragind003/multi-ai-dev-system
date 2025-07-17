from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import logging

from config import settings
from core.exceptions import UnauthorizedException

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    Data should include 'sub' (subject, e.g., username), 'user_id', and 'roles'.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verifies a JWT token and returns its payload.
    Raises UnauthorizedException if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        roles: List[str] = payload.get("roles", [])

        if username is None or user_id is None:
            logger.warning("Token payload missing 'sub' or 'user_id'.")
            raise UnauthorizedException("Invalid token payload.")
        
        return {"username": username, "user_id": user_id, "roles": roles}
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        raise UnauthorizedException("Invalid or expired token.")
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}", exc_info=True)
        raise UnauthorizedException("Token verification failed due to an unexpected error.")