from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from schemas import RecordingResponse, RecordingCreate, UserResponse
from services import RecordingService, AuditLogService
from utils.dependencies import get_db, get_recording_service, get_audit_log_service, get_current_user
from utils.errors import NotFoundException, ForbiddenException, ValidationException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post("/", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED, summary="Create Recording Metadata", description="Creates a new recording metadata entry in the database. (Admin only)")
async def create_recording(
    recording_data: RecordingCreate,
    current_user: UserResponse = Depends(get_current_user),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    Creates a new recording metadata entry.
    Requires admin privileges.
    """
    if not current_user.is_admin:
        raise ForbiddenException("Only administrators can create recording metadata.")
    
    try:
        recording = recording_service.create_recording(recording_data)
        logger.info(f"Recording metadata created for LAN ID: {recording.lan_id} by user {current_user.username}")
        return recording
    except ValidationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    except Exception as e:
        logger.error(f"Error creating recording metadata: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create recording metadata.")


@router.get("/{recording_id}", response_model=RecordingResponse, summary="Get Recording Metadata by ID", description="Retrieves metadata for a specific recording by its ID.")
async def get_recording(
    recording_id: int,
    current_user: UserResponse = Depends(get_current_user),
    recording_service: RecordingService = Depends(get_recording_service)
):
    """
    Retrieves metadata for a specific recording.
    Requires authentication.
    """
    try:
        recording = recording_service.get_recording_by_id(recording_id)
        logger.info(f"User {current_user.username} retrieved metadata for recording ID: {recording_id}")
        return recording
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error retrieving recording {recording_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve recording metadata.")


@router.get("/{recording_id}/download", summary="Download Recording", description="Downloads a specific recording file and logs the action.")
async def download_recording(
    recording_id: int,
    current_user: UserResponse = Depends(get_current_user),
    recording_service: RecordingService = Depends(get_recording_service),
    audit_log_service: AuditLogService = Depends(get_audit_log_service)
):
    """
    Downloads a recording file.
    This action is audited.
    Requires authentication.
    """
    try:
        recording = recording_service.get_recording_by_id(recording_id)
        
        # Log the download action BEFORE attempting to serve the file
        audit_log_service.log_action(
            user_id=current_user.id,
            action="download_recording",
            resource_type="recording",
            resource_id=recording.id,
            details=f"User '{current_user.username}' downloaded recording with LAN ID '{recording.lan_id}'."
        )
        logger.info(f"User {current_user.username} initiated download for recording ID: {recording_id} (LAN ID: {recording.lan_id})")

        # Serve the file
        return recording_service.download_recording(recording)

    except NotFoundException as e:
        logger.warning(f"Download failed: {e.detail} for user {current_user.username}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ValidationException as e:
        logger.error(f"Download validation failed: {e.detail} for user {current_user.username}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    except Exception as e:
        logger.critical(f"Critical error during recording download for ID {recording_id} by user {current_user.username}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to download recording due to an unexpected error.")