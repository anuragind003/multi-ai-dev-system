from typing import List, Annotated
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from services.recording_service import RecordingService
from schemas import RecordingCreate, RecordingResponse, RecordingUpdate, RecordingFilter
from database import get_db
from auth import get_current_active_user, get_current_auditor_or_admin_user, get_current_admin_user
from models import User, UserRole
from core.errors import NotFoundError, FileOperationError, DatabaseError, ValidationError
from config import settings, logger
from fastapi_limiter.depends import RateLimiter

router = APIRouter(prefix="/recordings", tags=["Recordings"])

@router.post(
    "/upload",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a V-KYC recording file and create metadata",
    dependencies=[Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def upload_recording(
    file: Annotated[UploadFile, File(description="V-KYC recording file to upload.")],
    lan_id: Annotated[str, File(description="LAN ID associated with the recording.")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Uploads a V-KYC recording file to the server (simulated NFS) and creates
    the corresponding metadata entry in the database.
    Requires authentication.
    """
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided.")
    if not lan_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="LAN ID is required.")

    recording_service = RecordingService(db)
    try:
        recording = await recording_service.upload_recording_file(file, lan_id, current_user)
        return recording
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except FileOperationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled error during recording upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during file upload.")


@router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="Get recording metadata by ID",
    dependencies=[Depends(get_current_active_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def get_recording_by_id(
    recording_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves the metadata for a specific V-KYC recording by its ID.
    Requires authentication.
    """
    recording_service = RecordingService(db)
    try:
        recording = recording_service.get_recording_by_id(recording_id)
        return recording
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/",
    response_model=List[RecordingResponse],
    summary="List all recording metadata with filters",
    dependencies=[Depends(get_current_active_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def list_recordings(
    filters: Annotated[RecordingFilter, Depends()],
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Retrieves a paginated list of V-KYC recording metadata.
    Supports filtering by LAN ID, status, upload date range, and uploader.
    Requires authentication.
    """
    recording_service = RecordingService(db)
    recordings = recording_service.get_all_recordings(filters, skip=skip, limit=limit)
    return recordings

@router.put(
    "/{recording_id}/status",
    response_model=RecordingResponse,
    summary="Update recording status (Auditor/Admin only)",
    dependencies=[Depends(get_current_auditor_or_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def update_recording_status(
    recording_id: int,
    update_data: RecordingUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates the status and notes of a V-KYC recording.
    Only users with 'auditor' or 'admin' roles can access this endpoint.
    """
    recording_service = RecordingService(db)
    try:
        updated_recording = recording_service.update_recording_status(recording_id, update_data)
        return updated_recording
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get(
    "/{recording_id}/download",
    summary="Download a V-KYC recording file",
    response_class=FileResponse,
    dependencies=[Depends(get_current_active_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def download_recording(
    recording_id: int,
    db: Session = Depends(get_db)
):
    """
    Downloads the actual V-KYC recording file from the server (simulated NFS).
    Requires authentication.
    """
    recording_service = RecordingService(db)
    try:
        return recording_service.download_recording_file(recording_id)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except FileOperationError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        logger.error(f"Unhandled error during recording download: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during file download.")

@router.delete(
    "/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete recording metadata and file (Admin only)",
    dependencies=[Depends(get_current_admin_user), Depends(RateLimiter(times=settings.RATE_LIMIT_PER_MINUTE, seconds=60))]
)
async def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db)
):
    """
    Deletes a V-KYC recording's metadata from the database and its associated file from the server.
    Only users with 'admin' role can access this endpoint.
    """
    recording_service = RecordingService(db)
    try:
        recording_service.delete_recording(recording_id)
        return {"message": "Recording deleted successfully."}
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (DatabaseError, FileOperationError) as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))