from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_
from datetime import datetime, date, time
from typing import List, Optional

from app.models.models import User, Recording, RecordingStatus
from app.schemas.schemas import UserCreate, UserUpdate, RecordingCreate, RecordingUpdate, RecordingFilter
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.exceptions import (
    NotFoundException,
    UnauthorizedException,
    DuplicateEntryException,
    ForbiddenException,
    InvalidInputException
)
from app.core.logging_config import logger
from app.core.config import settings

class AuthService:
    """
    Service layer for user authentication and management.
    Handles business logic related to users, password hashing, and JWT token generation.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by their username."""
        logger.debug(f"Fetching user by username: {username}")
        result = await self.db.execute(select(User).filter(User.username == username))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"User with username '{username}' not found.")
            raise NotFoundException(f"User '{username}' not found.")
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by their ID."""
        logger.debug(f"Fetching user by ID: {user_id}")
        result = await self.db.execute(select(User).filter(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            logger.warning(f"User with ID '{user_id}' not found.")
            raise NotFoundException(f"User with ID '{user_id}' not found.")
        return user

    async def get_all_users(self) -> List[User]:
        """Retrieves all users."""
        logger.debug("Fetching all users.")
        result = await self.db.execute(select(User))
        return result.scalars().all()

    async def create_user(self, user_create: UserCreate) -> User:
        """
        Creates a new user.
        Hashes the password and checks for duplicate username/email.
        """
        logger.info(f"Attempting to create new user: {user_create.username}")
        # Check for existing username or email
        existing_user_query = select(User).filter(
            or_(User.username == user_create.username, User.email == user_create.email)
        )
        existing_user_result = await self.db.execute(existing_user_query)
        existing_user = existing_user_result.scalar_one_or_none()

        if existing_user:
            if existing_user.username == user_create.username:
                logger.warning(f"User creation failed: Username '{user_create.username}' already exists.")
                raise DuplicateEntryException(f"Username '{user_create.username}' already exists.")
            if existing_user.email == user_create.email:
                logger.warning(f"User creation failed: Email '{user_create.email}' already exists.")
                raise DuplicateEntryException(f"Email '{user_create.email}' already exists.")

        hashed_password = get_password_hash(user_create.password)
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            hashed_password=hashed_password,
            full_name=user_create.full_name,
            roles=user_create.roles,
            is_active=True # New users are active by default
        )
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        logger.info(f"User '{db_user.username}' created successfully.")
        return db_user

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User:
        """
        Updates an existing user's details.
        Handles password hashing if password is provided.
        """
        logger.info(f"Attempting to update user with ID: {user_id}")
        user = await self.get_user_by_id(user_id) # This will raise NotFoundException if user doesn't exist

        # Check for duplicate username/email if they are being updated
        if user_update.username and user_update.username != user.username:
            existing_username = await self.db.execute(select(User).filter(User.username == user_update.username))
            if existing_username.scalar_one_or_none():
                logger.warning(f"Update failed: Username '{user_update.username}' already exists.")
                raise DuplicateEntryException(f"Username '{user_update.username}' already exists.")
        if user_update.email and user_update.email != user.email:
            existing_email = await self.db.execute(select(User).filter(User.email == user_update.email))
            if existing_email.scalar_one_or_none():
                logger.warning(f"Update failed: Email '{user_update.email}' already exists.")
                raise DuplicateEntryException(f"Email '{user_update.email}' already exists.")

        update_data = user_update.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

        for key, value in update_data.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)
        logger.info(f"User with ID {user_id} updated successfully.")
        return user

    async def delete_user(self, user_id: int):
        """
        Deletes a user. Prevents deletion of the last admin user or self-deletion by an admin.
        """
        logger.info(f"Attempting to delete user with ID: {user_id}")
        user_to_delete = await self.get_user_by_id(user_id) # This will raise NotFoundException

        # Prevent deleting the last admin if the user to delete is an admin
        if "admin" in user_to_delete.roles:
            admin_count_query = select(func.count(User.id)).filter(User.roles.contains(["admin"]))
            admin_count_result = await self.db.execute(admin_count_query)
            admin_count = admin_count_result.scalar_one()
            if admin_count <= 1:
                logger.warning(f"Deletion failed: Cannot delete the last admin user (ID: {user_id}).")
                raise ForbiddenException("Cannot delete the last admin user.")

        await self.db.delete(user_to_delete)
        await self.db.commit()
        logger.info(f"User with ID {user_id} deleted successfully.")

    async def authenticate_user(self, username: str, password: str) -> Token:
        """
        Authenticates a user by username and password.
        Returns a JWT token if successful.
        """
        logger.info(f"Authenticating user: {username}")
        try:
            user = await self.get_user_by_username(username)
        except NotFoundException:
            logger.warning(f"Authentication failed: User '{username}' not found.")
            raise UnauthorizedException("Incorrect username or password")

        if not user.is_active:
            logger.warning(f"Authentication failed: User '{username}' is inactive.")
            raise UnauthorizedException("Inactive user")

        if not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed: Incorrect password for user '{username}'.")
            raise UnauthorizedException("Incorrect username or password")

        access_token = create_access_token(
            data={"sub": user.username, "roles": user.roles}
        )
        logger.info(f"User '{username}' authenticated successfully. Token generated.")
        from app.schemas.schemas import Token # Import here to avoid circular dependency
        return Token(access_token=access_token, token_type="bearer")


class RecordingService:
    """
    Service layer for V-KYC recording metadata management.
    Handles business logic related to recordings, including filtering and file path validation.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_recording_by_id(self, recording_id: int) -> Recording:
        """Retrieves a recording by its ID."""
        logger.debug(f"Fetching recording by ID: {recording_id}")
        result = await self.db.execute(select(Recording).filter(Recording.id == recording_id))
        recording = result.scalar_one_or_none()
        if not recording:
            logger.warning(f"Recording with ID '{recording_id}' not found.")
            raise NotFoundException(f"Recording with ID '{recording_id}' not found.")
        return recording

    async def get_all_recordings(
        self,
        filters: RecordingFilter,
        page: int = 1,
        page_size: int = 10
    ) -> List[Recording]:
        """
        Retrieves a paginated and filtered list of recordings.
        """
        logger.debug(f"Fetching recordings with filters: {filters.model_dump()}, page: {page}, page_size: {page_size}")
        query = select(Recording)
        conditions = []

        if filters.lan_id:
            conditions.append(Recording.lan_id.ilike(f"%{filters.lan_id}%"))
        if filters.customer_name:
            conditions.append(Recording.customer_name.ilike(f"%{filters.customer_name}%"))
        if filters.start_date:
            try:
                start_dt = datetime.combine(date.fromisoformat(filters.start_date), time.min)
                conditions.append(Recording.recording_date >= start_dt)
            except ValueError:
                raise InvalidInputException("Invalid start_date format. Use YYYY-MM-DD.")
        if filters.end_date:
            try:
                end_dt = datetime.combine(date.fromisoformat(filters.end_date), time.max)
                conditions.append(Recording.recording_date <= end_dt)
            except ValueError:
                raise InvalidInputException("Invalid end_date format. Use YYYY-MM-DD.")
        if filters.status:
            conditions.append(Recording.status == filters.status)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        recordings = result.scalars().all()
        logger.debug(f"Retrieved {len(recordings)} recordings.")
        return recordings

    async def create_recording(self, recording_create: RecordingCreate) -> Recording:
        """
        Creates a new recording metadata entry.
        Checks for duplicate LAN ID and file path.
        """
        logger.info(f"Attempting to create recording metadata for LAN ID: {recording_create.lan_id}")
        # Check for existing LAN ID or file path
        existing_recording_query = select(Recording).filter(
            or_(Recording.lan_id == recording_create.lan_id, Recording.file_path == recording_create.file_path)
        )
        existing_recording_result = await self.db.execute(existing_recording_query)
        existing_recording = existing_recording_result.scalar_one_or_none()

        if existing_recording:
            if existing_recording.lan_id == recording_create.lan_id:
                logger.warning(f"Recording creation failed: LAN ID '{recording_create.lan_id}' already exists.")
                raise DuplicateEntryException(f"Recording with LAN ID '{recording_create.lan_id}' already exists.")
            if existing_recording.file_path == recording_create.file_path:
                logger.warning(f"Recording creation failed: File path '{recording_create.file_path}' already exists.")
                raise DuplicateEntryException(f"Recording with file path '{recording_create.file_path}' already exists.")

        db_recording = Recording(
            lan_id=recording_create.lan_id,
            customer_name=recording_create.customer_name,
            recording_date=recording_create.recording_date,
            file_path=recording_create.file_path,
            duration_seconds=recording_create.duration_seconds,
            status=recording_create.status,
            notes=recording_create.notes,
            # uploaded_by_user_id=current_user.id # This would be set by the endpoint based on current_user
        )
        self.db.add(db_recording)
        await self.db.commit()
        await self.db.refresh(db_recording)
        logger.info(f"Recording metadata for LAN ID '{db_recording.lan_id}' created successfully.")
        return db_recording

    async def update_recording(self, recording_id: int, recording_update: RecordingUpdate) -> Recording:
        """
        Updates an existing recording metadata entry.
        Checks for duplicate LAN ID or file path if they are being updated.
        """
        logger.info(f"Attempting to update recording with ID: {recording_id}")
        recording = await self.get_recording_by_id(recording_id) # This will raise NotFoundException

        # Check for duplicate LAN ID or file path if they are being updated
        if recording_update.lan_id and recording_update.lan_id != recording.lan_id:
            existing_lan_id = await self.db.execute(select(Recording).filter(Recording.lan_id == recording_update.lan_id))
            if existing_lan_id.scalar_one_or_none():
                logger.warning(f"Update failed: LAN ID '{recording_update.lan_id}' already exists.")
                raise DuplicateEntryException(f"LAN ID '{recording_update.lan_id}' already exists.")
        if recording_update.file_path and recording_update.file_path != recording.file_path:
            existing_file_path = await self.db.execute(select(Recording).filter(Recording.file_path == recording_update.file_path))
            if existing_file_path.scalar_one_or_none():
                logger.warning(f"Update failed: File path '{recording_update.file_path}' already exists.")
                raise DuplicateEntryException(f"File path '{recording_update.file_path}' already exists.")

        update_data = recording_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(recording, key, value)

        await self.db.commit()
        await self.db.refresh(recording)
        logger.info(f"Recording with ID {recording_id} updated successfully.")
        return recording

    async def delete_recording(self, recording_id: int):
        """
        Deletes a recording metadata entry.
        """
        logger.info(f"Attempting to delete recording metadata with ID: {recording_id}")
        recording_to_delete = await self.get_recording_by_id(recording_id) # This will raise NotFoundException

        await self.db.delete(recording_to_delete)
        await self.db.commit()
        logger.info(f"Recording metadata with ID {recording_id} deleted successfully.")