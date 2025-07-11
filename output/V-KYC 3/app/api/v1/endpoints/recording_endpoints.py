import json
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import RecordingResponse, RecordingCreate, RecordingUpdate, BulkRequestCreate, BulkRequestResponse
from app.services.recording_service import RecordingService
from app.auth import get_current_user, has_permission
from app.models import User
from app.exceptions import NotFoundException, ConflictException, InvalidInputException, ServiceUnavailableException
from app.logger import logger

router = APIRouter()

@router.post("/recordings/", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED, summary="Create Recording Metadata")
async def create_recording(
    recording: RecordingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:upload")) # Requires 'recording:upload' permission
):
    """
    Creates new metadata for a V-KYC recording.
    Simulates file creation on the NFS server.
    Requires 'recording:upload' permission.
    """
    recording_service = RecordingService(db)
    try:
        new_recording = recording_service.create_recording(recording, current_user.id)
        logger.info(f"User {current_user.email} created recording metadata for: {new_recording.file_name}")
        return new_recording
    except (ConflictException, ServiceUnavailableException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error creating recording: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during recording creation.")

@router.get("/recordings/", response_model=List[RecordingResponse], summary="Get All Recordings")
async def read_recordings(
    skip: int = 0,
    limit: int = 100,
    lan_id: Optional[str] = Query(None, description="Filter recordings by LAN ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:read")) # Requires 'recording:read' permission
):
    """
    Retrieves a list of all recording metadata with pagination and optional filtering.
    Requires 'recording:read' permission.
    """
    recording_service = RecordingService(db)
    recordings = recording_service.get_all_recordings(skip=skip, limit=limit, lan_id=lan_id)
    return recordings

@router.get("/recordings/{recording_id}", response_model=RecordingResponse, summary="Get Recording by ID")
async def read_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:read")) # Requires 'recording:read' permission
):
    """
    Retrieves a single recording's metadata by its ID.
    Requires 'recording:read' permission.
    """
    recording_service = RecordingService(db)
    recording = recording_service.get_recording_by_id(recording_id)
    return recording

@router.put("/recordings/{recording_id}", response_model=RecordingResponse, summary="Update Recording Metadata")
async def update_recording(
    recording_id: int,
    recording: RecordingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:upload")) # Requires 'recording:upload' permission
):
    """
    Updates an existing recording's metadata.
    Simulates file updates on the NFS server if file_path changes.
    Requires 'recording:upload' permission.
    """
    recording_service = RecordingService(db)
    try:
        updated_recording = recording_service.update_recording(recording_id, recording)
        logger.info(f"User {current_user.email} updated recording metadata for ID: {recording_id}")
        return updated_recording
    except (NotFoundException, ConflictException, ServiceUnavailableException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error updating recording {recording_id}: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during recording update.")

@router.delete("/recordings/{recording_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete Recording Metadata")
async def delete_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:delete")) # Requires 'recording:delete' permission
):
    """
    Deletes a recording's metadata and simulates file deletion on the NFS server.
    Requires 'recording:delete' permission.
    """
    recording_service = RecordingService(db)
    try:
        recording_service.delete_recording(recording_id)
        logger.info(f"User {current_user.email} deleted recording metadata for ID: {recording_id}")
        return {"message": "Recording deleted successfully"}
    except (NotFoundException, ServiceUnavailableException, InvalidInputException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error deleting recording {recording_id}: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during recording deletion.")

@router.get("/recordings/{recording_id}/download", summary="Download Recording File")
async def download_recording(
    recording_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("recording:download")) # Requires 'recording:download' permission
):
    """
    Downloads a V-KYC recording file.
    Simulates fetching the file from the NFS server.
    Requires 'recording:download' permission.
    """
    recording_service = RecordingService(db)
    try:
        file_path = recording_service.download_recording_file(recording_id)
        logger.info(f"User {current_user.email} initiated download for recording ID: {recording_id}")
        # FastAPI's FileResponse will stream the file
        return FileResponse(path=file_path, filename=file_path.split('/')[-1], media_type="application/octet-stream")
    except (NotFoundException, ServiceUnavailableException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error downloading recording {recording_id}: {e}")
        raise ServiceUnavailableException(detail="An unexpected error occurred during file download.")

@router.post("/bulk-requests/", response_model=BulkRequestResponse, status_code=status.HTTP_201_CREATED, summary="Create a Bulk Request")
async def create_bulk_request(
    bulk_request: BulkRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("bulk_request:write")) # Requires 'bulk_request:write' permission
):
    """
    Creates a new bulk operation request (e.g., bulk download).
    Requires 'bulk_request:write' permission.
    """
    recording_service = RecordingService(db)
    try:
        new_bulk_request = recording_service.create_bulk_request(bulk_request, current_user.id)
        logger.info(f"User {current_user.email} created bulk request of type: {new_bulk_request.request_type}")
        # In a real system, you'd trigger an async worker here to process the request
        # For this example, we'll simulate immediate processing if it's a download
        if new_bulk_request.request_type == "download":
            # This is a synchronous call for demonstration. In production, use a background task queue (Celery, RQ)
            recording_service.process_bulk_download(new_bulk_request.id)
            logger.info(f"Simulated immediate processing for bulk download request {new_bulk_request.id}")
            # Refresh the object to get updated status/results
            new_bulk_request = recording_service.get_bulk_request_by_id(new_bulk_request.id)
        return new_bulk_request
    except (InvalidInputException, NotFoundException, ServiceUnavailableException) as e:
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error creating bulk request: {e}")
        raise InvalidInputException(detail="An unexpected error occurred during bulk request creation.")

@router.get("/bulk-requests/", response_model=List[BulkRequestResponse], summary="Get All Bulk Requests")
async def read_bulk_requests(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = Query(None, description="Filter bulk requests by status (e.g., 'pending', 'completed')"),
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("bulk_request:read")) # Requires 'bulk_request:read' permission
):
    """
    Retrieves a list of all bulk operation requests with pagination and optional filtering.
    Requires 'bulk_request:read' permission.
    """
    recording_service = RecordingService(db)
    bulk_requests = recording_service.get_all_bulk_requests(skip=skip, limit=limit, status=status)
    return bulk_requests

@router.get("/bulk-requests/{request_id}", response_model=BulkRequestResponse, summary="Get Bulk Request by ID")
async def read_bulk_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(has_permission("bulk_request:read")) # Requires 'bulk_request:read' permission
):
    """
    Retrieves a single bulk operation request by its ID.
    Requires 'bulk_request:read' permission.
    """
    recording_service = RecordingService(db)
    bulk_request = recording_service.get_bulk_request_by_id(request_id)
    return bulk_request