from sqlalchemy.orm import Session
from typing import Optional, List
import logging
import os
import json

from app.crud import crud_user, crud_recording
from app.schemas import UserCreate, UserResponse, RecordingCreate, RecordingResponse
from app.models import User, Recording
from app.core.security import verify_password, get_password_hash
from app.core.exceptions import NotFoundException, ConflictException, UnauthorizedException, ServiceUnavailableException
from app.config import settings

logger = logging.getLogger(__name__)

class UserService:
    """
    Business logic for User operations.
    """
    def create_user(self, db: Session, user_in: UserCreate) -> UserResponse:
        """
        Creates a new user.
        Raises ConflictException if user with email already exists.
        """
        existing_user = crud_user.get_user_by_email(db, email=user_in.email)
        if existing_user:
            logger.warning(f"Attempted to create user with existing email: {user_in.email}")
            raise ConflictException(f"User with email '{user_in.email}' already exists.")

        hashed_password = get_password_hash(user_in.password)
        user = crud_user.create_user(db, user_in, hashed_password)
        return UserResponse.model_validate(user)

    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """
        Authenticates a user by email and password.
        Returns the user object if credentials are valid, otherwise None.
        """
        user = crud_user.get_user_by_email(db, email)
        if not user or not verify_password(password, user.hashed_password):
            logger.warning(f"Authentication failed for user: {email}")
            return None
        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {email}")
            return None
        logger.info(f"User authenticated: {email}")
        return user

    def get_user_by_email(self, db: Session, email: str) -> Optional[UserResponse]:
        """Retrieves a user by email."""
        user = crud_user.get_user_by_email(db, email)
        if not user:
            return None
        return UserResponse.model_validate(user)

class RecordingService:
    """
    Business logic for Recording operations.
    Handles fetching recording details and validating file existence.
    """
    def get_recording_details(self, db: Session, recording_id: int) -> RecordingResponse:
        """
        Retrieves details for a single recording by ID.
        Validates if the associated file exists on the NFS mount point.
        Raises NotFoundException if recording not found.
        Raises ServiceUnavailableException if file path is invalid or file not found on NFS.
        """
        recording = crud_recording.get_recording(db, recording_id)
        if not recording:
            logger.warning(f"Recording with ID {recording_id} not found.")
            raise NotFoundException(f"Recording with ID {recording_id} not found.")

        full_file_path = os.path.join(settings.NFS_MOUNT_POINT, recording.file_path.lstrip('/'))
        
        # Basic path sanitization to prevent directory traversal
        if not os.path.abspath(full_file_path).startswith(os.path.abspath(settings.NFS_MOUNT_POINT)):
            logger.error(f"Attempted directory traversal detected for recording ID {recording_id}: {full_file_path}")
            raise ServiceUnavailableException("Invalid file path detected.")

        if not os.path.exists(full_file_path):
            logger.error(f"Recording file not found on NFS for ID {recording_id} at path: {full_file_path}")
            # Optionally update recording status in DB to 'missing' or 'corrupted'
            raise ServiceUnavailableException(f"Recording file for ID {recording_id} not found or accessible.")
        
        if not os.path.isfile(full_file_path):
            logger.error(f"Path for recording ID {recording_id} is not a file: {full_file_path}")
            raise ServiceUnavailableException(f"Recording path for ID {recording_id} is not a file.")

        logger.info(f"Successfully retrieved details for recording ID {recording_id}.")
        return RecordingResponse.model_validate(recording)

    def create_recording(self, db: Session, recording_in: RecordingCreate) -> RecordingResponse:
        """
        Creates a new recording entry.
        Raises ConflictException if recording with LAN ID already exists.
        """
        existing_recording = crud_recording.get_recording_by_lan_id(db, lan_id=recording_in.lan_id)
        if existing_recording:
            logger.warning(f"Attempted to create recording with existing LAN ID: {recording_in.lan_id}")
            raise ConflictException(f"Recording with LAN ID '{recording_in.lan_id}' already exists.")
        
        recording = crud_recording.create_recording(db, recording_in)
        return RecordingResponse.model_validate(recording)

    def get_all_recordings(self, db: Session, skip: int = 0, limit: int = 100) -> List[RecordingResponse]:
        """Retrieves a list of all recordings."""
        recordings = crud_recording.get_recordings(db, skip=skip, limit=limit)
        return [RecordingResponse.model_validate(rec) for rec in recordings]

# Instantiate service classes for dependency injection
user_service = UserService()
recording_service = RecordingService()