from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.errors import ConflictException, UnauthorizedException
from app.core.logging_config import logger
from app.models.user import User
from app.schemas.common import Token, UserCreate, UserLogin

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    """
    Service layer for user authentication and authorization.
    Handles user creation, password hashing, and JWT token management.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verifies a plain password against a hashed password."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hashes a plain password."""
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Creates a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by username from the database."""
        result = await self.db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()

    async def register_user(self, user_data: UserCreate) -> User:
        """
        Registers a new user.
        Raises ConflictException if username already exists.
        """
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            logger.warning(f"Attempted to register existing username: {user_data.username}")
            raise ConflictException(detail="Username already registered.")

        hashed_password = self.get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            role=user_data.role
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User registered: {db_user.username} with role {db_user.role}")
        return db_user

    async def authenticate_user(self, user_login: UserLogin) -> Token:
        """
        Authenticates a user and generates a JWT token.
        Raises UnauthorizedException on invalid credentials.
        """
        user = await self.get_user_by_username(user_login.username)
        if not user or not self.verify_password(user_login.password, user.hashed_password):
            logger.warning(f"Failed login attempt for username: {user_login.username}")
            raise UnauthorizedException(detail="Incorrect username or password")

        # In a real app, scopes would be based on user roles/permissions
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            data={"sub": user.username, "scopes": [user.role]},
            expires_delta=access_token_expires
        )
        logger.info(f"User authenticated: {user.username}")
        return Token(access_token=access_token)