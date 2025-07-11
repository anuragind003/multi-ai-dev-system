from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import User, UserRole
from schemas import UserCreate, UserLogin, Token
from auth.security import get_password_hash, verify_password, create_access_token
from core.exceptions import UserAlreadyExistsException, UnauthorizedException
import logging

logger = logging.getLogger(__name__)

class UserService:
    """
    Service layer for user-related business logic.
    Handles user creation, authentication, and retrieval.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_in: UserCreate) -> User:
        """
        Creates a new user in the database.

        Args:
            user_in (UserCreate): Pydantic model containing user details.

        Returns:
            User: The newly created User ORM object.

        Raises:
            UserAlreadyExistsException: If a user with the given username or email already exists.
        """
        # Check if username already exists
        existing_user_by_username = await self.get_user_by_username(user_in.username)
        if existing_user_by_username:
            raise UserAlreadyExistsException(f"User with username '{user_in.username}' already exists.")

        # Check if email already exists (if provided)
        if user_in.email:
            existing_user_by_email = await self.get_user_by_email(user_in.email)
            if existing_user_by_email:
                raise UserAlreadyExistsException(f"User with email '{user_in.email}' already exists.")

        hashed_password = get_password_hash(user_in.password)
        db_user = User(
            username=user_in.username,
            hashed_password=hashed_password,
            email=user_in.email,
            full_name=user_in.full_name,
            role=user_in.role,
            is_active=True
        )
        self.db.add(db_user)
        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User '{db_user.username}' created successfully with role '{db_user.role}'.")
            return db_user
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error during user creation: {e}", exc_info=True)
            raise UserAlreadyExistsException("A user with this username or email already exists.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error during user creation: {e}", exc_info=True)
            raise

    async def authenticate_user(self, username: str, password: str) -> Token:
        """
        Authenticates a user and generates an access token.

        Args:
            username (str): The user's username.
            password (str): The user's plain password.

        Returns:
            Token: A Pydantic model containing the access token.

        Raises:
            UnauthorizedException: If authentication fails.
        """
        user = await self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException(detail="Incorrect username or password")
        if not user.is_active:
            raise UnauthorizedException(detail="Inactive user")

        access_token_data = {
            "sub": user.username,
            "user_id": user.id,
            "roles": [user.role.value] # Store roles as list of strings
        }
        access_token = create_access_token(access_token_data)
        logger.info(f"User '{username}' authenticated successfully.")
        return Token(access_token=access_token)

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        result = await self.db.execute(select(User).filter(User.username == username))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email."""
        result = await self.db.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_all_users(self) -> List[User]:
        """Retrieves all users from the database."""
        result = await self.db.execute(select(User))
        return result.scalars().all()