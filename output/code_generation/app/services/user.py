from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from app.utils.logger import logger

class UserService:
    """
    Service layer for user-related business logic.
    Handles interactions with the database and applies business rules.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(self, user_in: UserCreate) -> UserResponse:
        """
        Creates a new user in the database.
        Hashes the password before saving.
        Raises ConflictException if a user with the same email already exists.
        """
        logger.info(f"Attempting to create user with email: {user_in.email}")
        existing_user = await self.get_user_by_email(user_in.email)
        if existing_user:
            logger.warning(f"User creation failed: Email '{user_in.email}' already exists.")
            raise ConflictException(detail="User with this email already exists")

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            email=user_in.email,
            hashed_password=hashed_password,
            is_active=True # New users are active by default
        )
        self.db_session.add(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)
        logger.info(f"User '{db_user.email}' created successfully with ID: {db_user.id}")
        return UserResponse.model_validate(db_user)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Retrieves a user by their email address.
        """
        logger.debug(f"Fetching user by email: {email}")
        result = await self.db_session.execute(
            select(User).filter(func.lower(User.email) == func.lower(email))
        )
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found: {user.email}")
        else:
            logger.debug(f"User not found for email: {email}")
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID.
        """
        logger.debug(f"Fetching user by ID: {user_id}")
        result = await self.db_session.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user:
            logger.debug(f"User found: {user.id}")
        else:
            logger.debug(f"User not found for ID: {user_id}")
        return user

    async def authenticate_user(self, email: str, password: str) -> User:
        """
        Authenticates a user by email and password.
        Raises UnauthorizedException if authentication fails.
        """
        logger.info(f"Attempting to authenticate user: {email}")
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed for user: {email}")
            raise UnauthorizedException(detail="Incorrect email or password")
        if not user.is_active:
            logger.warning(f"Authentication failed: User '{email}' is inactive.")
            raise UnauthorizedException(detail="Inactive user")
        logger.info(f"User '{email}' authenticated successfully.")
        return user

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """
        Retrieves a list of users with pagination.
        """
        logger.debug(f"Fetching users with skip={skip}, limit={limit}")
        result = await self.db_session.execute(
            select(User).offset(skip).limit(limit)
        )
        users = result.scalars().all()
        logger.debug(f"Retrieved {len(users)} users.")
        return [UserResponse.model_validate(user) for user in users]