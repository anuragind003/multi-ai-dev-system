from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import get_settings
from models import User
from schemas import TokenData
from utils.exceptions import HTTPUnauthorized, HTTPForbidden, HTTPBadRequest
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """
    Service layer for authentication-related business logic.
    Handles password hashing, verification, and JWT operations.
    """

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hashes a plain password."""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """
        Creates a JWT access token.
        Args:
            data: Dictionary containing claims to be encoded in the token.
            expires_delta: Optional timedelta for token expiration.
        Returns:
            Encoded JWT string.
        """
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.info(f"Access token created for user: {data.get('sub')}")
        return encoded_jwt

    def decode_access_token(self, token: str) -> TokenData:
        """
        Decodes a JWT access token and returns its payload.
        Raises HTTPUnauthorized if token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                logger.warning("Token payload missing 'sub' (username).")
                raise HTTPUnauthorized(detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
            token_data = TokenData(username=username)
            logger.debug(f"Token decoded successfully for user: {username}")
            return token_data
        except JWTError as e:
            logger.warning(f"JWT decoding error: {e}")
            raise HTTPUnauthorized(detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
        except Exception as e:
            logger.error(f"Unexpected error during token decoding: {e}")
            raise HTTPUnauthorized(detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})

    def authenticate_user(self, db: Session, username: str, password: str) -> Optional[User]:
        """
        Authenticates a user by username and password.
        Returns the User object if credentials are valid, else None.
        """
        from services.user_service import UserService # Avoid circular import
        user_service = UserService()
        user = user_service.get_user_by_username(db, username)
        if not user:
            logger.warning(f"Authentication failed: User '{username}' not found.")
            return None
        if not self.verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Invalid password for user '{username}'.")
            return None
        if not user.is_active:
            logger.warning(f"Authentication failed: User '{username}' is inactive.")
            raise HTTPForbidden(detail="Inactive user")
        logger.info(f"User '{username}' authenticated successfully.")
        return user