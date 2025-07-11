from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hashes a plain password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Creates a JWT access token.
    Args:
        data (dict): The payload to encode into the token.
        expires_delta (Optional[timedelta]): Optional timedelta for token expiration.
                                             If None, uses default from settings.
    Returns:
        str: The encoded JWT token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    logger.debug(f"Access token created for user: {data.get('sub')}")
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """
    Verifies a JWT token and returns its payload.
    Args:
        token (str): The JWT token to verify.
    Returns:
        Optional[dict]: The decoded payload if valid, None otherwise.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        logger.debug(f"Token verified successfully. Payload: {payload.get('sub')}")
        return payload
    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}")
        return None

# Example user data (for demonstration, replace with actual DB lookup)
# In a real application, this would come from a database or identity provider
FAKE_USERS_DB = {
    "john.doe": {
        "username": "john.doe",
        "email": "john.doe@example.com",
        "full_name": "John Doe",
        "disabled": False,
        "hashed_password": get_password_hash("securepassword"),
        "scopes": ["user"],
    },
    "admin.user": {
        "username": "admin.user",
        "email": "admin.user@example.com",
        "full_name": "Admin User",
        "disabled": False,
        "hashed_password": get_password_hash("adminpassword"),
        "scopes": ["admin", "user"],
    },
    "auditor.user": {
        "username": "auditor.user",
        "email": "auditor.user@example.com",
        "full_name": "Auditor User",
        "disabled": False,
        "hashed_password": get_password_hash("auditorpassword"),
        "scopes": ["auditor", "user"],
    },
}

def get_user(username: str) -> Optional[dict]:
    """
    Retrieves user data from a mock database.
    In a real app, this would query your user database.
    """
    if username in FAKE_USERS_DB:
        user_dict = FAKE_USERS_DB[username]
        # Create a copy to avoid modifying the original dict
        # and remove hashed_password for security before returning
        user_copy = user_dict.copy()
        user_copy.pop("hashed_password", None)
        return user_copy
    return None