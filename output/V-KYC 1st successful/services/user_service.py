import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError

from core.exceptions import ConflictException, NotFoundException, UnauthorizedException
from models.models import User, UserRole
from schemas.schemas import UserCreate, UserLogin, UserResponse
from security.dependencies import get_password_hash, verify_password, create_access_token
from core.config import settings
from core.logger import logger

class UserService:
    """
    Service class for managing user-related business logic.
    Handles user CRUD operations and authentication.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetches a user by their username."""
        result = await self.db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetches a user by their email."""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Creates a new user.
        Raises ConflictException if username or email already exists.
        """
        existing_user_by_username = await self.get_user_by_username(user_in.username)
        if existing_user_by_username:
            raise ConflictException(detail="Username already registered")

        existing_user_by_email = await self.get_user_by_email(user_in.email)
        if existing_user_by_email:
            raise ConflictException(detail="Email already registered")

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=True
        )
        self.db.add(db_user)
        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User '{db_user.username}' created successfully.")
            return db_user
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error during user creation: {e}")
            raise ConflictException(detail="Username or email already registered.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise

    async def authenticate_user(self, user_login: UserLogin) -> User:
        """
        Authenticates a user by username and password.
        Raises UnauthorizedException if credentials are invalid.
        """
        user = await self.get_user_by_username(user_login.username)
        if not user or not verify_password(user_login.password, user.hashed_password):
            raise UnauthorizedException(detail="Incorrect username or password")
        if not user.is_active:
            raise UnauthorizedException(detail="Inactive user")
        logger.info(f"User '{user.username}' authenticated successfully.")
        return user

    async def create_access_token_for_user(self, user: User) -> str:
        """Generates an access token for a given user."""
        access_token_expires = datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Define scopes based on user role
        scopes = ["me"]
        if user.role == UserRole.ADMIN:
            scopes.extend(["users:read", "users:write", "test_cases:read", "test_cases:write", "test_runs:read", "test_runs:write", "test_runs:execute"])
        elif user.role == UserRole.QA_ENGINEER:
            scopes.extend(["test_cases:read", "test_cases:write", "test_runs:read", "test_runs:write", "test_runs:execute"])
        elif user.role == UserRole.DEVELOPER:
            scopes.extend(["test_cases:read", "test_runs:read"])
        elif user.role == UserRole.VIEWER:
            scopes.extend(["test_cases:read", "test_runs:read"])

        token_data = {"sub": user.username, "scopes": scopes}
        return create_access_token(token_data, expires_delta=access_token_expires)

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetches a user by their ID."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Fetches all users with pagination."""
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    async def update_user(self, user_id: int, user_update: UserCreate) -> User:
        """
        Updates an existing user.
        Raises NotFoundException if user does not exist.
        Raises ConflictException if updated username/email already exists.
        """
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found")

        # Check for username/email conflicts if they are being updated
        if user_update.username and user_update.username != db_user.username:
            existing_user = await self.get_user_by_username(user_update.username)
            if existing_user and existing_user.id != user_id:
                raise ConflictException(detail="Username already taken")
        
        if user_update.email and user_update.email != db_user.email:
            existing_user = await self.get_user_by_email(user_update.email)
            if existing_user and existing_user.id != user_id:
                raise ConflictException(detail="Email already taken")

        for key, value in user_update.model_dump(exclude_unset=True).items():
            if key == "password":
                setattr(db_user, "hashed_password", get_password_hash(value))
            else:
                setattr(db_user, key, value)
        
        db_user.updated_at = datetime.datetime.now(datetime.timezone.utc)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' (ID: {db_user.id}) updated.")
        return db_user

    async def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user.
        Raises NotFoundException if user does not exist.
        """
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(detail="User not found")
        
        await self.db.delete(db_user)
        await self.db.commit()
        logger.info(f"User '{db_user.username}' (ID: {db_user.id}) deleted.")
        return True