from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import logging

from models import User
from schemas import UserCreate, UserUpdate
from core.exceptions import CustomException, ConflictException, NotFoundException

logger = logging.getLogger(__name__)

class UserCRUD:
    """
    CRUD operations for the User model.
    Handles database interactions for user-related data.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, user_in: UserCreate, hashed_password: str) -> User:
        """
        Creates a new user in the database.
        Raises ConflictException if username or email already exists.
        """
        try:
            db_user = User(
                username=user_in.username,
                email=user_in.email,
                hashed_password=hashed_password,
                role=user_in.role,
                is_active=True # New users are active by default
            )
            self.db.add(db_user)
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User '{db_user.username}' created successfully.")
            return db_user
        except IntegrityError:
            await self.db.rollback()
            logger.warning(f"Attempted to create user with existing username/email: {user_in.username}/{user_in.email}")
            raise ConflictException("Username or email already registered.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user {user_in.username}: {e}", exc_info=True)
            raise CustomException(f"Failed to create user: {e}")

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieves a list of users with pagination."""
        stmt = select(User).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_user(self, user_id: int, user_in: UserUpdate, hashed_password: Optional[str] = None) -> User:
        """
        Updates an existing user's information.
        Raises NotFoundException if user does not exist.
        Raises ConflictException if updated username/email already exists.
        """
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(f"User with ID {user_id} not found.")

        update_data = user_in.model_dump(exclude_unset=True)
        if hashed_password:
            update_data["hashed_password"] = hashed_password

        for key, value in update_data.items():
            setattr(db_user, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(db_user)
            logger.info(f"User '{db_user.username}' (ID: {user_id}) updated successfully.")
            return db_user
        except IntegrityError:
            await self.db.rollback()
            logger.warning(f"Attempted to update user {user_id} with existing username/email.")
            raise ConflictException("Username or email already registered by another user.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to update user: {e}")

    async def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user from the database.
        Raises NotFoundException if user does not exist.
        """
        db_user = await self.get_user_by_id(user_id)
        if not db_user:
            raise NotFoundException(f"User with ID {user_id} not found.")

        try:
            await self.db.delete(db_user)
            await self.db.commit()
            logger.info(f"User '{db_user.username}' (ID: {user_id}) deleted successfully.")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to delete user: {e}")