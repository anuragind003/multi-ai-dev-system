from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from core.exceptions import UnauthorizedException
from schemas import TokenData
from core.logging_config import setup_logging

logger = setup_logging()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> TokenData:
    """
    Decodes a JWT token and returns the payload as TokenData.
    Raises UnauthorizedException if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")
        email: str = payload.get("email")
        roles: list[str] = payload.get("roles", [])
        permissions: list[str] = payload.get("permissions", [])

        if user_id is None or email is None:
            raise UnauthorizedException(detail="Could not validate credentials: Missing user info")
        
        token_data = TokenData(user_id=user_id, email=email, roles=roles, permissions=permissions)
        logger.debug(f"Token decoded successfully for user_id: {user_id}")
        return token_data
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        raise UnauthorizedException(detail="Could not validate credentials: Invalid token") from e
    except Exception as e:
        logger.error(f"Unexpected error during token decoding: {e}")
        raise UnauthorizedException(detail="Could not validate credentials: Token processing error") from e