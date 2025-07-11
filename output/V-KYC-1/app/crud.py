import datetime
import logging
from typing import List, Optional, Type

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictException, NotFoundException
from app.models import Recording, RecordingStatus, User, UserRole
from app.schemas import (
    RecordingCreate,
    RecordingSearch,
    RecordingUpdate,
    UserCreate,
    UserUpdate,
)

logger = logging.getLogger(__name__)

# --- User CRUD Operations ---
def get_user(db: Session, user_id: int) -> Optional[User]:
    """Retrieve a user by their ID."""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Retrieve a user by their email address."""
    return db.query(User).filter(User.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Retrieve a list of users."""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate, hashed_password: str) -> User:
    """Create a new user in the database."""
    db_user = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role,
    )
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        logger.info(f"User created: {db_user.email} with role {db_user.role}")
        return db_user
    except IntegrityError:
        db.rollback()
        logger.error(f"Attempted to create user with existing email: {user.email}")
        raise ConflictException(f"User with email '{user.email}' already exists.")

def update_user(db: Session, user_id: int, user_update: UserUpdate) -> User:
    """Update an existing user's information."""
    db_user = get_user(db, user_id)
    if not db_user:
        raise NotFoundException(f"User with ID {user_id} not found.")

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    logger.info(f"User {user_id} updated.")
    return db_user

def delete_user(db: Session, user_id: int) -> User:
    """Delete a user from the database."""
    db_user = get_user(db, user_id)
    if not db_user:
        raise NotFoundException(f"User with ID {user_id} not found.")

    db.delete(db_user)
    db.commit()
    logger.info(f"User {user_id} deleted.")
    return db_user

# --- Recording CRUD Operations ---
def get_recording(db: Session, recording_id: int) -> Optional[Recording]:
    """Retrieve a recording by its ID."""
    return db.query(Recording).filter(Recording.id == recording_id).first()

def get_recordings(db: Session, skip: int = 0, limit: int = 100) -> List[Recording]:
    """Retrieve a list of all recordings."""
    return db.query(Recording).offset(skip).limit(limit).all()

def search_recordings(db: Session, search_params: RecordingSearch) -> List[Recording]:
    """Search recordings based on provided filters."""
    query = db.query(Recording)

    if search_params.lan_id:
        query = query.filter(Recording.lan_id.ilike(f"%{search_params.lan_id}%"))
    if search_params.status:
        query = query.filter(Recording.status == search_params.status)
    if search_params.uploader_id:
        query = query.filter(Recording.uploader_id == search_params.uploader_id)
    if search_params.start_date:
        query = query.filter(Recording.upload_date >= search_params.start_date)
    if search_params.end_date:
        # Add one day to include recordings from the end_date itself
        end_of_day = datetime.datetime.combine(search_params.end_date, datetime.time.max)
        query = query.filter(Recording.upload_date <= end_of_day)

    return query.offset(search_params.offset).limit(search_params.limit).all()

def create_recording(db: Session, recording: RecordingCreate, uploader_id: int) -> Recording:
    """Create a new recording entry in the database."""
    db_recording = Recording(
        lan_id=recording.lan_id,
        file_path=recording.file_path,
        file_name=recording.file_name,
        notes=recording.notes,
        uploader_id=uploader_id,
        upload_date=datetime.datetime.now(),
        status=RecordingStatus.PENDING # Default status
    )
    try:
        db.add(db_recording)
        db.commit()
        db.refresh(db_recording)
        logger.info(f"Recording created: ID {db_recording.id}, LAN ID {db_recording.lan_id}")
        return db_recording
    except IntegrityError:
        db.rollback()
        logger.error(f"Attempted to create recording with existing file path: {recording.file_path}")
        raise ConflictException(f"Recording with file path '{recording.file_path}' already exists.")

def update_recording(db: Session, recording_id: int, recording_update: RecordingUpdate, approver_id: Optional[int] = None) -> Recording:
    """Update an existing recording's information."""
    db_recording = get_recording(db, recording_id)
    if not db_recording:
        raise NotFoundException(f"Recording with ID {recording_id} not found.")

    update_data = recording_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_recording, key, value)

    # Handle approval status change
    if "status" in update_data and update_data["status"] == RecordingStatus.APPROVED:
        if approver_id:
            db_recording.approved_by_id = approver_id
            db_recording.approved_at = datetime.datetime.now()
        else:
            logger.warning(f"Recording {recording_id} approved without an approver_id.")

    db.add(db_recording)
    db.commit()
    db.refresh(db_recording)
    logger.info(f"Recording {recording_id} updated.")
    return db_recording

def delete_recording(db: Session, recording_id: int) -> Recording:
    """Delete a recording from the database."""
    db_recording = get_recording(db, recording_id)
    if not db_recording:
        raise NotFoundException(f"Recording with ID {recording_id} not found.")

    db.delete(db_recording)
    db.commit()
    logger.info(f"Recording {recording_id} deleted.")
    return db_recording