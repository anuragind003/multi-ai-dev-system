from sqlalchemy.orm import Session
from repositories import VKYCRecordingRepository, UserRepository
from schemas import VKYCRecordingCreate, VKYCRecordingUpdate, VKYCRecordingResponse, UserCreate, UserResponse
from exceptions import NotFoundException, ConflictException, BadRequestException, InternalServerError
from logger import logger
from models import VKYCRecording, UserRole

class VKYCRecordingService:
    """
    Service layer for VKYC Recording operations.
    Encapsulates business logic and orchestrates data access via the repository.
    """
    def __init__(self, db: Session):
        self.repository = VKYCRecordingRepository(db)

    def create_recording(self, recording_data: VKYCRecordingCreate) -> VKYCRecordingResponse:
        """
        Creates a new VKYC recording.
        Performs business logic validation (e.g., path validity, LAN ID uniqueness).
        """
        logger.info(f"Attempting to create VKYC recording for LAN ID: {recording_data.lan_id}")

        # Example business logic: Validate recording path format or existence (mocked)
        if not recording_data.recording_path.startswith("/mnt/vkyc_recordings/"):
            raise BadRequestException(detail="Recording path must be within the designated NFS mount.")

        # Check for existing LAN ID before attempting to create
        existing_recording = self.repository.get_by_lan_id(recording_data.lan_id)
        if existing_recording:
            raise ConflictException(detail=f"VKYC recording with LAN ID '{recording_data.lan_id}' already exists.")

        db_recording = self.repository.create(recording_data)
        return VKYCRecordingResponse.model_validate(db_recording)

    def get_recording_by_id(self, recording_id: int) -> VKYCRecordingResponse:
        """Retrieves a VKYC recording by ID."""
        logger.info(f"Attempting to retrieve VKYC recording by ID: {recording_id}")
        recording = self.repository.get_by_id(recording_id)
        if not recording:
            raise NotFoundException(detail=f"VKYC recording with ID '{recording_id}' not found.")
        return VKYCRecordingResponse.model_validate(recording)

    def get_all_recordings(self, skip: int = 0, limit: int = 100, lan_id_filter: str = None, status_filter: str = None) -> tuple[list[VKYCRecordingResponse], int]:
        """Retrieves all VKYC recordings with pagination and filters."""
        logger.info(f"Retrieving VKYC recordings: skip={skip}, limit={limit}, lan_id_filter={lan_id_filter}, status_filter={status_filter}")
        recordings, total_count = self.repository.get_all(skip, limit, lan_id_filter, status_filter)
        return [VKYCRecordingResponse.model_validate(rec) for rec in recordings], total_count

    def update_recording(self, recording_id: int, update_data: VKYCRecordingUpdate) -> VKYCRecordingResponse:
        """
        Updates an existing VKYC recording.
        Applies business rules for updates.
        """
        logger.info(f"Attempting to update VKYC recording with ID: {recording_id}")
        recording = self.repository.get_by_id(recording_id)
        if not recording:
            raise NotFoundException(detail=f"VKYC recording with ID '{recording_id}' not found.")

        # Example business logic: Prevent changing LAN ID if status is COMPLETED
        if recording.status == VKYCRecording.status.COMPLETED and update_data.lan_id is not None and update_data.lan_id != recording.lan_id:
            raise BadRequestException(detail="LAN ID cannot be changed for completed recordings.")

        # If LAN ID is being updated, check for conflict
        if update_data.lan_id and update_data.lan_id != recording.lan_id:
            existing_with_new_lan_id = self.repository.get_by_lan_id(update_data.lan_id)
            if existing_with_new_lan_id and existing_with_new_lan_id.id != recording_id:
                raise ConflictException(detail=f"Another recording with LAN ID '{update_data.lan_id}' already exists.")

        db_recording = self.repository.update(recording, update_data)
        return VKYCRecordingResponse.model_validate(db_recording)

    def delete_recording(self, recording_id: int):
        """
        Deletes a VKYC recording.
        Can implement soft delete here if `is_active` flag is used.
        """
        logger.info(f"Attempting to delete VKYC recording with ID: {recording_id}")
        recording = self.repository.get_by_id(recording_id)
        if not recording:
            raise NotFoundException(detail=f"VKYC recording with ID '{recording_id}' not found.")

        # Example business logic: Prevent deletion if status is PENDING (requires manual review)
        if recording.status == VKYCRecording.status.PENDING:
            raise BadRequestException(detail="Pending recordings cannot be deleted directly. Change status first.")

        # For soft delete:
        # update_data = VKYCRecordingUpdate(is_active=False)
        # self.repository.update(recording, update_data)
        # logger.info(f"Soft deleted VKYC recording with ID: {recording_id}")

        # For hard delete:
        self.repository.delete(recording)
        logger.info(f"Hard deleted VKYC recording with ID: {recording_id}")


class UserService:
    """
    Service layer for User operations.
    """
    def __init__(self, db: Session):
        self.repository = UserRepository(db)

    def create_user(self, user_data: UserCreate) -> UserResponse:
        """Creates a new user."""
        logger.info(f"Attempting to create user: {user_data.username}")
        existing_user = self.repository.get_user_by_username(user_data.username)
        if existing_user:
            raise ConflictException(detail=f"User with username '{user_data.username}' already exists.")
        
        db_user = self.repository.create_user(user_data)
        return UserResponse.model_validate(db_user)

    def get_user_by_username(self, username: str) -> UserResponse:
        """Retrieves a user by username."""
        user = self.repository.get_user_by_username(username)
        if not user:
            raise NotFoundException(detail=f"User '{username}' not found.")
        return UserResponse.model_validate(user)

    def get_user_by_id(self, user_id: int) -> UserResponse:
        """Retrieves a user by ID."""
        user = self.repository.get_user_by_id(user_id)
        if not user:
            raise NotFoundException(detail=f"User with ID '{user_id}' not found.")
        return UserResponse.model_validate(user)