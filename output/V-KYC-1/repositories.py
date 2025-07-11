from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from models import User
from schemas import UserCreate, UserUpdate
from utils.exceptions import NotFoundException, ConflictException, DatabaseException
from utils.logger import get_logger

logger = get_logger(__name__)

class UserRepository:
    """
    Repository layer for User model, handling all database interactions.
    Abstracts direct SQLAlchemy operations from the service layer.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_data: UserCreate) -> User:
        """
        Creates a new user in the database.
        Raises ConflictException if username or email already exists.
        """
        try:
            new_user = User(
                username=user_data.username,
                email=user_data.email,
                hashed_password=user_data.password, # Password should be hashed before passing to repo
                role=user_data.role,
                is_active=user_data.is_active
            )
            self.db.add(new_user)
            await self.db.commit()
            await self.db.refresh(new_user)
            logger.info(f"User created: {new_user.username}")
            return new_user
        except IntegrityError as e:
            await self.db.rollback()
            if "users_username_key" in str(e):
                raise ConflictException(detail=f"User with username '{user_data.username}' already exists.")
            elif "users_email_key" in str(e):
                raise ConflictException(detail=f"User with email '{user_data.email}' already exists.")
            else:
                logger.error(f"Database integrity error during user creation: {e}", exc_info=True)
                raise DatabaseException(detail="Failed to create user due to a database integrity constraint.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating user {user_data.username}: {e}", exc_info=True)
            raise DatabaseException(detail=f"Failed to create user: {e}")

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """
        Retrieves a user by their ID.
        """
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"User with ID {user_id} not found.")
        return user

    async def get_by_username(self, username: str) -> Optional[User]:
        """
        Retrieves a user by their username.
        """
        result = await self.db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"User with username '{username}' not found.")
        return user

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Retrieves a list of all users with pagination.
        """
        result = await self.db.execute(select(User).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def update(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Updates an existing user's information.
        Raises NotFoundException if user does not exist.
        Raises ConflictException if updated username/email already exists.
        """
        existing_user = await self.get_by_id(user_id)
        if not existing_user:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        update_data = user_data.model_dump(exclude_unset=True)
        if not update_data:
            logger.info(f"No update data provided for user ID {user_id}.")
            return existing_user # No changes to apply

        try:
            stmt = update(User).where(User.id == user_id).values(**update_data).returning(User)
            result = await self.db.execute(stmt)
            updated_user = result.scalar_one_or_none()
            await self.db.commit()
            if updated_user:
                await self.db.refresh(updated_user)
                logger.info(f"User ID {user_id} updated.")
                return updated_user
            else:
                # This case should ideally not be reached if existing_user was found
                raise NotFoundException(detail=f"User with ID {user_id} not found during update operation.")
        except IntegrityError as e:
            await self.db.rollback()
            if "users_username_key" in str(e):
                raise ConflictException(detail=f"User with username '{user_data.username}' already exists.")
            elif "users_email_key" in str(e):
                raise ConflictException(detail=f"User with email '{user_data.email}' already exists.")
            else:
                logger.error(f"Database integrity error during user update for ID {user_id}: {e}", exc_info=True)
                raise DatabaseException(detail="Failed to update user due to a database integrity constraint.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating user ID {user_id}: {e}", exc_info=True)
            raise DatabaseException(detail=f"Failed to update user: {e}")

    async def delete(self, user_id: int) -> bool:
        """
        Deletes a user by their ID.
        Returns True if deleted, False if not found.
        """
        stmt = delete(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        if result.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent user with ID {user_id}.")
            return False
        logger.info(f"User ID {user_id} deleted.")
        return True