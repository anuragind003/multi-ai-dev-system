from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_
from typing import List, Optional, Tuple
from datetime import datetime

from models import Recording, RecordingStatus
from schemas import RecordingCreate, RecordingUpdate, RecordingSearch
from core.exceptions import CustomHTTPException
from core.logging_config import setup_logging
from config import settings
import os

logger = setup_logging()

class RecordingService:
    """
    Service layer for managing V-KYC recordings.
    Handles CRUD operations, search, filter, and interaction with NFS (simulated).
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recording(self, recording_data: RecordingCreate, uploaded_by_user_id: int) -> Recording:
        """
        Creates a new V-KYC recording entry in the database.
        Simulates checking file existence on NFS.
        """
        logger.info(f"Attempting to create recording for LAN ID: {recording_data.lan_id}")

        # Simulate NFS file existence check
        full_nfs_path = os.path.join(settings.NFS_BASE_PATH, recording_data.file_path.lstrip('/'))
        # In a real scenario, you'd use os.path.exists or a more robust NFS client library
        # For this example, we'll assume the file path is valid or will be valid.
        # if not os.path.exists(full_nfs_path):
        #     logger.warning(f"File path does not exist on NFS: {full_nfs_path}")
        #     raise CustomHTTPException(
        #         status_code=400,
        #         detail=f"Recording file not found at specified path: {recording_data.file_path}",
        #         code="FILE_NOT_FOUND"
        #     )

        # Check for duplicate file_path
        existing_recording = await self.db.execute(
            select(Recording).filter(Recording.file_path == recording_data.file_path)
        )
        if existing_recording.scalars().first():
            logger.warning(f"Recording creation failed: Duplicate file path {recording_data.file_path}")
            raise CustomHTTPException(
                status_code=409,
                detail="A recording with this file path already exists.",
                code="DUPLICATE_FILE_PATH"
            )

        db_recording = Recording(
            **recording_data.model_dump(),
            uploaded_by=uploaded_by_user_id,
            status=RecordingStatus.PENDING_REVIEW # Default status on creation
        )
        self.db.add(db_recording)
        await self.db.commit()
        await self.db.refresh(db_recording)
        logger.info(f"Recording '{db_recording.id}' created successfully for LAN ID: {db_recording.lan_id}")
        return db_recording

    async def get_recording_by_id(self, recording_id: int) -> Optional[Recording]:
        """Fetches a recording by its ID."""
        result = await self.db.execute(select(Recording).filter(Recording.id == recording_id))
        return result.scalars().first()

    async def get_all_recordings(self, skip: int = 0, limit: int = 100) -> Tuple[List[Recording], int]:
        """Fetches all recordings with pagination."""
        logger.debug(f"Fetching all recordings, skip={skip}, limit={limit}")
        total_count_result = await self.db.execute(select(func.count(Recording.id)))
        total_count = total_count_result.scalar_one()

        result = await self.db.execute(
            select(Recording).offset(skip).limit(limit).order_by(Recording.uploaded_at.desc())
        )
        recordings = result.scalars().all()
        logger.debug(f"Fetched {len(recordings)} recordings out of {total_count}.")
        return recordings, total_count

    async def search_recordings(
        self,
        search_params: RecordingSearch,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Recording], int]:
        """
        Searches and filters recordings based on provided criteria.
        """
        logger.info(f"Searching recordings with params: {search_params.model_dump()}")
        query = select(Recording)
        count_query = select(func.count(Recording.id))
        filters = []

        if search_params.lan_id:
            filters.append(Recording.lan_id.ilike(f"%{search_params.lan_id}%"))
        if search_params.customer_name:
            filters.append(Recording.customer_name.ilike(f"%{search_params.customer_name}%"))
        if search_params.status:
            filters.append(Recording.status == search_params.status)
        if search_params.start_date:
            filters.append(Recording.recording_date >= search_params.start_date)
        if search_params.end_date:
            # Add one day to end_date to include recordings on the end_date itself
            end_of_day = search_params.end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            filters.append(Recording.recording_date <= end_of_day)
        if search_params.uploaded_by:
            filters.append(Recording.uploaded_by == search_params.uploaded_by)

        if filters:
            query = query.filter(and_(*filters))
            count_query = count_query.filter(and_(*filters))

        total_count_result = await self.db.execute(count_query)
        total_count = total_count_result.scalar_one()

        result = await self.db.execute(
            query.offset(skip).limit(limit).order_by(Recording.recording_date.desc())
        )
        recordings = result.scalars().all()
        logger.info(f"Found {len(recordings)} recordings matching search criteria out of {total_count}.")
        return recordings, total_count

    async def update_recording(self, recording_id: int, update_data: RecordingUpdate) -> Recording:
        """
        Updates an existing recording.
        Raises CustomHTTPException if recording not found or duplicate file_path.
        """
        logger.info(f"Attempting to update recording ID: {recording_id}")
        db_recording = await self.get_recording_by_id(recording_id)
        if not db_recording:
            logger.warning(f"Update failed: Recording ID {recording_id} not found.")
            raise CustomHTTPException(
                status_code=404,
                detail="Recording not found.",
                code="RECORDING_NOT_FOUND"
            )

        update_dict = update_data.model_dump(exclude_unset=True)

        if 'file_path' in update_dict and update_dict['file_path'] != db_recording.file_path:
            # Check for duplicate file_path if it's being updated
            existing_with_new_path = await self.db.execute(
                select(Recording).filter(Recording.file_path == update_dict['file_path'], Recording.id != recording_id)
            )
            if existing_with_new_path.scalars().first():
                logger.warning(f"Update failed: Duplicate file path {update_dict['file_path']} for another recording.")
                raise CustomHTTPException(
                    status_code=409,
                    detail="A recording with this file path already exists.",
                    code="DUPLICATE_FILE_PATH"
                )
            # Simulate NFS file existence check for new path
            # full_nfs_path = os.path.join(settings.NFS_BASE_PATH, update_dict['file_path'].lstrip('/'))
            # if not os.path.exists(full_nfs_path):
            #     logger.warning(f"New file path does not exist on NFS: {full_nfs_path}")
            #     raise CustomHTTPException(
            #         status_code=400,
            #         detail=f"New recording file not found at specified path: {update_dict['file_path']}",
            #         code="FILE_NOT_FOUND"
            #     )

        for key, value in update_dict.items():
            setattr(db_recording, key, value)

        db_recording.last_modified_at = datetime.now() # Explicitly update timestamp
        await self.db.commit()
        await self.db.refresh(db_recording)
        logger.info(f"Recording ID {recording_id} updated successfully.")
        return db_recording

    async def delete_recording(self, recording_id: int):
        """
        Deletes a recording from the database.
        Raises CustomHTTPException if recording not found.
        """
        logger.info(f"Attempting to delete recording ID: {recording_id}")
        db_recording = await self.get_recording_by_id(recording_id)
        if not db_recording:
            logger.warning(f"Deletion failed: Recording ID {recording_id} not found.")
            raise CustomHTTPException(
                status_code=404,
                detail="Recording not found.",
                code="RECORDING_NOT_FOUND"
            )
        await self.db.delete(db_recording)
        await self.db.commit()
        logger.info(f"Recording ID {recording_id} deleted successfully.")

    async def get_recording_file(self, recording_id: int) -> str:
        """
        Retrieves the full NFS path for a recording.
        In a real application, this would involve streaming the file.
        """
        logger.info(f"Attempting to retrieve file path for recording ID: {recording_id}")
        db_recording = await self.get_recording_by_id(recording_id)
        if not db_recording:
            logger.warning(f"File retrieval failed: Recording ID {recording_id} not found.")
            raise CustomHTTPException(
                status_code=404,
                detail="Recording not found.",
                code="RECORDING_NOT_FOUND"
            )
        
        full_nfs_path = os.path.join(settings.NFS_BASE_PATH, db_recording.file_path.lstrip('/'))
        # In a real scenario, you'd check if the file actually exists on NFS before returning the path
        # if not os.path.exists(full_nfs_path):
        #     logger.error(f"Actual file not found on NFS for recording ID {recording_id} at {full_nfs_path}")
        #     raise CustomHTTPException(
        #         status_code=500,
        #         detail="Recording file not accessible on server.",
        #         code="FILE_NOT_ACCESSIBLE"
        #     )
        logger.info(f"Retrieved file path for recording ID {recording_id}: {full_nfs_path}")
        return full_nfs_path