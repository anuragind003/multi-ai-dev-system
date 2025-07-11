import logging
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_

from app.models.security_test import User, UserRole
from app.schemas.security_test import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.exceptions import NotFoundException, ConflictException, UnauthorizedException, BadRequestException

logger = logging.getLogger(__name__)

class UserService:
    """
    Service layer for User management.
    Handles business logic and interacts with the database.
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Fetches a user by their ID."""
        result = await self.db_session.execute(
            select(User).filter(User.id == user_id)
        )
        user = result.scalars().first()
        if not user:
            logger.warning(f"User with ID {user_id} not found.")
        return user

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Fetches a user by their username."""
        result = await self.db_session.execute(
            select(User).filter(User.username == username)
        )
        user = result.scalars().first()
        if not user:
            logger.warning(f"User with username '{username}' not found.")
        return user

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Fetches a user by their email."""
        result = await self.db_session.execute(
            select(User).filter(User.email == email)
        )
        user = result.scalars().first()
        if not user:
            logger.warning(f"User with email '{email}' not found.")
        return user

    async def create_user(self, user_data: UserCreate, current_user: Optional[User] = None) -> User:
        """
        Creates a new user.
        Only admins can create other admins or testers.
        """
        # Check for existing username or email
        existing_user = await self.db_session.execute(
            select(User).filter(or_(User.username == user_data.username, User.email == user_data.email))
        )
        if existing_user.scalars().first():
            raise ConflictException(detail="Username or email already registered.")

        # Role-based creation logic
        if user_data.role != UserRole.VIEWER and (not current_user or current_user.role != UserRole.ADMIN):
            raise ForbiddenException(detail="Only administrators can create users with 'admin' or 'tester' roles.")

        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            username=user_data.username,
            hashed_password=hashed_password,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=user_data.is_active
        )
        self.db_session.add(db_user)
        await self.db_session.commit()
        await self.db_session.refresh(db_user)
        logger.info(f"User '{db_user.username}' created successfully with role '{db_user.role.value}'.")
        return db_user

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticates a user by username and password.
        Returns the user object if credentials are valid, otherwise None.
        """
        user = await self.get_user_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed for username '{username}'. Invalid credentials.")
            return None
        if not user.is_active:
            logger.warning(f"Authentication failed for username '{username}'. User is inactive.")
            return None
        logger.info(f"User '{username}' authenticated successfully.")
        return user

    async def update_user(self, user_id: int, user_data: UserUpdate, current_user: User) -> User:
        """
        Updates an existing user's information.
        Admins can update any user. Non-admins can only update their own profile.
        """
        user_to_update = await self.get_user_by_id(user_id)
        if not user_to_update:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        # Authorization check
        if current_user.role != UserRole.ADMIN and current_user.id != user_id:
            raise ForbiddenException(detail="You are not authorized to update this user's profile.")

        # Prevent non-admins from changing roles or active status
        if current_user.role != UserRole.ADMIN:
            if user_data.role is not None and user_data.role != user_to_update.role:
                raise ForbiddenException(detail="You are not authorized to change user roles.")
            if user_data.is_active is not None and user_data.is_active != user_to_update.is_active:
                raise ForbiddenException(detail="You are not authorized to change user active status.")

        # Check for username/email conflict if they are being updated
        if user_data.username and user_data.username != user_to_update.username:
            existing_user = await self.get_user_by_username(user_data.username)
            if existing_user and existing_user.id != user_id:
                raise ConflictException(detail="Username already taken.")
        if user_data.email and user_data.email != user_to_update.email:
            existing_user = await self.get_user_by_email(user_data.email)
            if existing_user and existing_user.id != user_id:
                raise ConflictException(detail="Email already taken.")

        update_data = user_data.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for key, value in update_data.items():
            setattr(user_to_update, key, value)

        self.db_session.add(user_to_update)
        await self.db_session.commit()
        await self.db_session.refresh(user_to_update)
        logger.info(f"User with ID {user_id} updated successfully by user {current_user.username}.")
        return user_to_update

    async def delete_user(self, user_id: int, current_user: User) -> None:
        """
        Deletes a user. Only admins can delete users.
        Admins cannot delete themselves.
        """
        user_to_delete = await self.get_user_by_id(user_id)
        if not user_to_delete:
            raise NotFoundException(detail=f"User with ID {user_id} not found.")

        if current_user.role != UserRole.ADMIN:
            raise ForbiddenException(detail="Only administrators can delete users.")
        
        if current_user.id == user_id:
            raise BadRequestException(detail="Administrators cannot delete their own account.")

        await self.db_session.delete(user_to_delete)
        await self.db_session.commit()
        logger.info(f"User with ID {user_id} deleted successfully by user {current_user.username}.")

    async def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Fetches all users with pagination."""
        result = await self.db_session.execute(
            select(User).offset(skip).limit(limit)
        )
        return list(result.scalars().all())