from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from schemas import RecordingCreate, RecordingResponse, RecordingUpdate, RecordingSearch
from services import recording_service
from database import get_db
from core.security import get_current_active_user, require_roles
from core.exceptions import NotFoundException, ForbiddenException, ConflictException, ServiceUnavailableException
from models import User, UserRole, RecordingStatus
from typing import List
from loguru import logger
import os

router = APIRouter(prefix="/recordings", tags=["Recordings"])

@router.post(
    "/upload",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload V-KYC recording metadata",
    description="Uploads metadata for a V-KYC recording. The actual file is assumed to be on NFS. Requires 'user' or 'admin' role."
)
async def upload_recording_metadata(
    recording_in: RecordingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.USER, UserRole.ADMIN]))
):
    """
    Uploads metadata for a V-KYC recording.
    - **lan_id**: Loan Account Number or unique identifier.
    - **file_path**: Path to the recording file on the NFS server.
    - **notes**: Optional notes about the recording.
    """
    logger.info(f"User '{current_user.username}' attempting to upload recording metadata for LAN ID: {recording_in.lan_id}")
    try:
        recording = await recording_service.upload_recording_metadata(db, recording_in, current_user)
        return RecordingResponse.model_validate(recording)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error uploading recording metadata for LAN ID {recording_in.lan_id} by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during metadata upload.")

@router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="Get recording details by ID",
    description="Retrieves detailed information about a specific V-KYC recording. Requires 'user', 'auditor', or 'admin' role."
)
async def get_recording_details(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.USER, UserRole.AUDITOR, UserRole.ADMIN]))
):
    """
    Get details of a specific recording.
    - **recording_id**: The ID of the recording.
    """
    logger.info(f"User '{current_user.username}' requested details for recording ID: {recording_id}")
    try:
        recording = await recording_service.get_recording_details(db, recording_id)
        return RecordingResponse.model_validate(recording)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error retrieving recording ID {recording_id} by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.put(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="Update recording status or notes",
    description="Updates the status or notes of a V-KYC recording. Requires 'auditor' or 'admin' role."
)
async def update_recording_status(
    recording_id: int,
    recording_update: RecordingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.AUDITOR, UserRole.ADMIN]))
):
    """
    Update a recording's status or notes.
    - **recording_id**: The ID of the recording to update.
    - **recording_update**: The updated recording data (status, notes).
    """
    logger.info(f"User '{current_user.username}' attempting to update recording ID: {recording_id}")
    try:
        updated_recording = await recording_service.update_recording_status(db, recording_id, recording_update, current_user)
        return RecordingResponse.model_validate(updated_recording)
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ForbiddenException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except Exception as e:
        logger.error(f"Error updating recording ID {recording_id} by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during update.")

@router.post(
    "/search",
    response_model=List[RecordingResponse],
    summary="Search and filter recordings",
    description="Searches and filters V-KYC recordings based on various criteria like LAN ID, status, uploader, and date range. Requires 'user', 'auditor', or 'admin' role."
)
async def search_recordings(
    search_params: RecordingSearch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.USER, UserRole.AUDITOR, UserRole.ADMIN]))
):
    """
    Search and filter recordings.
    - **search_params**: Criteria for filtering (lan_id, status, uploader_id, date range, limit, offset).
    """
    logger.info(f"User '{current_user.username}' performing recording search with params: {search_params.model_dump()}")
    try:
        recordings, total_count = await recording_service.search_and_filter_recordings(db, search_params)
        # You might want to return total_count in headers or a custom response model
        return [RecordingResponse.model_validate(rec) for rec in recordings]
    except Exception as e:
        logger.error(f"Error during recording search by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during search.")

@router.get(
    "/download/{recording_id}",
    summary="Download V-KYC recording file",
    description="Streams a V-KYC recording file from the NFS server. Requires 'user', 'auditor', or 'admin' role."
)
async def download_recording_file(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles([UserRole.USER, UserRole.AUDITOR, UserRole.ADMIN]))
):
    """
    Download a V-KYC recording file.
    - **recording_id**: The ID of the recording to download.
    """
    logger.info(f"User '{current_user.username}' attempting to download recording ID: {recording_id}")
    try:
        recording = await recording_service.get_recording_details(db, recording_id)
        
        # Simulate file existence check on NFS
        # In a real system, you'd check if the file_path exists and is accessible on NFS
        # For this example, we assume the file_path is valid and the file can be streamed.
        
        file_path = recording.file_path
        file_name = os.path.basename(file_path) # Extract filename for download

        # Stream the file
        file_iterator = await recording_service.stream_recording_file(file_path)
        
        return StreamingResponse(
            file_iterator,
            media_type="application/octet-stream", # Or specific video/audio type if known
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ServiceUnavailableException as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.detail)
    except Exception as e:
        logger.error(f"Error downloading recording ID {recording_id} by {current_user.username}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during download.")