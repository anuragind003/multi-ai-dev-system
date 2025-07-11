from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models import VKYCRecording, User
from schemas import VKYCRecordingCreate, VKYCRecordingUpdate, UserCreate
from exceptions import ConflictException, NotFoundException, InternalServerError
from logger import logger
from auth import get_password_hash

class VKYCRecordingRepository:
    """
    Repository class for VKYCRecording model.
    Handles direct database interactions for VKYC recordings.
    """
    def __init__(self, db: Session):
        self.db = db

    def create(self, recording_data: VKYCRecordingCreate) -> VKYCRecording:
        """
        Creates a new VKYC recording in the database.
        Raises ConflictException if a recording with the same LAN ID already exists.
        """
        try:
            db_recording = VKYCRecording(**recording_data.model_dump())
            self.db.add(db_recording)
            self.db.commit()
            self.db.refresh(db_recording)
            logger.info(f"Created VKYC recording with LAN ID: {db_recording.lan_id}")
            return db_recording
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error creating VKYC recording for LAN ID {recording_data.lan_id}: {e}")
            if "duplicate key value violates unique constraint" in str(e):
                raise ConflictException(detail=f"VKYC recording with LAN ID '{recording_data.lan_id}' already exists.")
            raise InternalServerError(detail="Database integrity error during creation.")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating VKYC recording: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to create VKYC recording due to a database error.")

    def get_by_id(self, recording_id: int) -> Optional[VKYCRecording]:
        """Retrieves a VKYC recording by its ID."""
        try:
            recording = self.db.query(VKYCRecording).filter(VKYCRecording.id == recording_id).first()
            logger.debug(f"Retrieved VKYC recording by ID {recording_id}: {recording is not None}")
            return recording
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving VKYC recording by ID {recording_id}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to retrieve VKYC recording due to a database error.")

    def get_by_lan_id(self, lan_id: str) -> Optional[VKYCRecording]:
        """Retrieves a VKYC recording by its LAN ID."""
        try:
            recording = self.db.query(VKYCRecording).filter(VKYCRecording.lan_id == lan_id).first()
            logger.debug(f"Retrieved VKYC recording by LAN ID {lan_id}: {recording is not None}")
            return recording
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving VKYC recording by LAN ID {lan_id}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to retrieve VKYC recording due to a database error.")

    def get_all(self, skip: int = 0, limit: int = 100, lan_id_filter: Optional[str] = None, status_filter: Optional[str] = None) -> tuple[list[VKYCRecording], int]:
        """
        Retrieves all VKYC recordings with pagination and optional filters.
        Returns a tuple of (list of recordings, total count).
        """
        try:
            query = self.db.query(VKYCRecording)
            if lan_id_filter:
                query = query.filter(VKYCRecording.lan_id.ilike(f"%{lan_id_filter}%"))
            if status_filter:
                query = query.filter(VKYCRecording.status == status_filter)

            total_count = query.count()
            recordings = query.offset(skip).limit(limit).all()
            logger.debug(f"Retrieved {len(recordings)} VKYC recordings (total: {total_count}) with skip={skip}, limit={limit}")
            return recordings, total_count
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all VKYC recordings: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to retrieve VKYC recordings due to a database error.")

    def update(self, recording: VKYCRecording, update_data: VKYCRecordingUpdate) -> VKYCRecording:
        """
        Updates an existing VKYC recording.
        Raises ConflictException if the updated LAN ID conflicts with an existing one.
        """
        try:
            for key, value in update_data.model_dump(exclude_unset=True).items():
                setattr(recording, key, value)
            self.db.add(recording)
            self.db.commit()
            self.db.refresh(recording)
            logger.info(f"Updated VKYC recording with ID: {recording.id}")
            return recording
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error updating VKYC recording ID {recording.id}: {e}")
            if "duplicate key value violates unique constraint" in str(e) and update_data.lan_id:
                raise ConflictException(detail=f"VKYC recording with LAN ID '{update_data.lan_id}' already exists.")
            raise InternalServerError(detail="Database integrity error during update.")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error updating VKYC recording ID {recording.id}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to update VKYC recording due to a database error.")

    def delete(self, recording: VKYCRecording):
        """Deletes a VKYC recording from the database."""
        try:
            self.db.delete(recording)
            self.db.commit()
            logger.info(f"Deleted VKYC recording with ID: {recording.id}")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error deleting VKYC recording ID {recording.id}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to delete VKYC recording due to a database error.")

class UserRepository:
    """
    Repository class for User model.
    Handles direct database interactions for users.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: UserCreate) -> User:
        """
        Creates a new user in the database.
        Hashes the password before storing.
        Raises ConflictException if username or email already exists.
        """
        try:
            hashed_password = get_password_hash(user_data.password)
            db_user = User(
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                role=user_data.role,
                hashed_password=hashed_password
            )
            self.db.add(db_user)
            self.db.commit()
            self.db.refresh(db_user)
            logger.info(f"Created user: {db_user.username}")
            return db_user
        except IntegrityError as e:
            self.db.rollback()
            logger.warning(f"Integrity error creating user {user_data.username}: {e}")
            if "duplicate key value violates unique constraint" in str(e):
                if "username" in str(e):
                    raise ConflictException(detail=f"User with username '{user_data.username}' already exists.")
                if "email" in str(e):
                    raise ConflictException(detail=f"User with email '{user_data.email}' already exists.")
            raise InternalServerError(detail="Database integrity error during user creation.")
        except SQLAlchemyError as e:
            self.db.rollback()
            logger.error(f"Database error creating user: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to create user due to a database error.")

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Retrieves a user by username."""
        try:
            user = self.db.query(User).filter(User.username == username).first()
            logger.debug(f"Retrieved user by username {username}: {user is not None}")
            return user
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user by username {username}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to retrieve user due to a database error.")

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieves a user by ID."""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            logger.debug(f"Retrieved user by ID {user_id}: {user is not None}")
            return user
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving user by ID {user_id}: {e}", exc_info=True)
            raise InternalServerError(detail="Failed to retrieve user due to a database error.")