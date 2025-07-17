from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from models import Recording
from schemas import RecordingCreate, RecordingSearch, RecordingResponse
from exceptions import RecordingNotFoundError, InvalidInputError
from logger import logger
from nfs_service import NFSManager

class RecordingService:
    """
    Service layer for managing VKYC recording metadata in the database
    and orchestrating interactions with the NFS service.
    """
    def __init__(self, db: Session, nfs_manager: NFSManager):
        self.db = db
        self.nfs_manager = nfs_manager

    def create_recording(self, recording_in: RecordingCreate) -> Recording:
        """
        Creates a new recording metadata entry in the database.
        Performs validation against NFS existence before creation.
        """
        if self.db.query(Recording).filter(Recording.lan_id == recording_in.lan_id).first():
            raise InvalidInputError(f"Recording with LAN ID '{recording_in.lan_id}' already exists.")

        # Validate file existence and size on NFS before creating DB entry
        try:
            if not self.nfs_manager.check_file_exists(recording_in.file_path_on_nfs):
                raise InvalidInputError(f"File '{recording_in.file_path_on_nfs}' not found on NFS. Cannot create recording metadata.")
            actual_size = self.nfs_manager.get_file_size(recording_in.file_path_on_nfs)
            if actual_size != recording_in.size_bytes:
                logger.warning(f"Mismatch in reported size for {recording_in.file_path_on_nfs}. DB: {recording_in.size_bytes}, NFS: {actual_size}")
                # Optionally, update recording_in.size_bytes = actual_size or raise error
                # For now, we'll proceed but log a warning.
        except Exception as e:
            logger.error(f"NFS validation failed for {recording_in.file_path_on_nfs}: {e}")
            raise InvalidInputError(f"NFS validation failed for file path: {e}")

        db_recording = Recording(**recording_in.model_dump())
        self.db.add(db_recording)
        self.db.commit()
        self.db.refresh(db_recording)
        logger.info(f"Created recording metadata for LAN ID: {db_recording.lan_id}")
        return db_recording

    def get_recording_by_lan_id(self, lan_id: str) -> Recording:
        """Retrieves a recording by its LAN ID."""
        recording = self.db.query(Recording).filter(Recording.lan_id == lan_id).first()
        if not recording:
            raise RecordingNotFoundError(f"Recording with LAN ID '{lan_id}' not found.")
        return recording

    def get_recording_by_id(self, recording_id: int) -> Recording:
        """Retrieves a recording by its primary key ID."""
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            raise RecordingNotFoundError(f"Recording with ID '{recording_id}' not found.")
        return recording

    def search_recordings(
        self,
        search_params: RecordingSearch,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Recording], int]:
        """
        Searches and filters recordings based on provided criteria.
        Returns a list of recordings and the total count.
        """
        query = select(Recording)

        if search_params.lan_id:
            query = query.filter(Recording.lan_id.ilike(f"%{search_params.lan_id}%"))
        if search_params.start_date:
            query = query.filter(Recording.recorded_at >= search_params.start_date)
        if search_params.end_date:
            query = query.filter(Recording.recorded_at <= search_params.end_date)
        if search_params.min_size_bytes is not None:
            query = query.filter(Recording.size_bytes >= search_params.min_size_bytes)
        if search_params.max_size_bytes is not None:
            query = query.filter(Recording.size_bytes <= search_params.max_size_bytes)
        if search_params.is_active is not None:
            query = query.filter(Recording.is_active == search_params.is_active)

        # Get total count before applying limit/offset
        total_count = self.db.scalar(select(func.count()).select_from(query.subquery()))

        # Apply ordering, offset, and limit
        query = query.order_by(Recording.recorded_at.desc()).offset(skip).limit(limit)
        
        recordings = self.db.scalars(query).all()
        logger.info(f"Found {len(recordings)} recordings (total: {total_count}) for search params: {search_params.model_dump()}")
        return recordings, total_count

    def update_recording_status(self, lan_id: str, is_active: bool) -> Recording:
        """Updates the active status of a recording."""
        recording = self.get_recording_by_lan_id(lan_id)
        recording.is_active = is_active
        self.db.commit()
        self.db.refresh(recording)
        logger.info(f"Updated recording {lan_id} active status to {is_active}")
        return recording