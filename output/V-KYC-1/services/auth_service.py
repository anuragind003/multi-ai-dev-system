from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import settings
from models import User, UserRole
from schemas import UserCreate, UserLogin, UserResponse, Token
from security.dependencies import get_password_hash, verify_password
from core.exceptions import CustomHTTPException
from core.logging_config import setup_logging

logger = setup_logging()

class AuthService:
    """
    Service layer for user authentication and authorization.
    Handles user registration, login, and JWT token management.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetches a user by username."""
        result = await self.db.execute(select(User).filter(User.username == username))
        return result.scalars().first()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetches a user by email."""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetches a user by ID."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def register_user(self, user_data: UserCreate) -> UserResponse:
        """
        Registers a new user.
        Raises CustomHTTPException if username or email already exists.
        """
        logger.info(f"Attempting to register user: {user_data.username}")
        existing_user = await self.db.execute(
            select(User).filter(or_(User.username == user_data.username, User.email == user_data.email))
        )
        if existing_user.scalars().first():
            logger.warning(f"Registration failed: Username or email already exists for {user_data.username}")
            raise CustomHTTPException(
                status_code=409,
                detail="Username or email already registered.",
                code="USER_ALREADY_EXISTS"
            )

        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            role=user_data.role
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' registered successfully with role '{db_user.role}'.")
        return UserResponse.from_orm(db_user)

    async def authenticate_user(self, user_login: UserLogin) -> User:
        """
        Authenticates a user by username and password.
        Raises CustomHTTPException for invalid credentials.
        """
        logger.info(f"Attempting to authenticate user: {user_login.username}")
        user = await self.get_user_by_username(user_login.username)
        if not user or not verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Authentication failed for user: {user_login.username} - Invalid credentials.")
            raise CustomHTTPException(
                status_code=401,
                detail="Incorrect username or password.",
                code="INVALID_CREDENTIALS"
            )
        if not user.is_active:
            logger.warning(f"Authentication failed for user: {user_login.username} - User is inactive.")
            raise CustomHTTPException(
                status_code=403,
                detail="User account is inactive.",
                code="USER_INACTIVE"
            )
        logger.info(f"User '{user.username}' authenticated successfully.")
        return user

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> Token:
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
        logger.debug(f"Access token created for data: {data}")
        return Token(access_token=encoded_jwt)