from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from models import User
from core.security import verify_password, get_password_hash, create_access_token
from services.user_service import UserService
from core.exceptions import UnauthorizedException, ConflictException
from config import settings
from utils.logger import setup_logging

logger = setup_logging()

class AuthService:
    """
    Service layer for authentication-related business logic.
    Handles user creation, authentication, and token generation.
    """
    def __init__(self, user_service: UserService = UserService()):
        self.user_service = user_service

    def create_user(self, db: Session, email: str, hashed_password: str) -> User:
        """
        Creates a new user in the database.
        Args:
            db: Database session.
            email: User's email.
            hashed_password: Hashed password for the user.
        Returns:
            The newly created User object.
        Raises:
            ConflictException: If a user with the given email already exists.
        """
        logger.debug(f"Attempting to create user: {email}")
        db_user = self.user_service.get_user_by_email(db, email)
        if db_user:
            logger.warning(f"User creation failed: Email '{email}' already exists.")
            raise ConflictException(detail="Email already registered")

        user = User(email=email, hashed_password=hashed_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User '{email}' created successfully with ID: {user.id}")
        return user

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticates a user by verifying their email and password.
        Args:
            db: Database session.
            email: User's email.
            password: Raw password provided by the user.
        Returns:
            The authenticated User object if credentials are valid, otherwise None.
        """
        logger.debug(f"Attempting to authenticate user: {email}")
        user = self.user_service.get_user_by_email(db, email)
        if not user:
            logger.warning(f"Authentication failed for '{email}': User not found.")
            return None
        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed for '{email}': Invalid password.")
            return None
        if not user.is_active:
            logger.warning(f"Authentication failed for '{email}': User is inactive.")
            raise UnauthorizedException(detail="Inactive user")

        logger.info(f"User '{email}' authenticated successfully.")
        return user

    def create_access_token(self, data: dict) -> str:
        """
        Creates a JWT access token.
        Args:
            data: Dictionary containing claims to be encoded in the token (e.g., {"sub": user_email}).
        Returns:
            The encoded JWT access token string.
        """
        logger.debug(f"Creating access token for data: {data.get('sub')}")
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        token = create_access_token(to_encode)
        logger.info(f"Access token created for {data.get('sub')}, expires at {expire}.")
        return token