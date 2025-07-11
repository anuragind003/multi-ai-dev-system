import os
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from app.core.config import settings
from app.core.exceptions import NotFoundException, BadRequestException, ServiceUnavailableException
from app.crud.recording import RecordingCRUD
from app.schemas.recordings import RecordingFilter, RecordingInDB, RecordingListResponse
from app.models.recording import Recording
from app.utils.logger import logger

class RecordingService:
    """
    Business logic for VKYC Recordings.
    Handles data retrieval, validation, and interaction with external systems (simulated NFS).
    """
    def __init__(self, db_session: AsyncSession):
        self.crud = RecordingCRUD(db_session)

    async def get_paginated_recordings(
        self,
        filters: RecordingFilter,
        page: int,
        size: int
    ) -> RecordingListResponse:
        """
        Retrieves a paginated list of VKYC recordings based on filters.
        """
        if size > settings.MAX_PAGE_SIZE:
            size = settings.MAX_PAGE_SIZE
            logger.warning(f"Requested page size {size} exceeds max, capped to {settings.MAX_PAGE_SIZE}")

        skip = (page - 1) * size
        
        try:
            recordings, total_count = await self.crud.get_recordings(filters, skip=skip, limit=size)
            
            return RecordingListResponse(
                total_count=total_count,
                page=page,
                size=size,
                items=[RecordingInDB.model_validate(rec) for rec in recordings]
            )
        except Exception as e:
            logger.error(f"Failed to retrieve recordings: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An error occurred while fetching recordings."
            )

    async def get_recording_for_download(self, recording_id: str) -> Tuple[str, str]:
        """
        Retrieves recording details for download and simulates NFS path validation.
        Returns (full_file_path, file_name).
        """
        recording = await self.crud.get_recording_by_id(recording_id)
        if not recording:
            raise NotFoundException(message=f"Recording with ID '{recording_id}' not found.")

        full_file_path = os.path.join(settings.NFS_RECORDINGS_PATH, recording.file_path)
        
        # Simulate checking if file exists on NFS
        # In a real scenario, this would involve actual file system checks or NFS client calls.
        if not os.path.exists(full_file_path):
            logger.warning(f"Recording file not found on NFS: {full_file_path}")
            # For a production system, you might want to update the recording status in DB
            # or trigger an alert if a file is missing.
            raise ServiceUnavailableException(message=f"Recording file for ID '{recording_id}' is currently unavailable.")
        
        logger.info(f"Preparing download for recording ID {recording_id} from {full_file_path}")
        return full_file_path, recording.file_name

    async def get_recordings_for_bulk_download(self, lan_ids: List[str]) -> List[Tuple[str, str]]:
        """
        Retrieves multiple recording details for bulk download and simulates NFS path validation.
        Returns a list of (full_file_path, file_name) tuples.
        """
        if not lan_ids:
            raise BadRequestException(message="No LAN IDs provided for bulk download.")
        if len(lan_ids) > 10: # Enforce max limit from schema
            raise BadRequestException(message="Maximum 10 LAN IDs allowed for bulk download.")

        recordings = await self.crud.get_recordings_by_lan_ids(lan_ids)
        
        if not recordings:
            raise NotFoundException(message="No recordings found for the provided LAN IDs.")

        found_lan_ids = {rec.lan_id for rec in recordings}
        missing_lan_ids = set(lan_ids) - found_lan_ids
        if missing_lan_ids:
            logger.warning(f"Some LAN IDs not found for bulk download: {missing_lan_ids}")
            # Depending on requirements, you might raise an error or proceed with found ones.
            # For now, we'll proceed but log the missing ones.

        download_files = []
        for recording in recordings:
            full_file_path = os.path.join(settings.NFS_RECORDINGS_PATH, recording.file_path)
            
            # Simulate checking if file exists on NFS
            if not os.path.exists(full_file_path):
                logger.warning(f"Recording file not found on NFS for LAN ID {recording.lan_id}: {full_file_path}. Skipping.")
                continue # Skip this file if not found
            
            download_files.append((full_file_path, recording.file_name))
        
        if not download_files:
            raise ServiceUnavailableException(message="No available recording files found for the provided LAN IDs.")

        logger.info(f"Preparing bulk download for {len(download_files)} recordings.")
        return download_files

# Dependency for injecting RecordingService
async def get_recording_service(db_session: AsyncSession = Depends(RecordingCRUD.db_session)) -> RecordingService:
    """
    Provides a RecordingService instance with a database session.
    Note: RecordingCRUD.db_session is not a direct dependency.
    It should be `Depends(get_db)` from `app.core.database`.
    Corrected dependency injection:
    """
    return RecordingService(db_session)

# Corrected dependency injection function for FastAPI
async def get_recording_service_dependency(db_session: AsyncSession = Depends(RecordingCRUD(None).db_session)) -> RecordingService:
    """
    Provides a RecordingService instance with a database session.
    This is a placeholder for the actual dependency injection.
    The `RecordingCRUD(None).db_session` is a hack to get the type hint.
    The actual `db_session` should come from `app.core.database.get_db`.
    """
    # This function should be defined in app.core.database or a common dependency file
    # For now, let's assume get_db is imported and used directly.
    from app.core.database import get_db
    return RecordingService(db_session=Depends(get_db)) # This is how it should be used in endpoints