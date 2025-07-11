from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
import logging

from models.user import User
from schemas.user import UserCreate, UserUpdate
from exceptions import NotFoundException, ConflictException

logger = logging.getLogger(__name__)

class UserRepository:
    """
    Repository class for User model, handling all database CRUD operations.
    Abstracts database interactions from the service layer.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create_user(self, user_data: UserCreate, hashed_password: str) -> User:
        """
        Creates a new user in the database.
        Raises ConflictException if a user with the given email already exists.
        """
        try:
            new_user = User(
                email=user_data.email,
                hashed_password=hashed_password,
                full_name=user_data.full_name,
                is_superuser=user_data.is_superuser
            )
            self.db_session.add(new_user)
            await self.db_session.commit()
            await self.db_session.refresh(new_user)
            logger.info(f"User created: {new_user.email}")
            return new_user
        except IntegrityError:
            await self.db_session.rollback()
            logger.warning(f"Attempted to create user with existing email: {user_data.email}")
            raise ConflictException(detail=f"User with email '{user_data.email}' already exists.")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error creating user {user_data.email}: {e}", exc_info=True)
            raise

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieves a user by their email address."""
        result = await self.db_session.execute(
            select(User).filter(User.email == email)
        )
        user = result.scalars().first()
        logger.debug(f"Retrieved user by email {email}: {'found' if user else 'not found'}")
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        result = await self.db_session.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalars().first()
        logger.debug(f"Retrieved user by ID {user_id}: {'found' if user else 'not found'}")
        return user

    async def get_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Retrieves a list of users with pagination."""
        result = await self.db_session.execute(
            select(User).offset(skip).limit(limit)
        )
        users = result.scalars().all()
        logger.debug(f"Retrieved {len(users)} users (skip={skip}, limit={limit})")
        return list(users)

    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """
        Updates an existing user's information.
        Raises NotFoundException if the user does not exist.
        Raises ConflictException if the new email already exists for another user.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            logger.warning(f"Attempted to update non-existent user with ID: {user_id}")
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        update_data = user_data.model_dump(exclude_unset=True)
        
        # Handle email change specifically to catch IntegrityError
        if 'email' in update_data and update_data['email'] != user.email:
            existing_user_with_new_email = await self.get_user_by_email(update_data['email'])
            if existing_user_with_new_email and existing_user_with_new_email.id != user_id:
                raise ConflictException(detail=f"Email '{update_data['email']}' is already taken by another user.")

        try:
            stmt = update(User).where(User.id == user_id).values(**update_data)
            await self.db_session.execute(stmt)
            await self.db_session.commit()
            await self.db_session.refresh(user) # Refresh the user object to reflect changes
            logger.info(f"User with ID {user_id} updated.")
            return user
        except IntegrityError:
            await self.db_session.rollback()
            logger.warning(f"Integrity error during update for user ID {user_id}", exc_info=True)
            raise ConflictException(detail="A unique constraint was violated during update. Check email or other unique fields.")
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error updating user ID {user_id}: {e}", exc_info=True)
            raise

    async def delete_user(self, user_id: int) -> bool:
        """
        Deletes a user from the database.
        Returns True if the user was deleted, False otherwise.
        """
        stmt = delete(User).where(User.id == user_id)
        result = await self.db_session.execute(stmt)
        await self.db_session.commit()
        if result.rowcount == 0:
            logger.warning(f"Attempted to delete non-existent user with ID: {user_id}")
            raise NotFoundException(detail=f"User with ID {user_id} not found.")
        logger.info(f"User with ID {user_id} deleted.")
        return True