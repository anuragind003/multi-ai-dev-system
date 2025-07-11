from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional
import logging

from app.models import User, Recording
from app.schemas import UserCreate, RecordingCreate

logger = logging.getLogger(__name__)

class CRUDUser:
    """
    CRUD operations for User model.
    """
    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        """Retrieve a user by their email address."""
        try:
            return db.query(User).filter(User.email == email).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching user by email {email}: {e}")
            raise

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        """Retrieve a user by their ID."""
        try:
            return db.query(User).filter(User.id == user_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching user by ID {user_id}: {e}")
            raise

    def create_user(self, db: Session, user: UserCreate, hashed_password: str) -> User:
        """Create a new user in the database."""
        db_user = User(
            email=user.email,
            hashed_password=hashed_password,
            full_name=user.full_name,
            is_active=True,
            is_superuser=False # Default to non-superuser
        )
        try:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"User created: {db_user.email}")
            return db_user
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating user {user.email}: {e}")
            raise

class CRUDRecording:
    """
    CRUD operations for Recording model.
    """
    def get_recording(self, db: Session, recording_id: int) -> Optional[Recording]:
        """Retrieve a single recording by its ID."""
        try:
            return db.query(Recording).filter(Recording.id == recording_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching recording by ID {recording_id}: {e}")
            raise

    def get_recording_by_lan_id(self, db: Session, lan_id: str) -> Optional[Recording]:
        """Retrieve a single recording by its LAN ID."""
        try:
            return db.query(Recording).filter(Recording.lan_id == lan_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching recording by LAN ID {lan_id}: {e}")
            raise

    def get_recordings(self, db: Session, skip: int = 0, limit: int = 100) -> List[Recording]:
        """Retrieve a list of recordings with pagination."""
        try:
            return db.query(Recording).offset(skip).limit(limit).all()
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching recordings (skip={skip}, limit={limit}): {e}")
            raise

    def create_recording(self, db: Session, recording: RecordingCreate) -> Recording:
        """Create a new recording entry in the database."""
        db_recording = Recording(
            lan_id=recording.lan_id,
            file_path=recording.file_path,
            file_name=recording.file_name,
            duration_seconds=recording.duration_seconds,
            size_bytes=recording.size_bytes,
            status=recording.status,
            metadata_json=recording.metadata_json
        )
        try:
            db.add(db_recording)
            db.commit()
            db.refresh(db_recording)
            logger.info(f"Recording created: LAN ID {db_recording.lan_id}")
            return db_recording
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Database error creating recording {recording.lan_id}: {e}")
            raise

# Instantiate CRUD classes for dependency injection
crud_user = CRUDUser()
crud_recording = CRUDRecording()