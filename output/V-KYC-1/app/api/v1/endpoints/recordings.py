from fastapi import APIRouter, Depends, status, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import os

from app.schemas.schemas import RecordingCreate, RecordingResponse, RecordingUpdate, RecordingFilter
from app.services.services import RecordingService
from app.api.v1.dependencies.common import get_db_session, get_recording_service, get_current_user, get_current_admin_user
from app.models.models import User
from app.core.exceptions import NotFoundException, DuplicateEntryException, FileOperationException, ForbiddenException
from app.core.logging_config import logger
from app.core.config import settings

router = APIRouter()

@router.post("/recordings/", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED, summary="Create a new recording metadata entry (Admin only)")
async def create_recording(
    recording_create: RecordingCreate,
    recording_service: RecordingService = Depends(get_recording_service),
    current_admin: User = Depends(get_current_admin_user) # Only admins can create
):
    """
    Creates a new metadata entry for a V-KYC recording.
    This endpoint does not upload the file itself, but registers its details.
    Requires 'admin' role.
    """
    logger.info(f"Admin {current_admin.username} attempting to create recording metadata for LAN ID: {recording_create.lan_id}")
    try:
        new_recording = await recording_service.create_recording(recording_create)
        logger.info(f"Recording metadata created for LAN ID: {new_recording.lan_id} by admin {current_admin.username}.")
        return new_recording
    except DuplicateEntryException as e:
        logger.warning(f"Failed to create recording for LAN ID {recording_create.lan_id}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Unexpected error creating recording for LAN ID {recording_create.lan_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create recording metadata.")

@router.get("/recordings/{recording_id}", response_model=RecordingResponse, summary="Get recording metadata by ID")
async def get_recording_by_id(
    recording_id: int,
    recording_service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_user) # Any authenticated user can view
):
    """
    Retrieves the metadata details of a specific V-KYC recording by its ID.
    Requires authentication.
    """
    logger.info(f"User {current_user.username} attempting to retrieve recording with ID: {recording_id}")
    try:
        recording = await recording_service.get_recording_by_id(recording_id)
        logger.info(f"Recording with ID {recording_id} retrieved by user {current_user.username}.")
        return recording
    except NotFoundException as e:
        logger.warning(f"Recording with ID {recording_id} not found: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Unexpected error retrieving recording with ID {recording_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve recording.")

@router.get("/recordings/", response_model=List[RecordingResponse], summary="List and filter recording metadata")
async def list_recordings(
    lan_id: Optional[str] = Query(None, description="Filter by LAN ID"),
    customer_name: Optional[str] = Query(None, description="Filter by customer name"),
    start_date: Optional[str] = Query(None, description="Filter by recording date (YYYY-MM-DD) from"),
    end_date: Optional[str] = Query(None, description="Filter by recording date (YYYY-MM-DD) to"),
    status: Optional[str] = Query(None, description="Filter by approval status (e.g., 'Approved', 'Pending', 'Rejected')"),
    page: int = Query(1, ge=1, description="Page number for pagination"),
    page_size: int = Query(10, ge=1, le=100, description="Number of items per page"),
    recording_service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_user) # Any authenticated user can view
):
    """
    Retrieves a paginated list of V-KYC recording metadata.
    Supports filtering by LAN ID, customer name, date range, and approval status.
    Requires authentication.
    """
    logger.info(f"User {current_user.username} listing recordings with filters: LAN ID={lan_id}, Customer={customer_name}, Status={status}")
    filters = RecordingFilter(
        lan_id=lan_id,
        customer_name=customer_name,
        start_date=start_date,
        end_date=end_date,
        status=status
    )
    try:
        recordings = await recording_service.get_all_recordings(filters, page, page_size)
        logger.info(f"User {current_user.username} retrieved {len(recordings)} recordings for page {page}.")
        return recordings
    except Exception as e:
        logger.error(f"Unexpected error listing recordings: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve recordings.")

@router.put("/recordings/{recording_id}", response_model=RecordingResponse, summary="Update recording metadata by ID (Admin only)")
async def update_recording(
    recording_id: int,
    recording_update: RecordingUpdate,
    recording_service: RecordingService = Depends(get_recording_service),
    current_admin: User = Depends(get_current_admin_user) # Only admins can update
):
    """
    Updates the metadata details of an existing V-KYC recording.
    Requires 'admin' role.
    """
    logger.info(f"Admin {current_admin.username} attempting to update recording with ID: {recording_id}")
    try:
        updated_recording = await recording_service.update_recording(recording_id, recording_update)
        logger.info(f"Recording with ID {recording_id} updated by admin {current_admin.username}.")
        return updated_recording
    except NotFoundException as e:
        logger.warning(f"Failed to update recording with ID {recording_id}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except DuplicateEntryException as e:
        logger.warning(f"Failed to update recording with ID {recording_id} due to conflict: {e.detail}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Unexpected error updating recording with ID {recording_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update recording metadata.")

@router.delete("/recordings/{recording_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete recording metadata by ID (Admin only)")
async def delete_recording(
    recording_id: int,
    recording_service: RecordingService = Depends(get_recording_service),
    current_admin: User = Depends(get_current_admin_user) # Only admins can delete
):
    """
    Deletes a V-KYC recording metadata entry.
    This does NOT delete the actual file from the NFS server.
    Requires 'admin' role.
    """
    logger.info(f"Admin {current_admin.username} attempting to delete recording metadata with ID: {recording_id}")
    try:
        await recording_service.delete_recording(recording_id)
        logger.info(f"Recording metadata with ID {recording_id} deleted by admin {current_admin.username}.")
    except NotFoundException as e:
        logger.warning(f"Failed to delete recording with ID {recording_id}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Unexpected error deleting recording with ID {recording_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete recording metadata.")

@router.get("/recordings/{recording_id}/download", summary="Download a V-KYC recording file")
async def download_recording(
    recording_id: int,
    recording_service: RecordingService = Depends(get_recording_service),
    current_user: User = Depends(get_current_user) # Any authenticated user can download
):
    """
    Initiates the download of a V-KYC recording file from the NFS server.
    Requires authentication.
    """
    logger.info(f"User {current_user.username} attempting to download recording with ID: {recording_id}")
    try:
        recording = await recording_service.get_recording_by_id(recording_id)
        
        # Construct the full file path. Ensure path traversal attacks are prevented.
        # The service layer should ideally validate and sanitize file_path.
        # For this demo, we assume recording.file_path is already sanitized and relative to NFS_SERVER_BASE_PATH.
        full_file_path = os.path.join(settings.NFS_SERVER_BASE_PATH, recording.file_path)
        
        # Basic security check: ensure the path is within the allowed base path
        # This is a critical security measure against path traversal.
        if not os.path.abspath(full_file_path).startswith(os.path.abspath(settings.NFS_SERVER_BASE_PATH)):
            logger.error(f"Attempted path traversal detected for file: {full_file_path}")
            raise ForbiddenException("Access to specified file path is forbidden.")

        if not os.path.exists(full_file_path):
            logger.warning(f"File not found on NFS for recording ID {recording_id}: {full_file_path}")
            raise NotFoundException(f"Recording file not found at path: {recording.file_path}")

        # Stream the file content
        def file_iterator():
            with open(full_file_path, mode="rb") as file_like:
                yield from file_like

        file_name = os.path.basename(full_file_path)
        logger.info(f"User {current_user.username} successfully initiated download for recording ID {recording_id}: {file_name}")
        return Response(
            content=file_iterator(),
            media_type="application/octet-stream", # Or specific video/audio type if known
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except FileOperationException as e:
        logger.error(f"File operation error during download for recording ID {recording_id}: {e.detail}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to read file: {e.detail}")
    except Exception as e:
        logger.error(f"Unexpected error during download for recording ID {recording_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download recording.")