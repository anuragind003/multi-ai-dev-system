import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app import crud
from app.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException, BadRequestException, ServiceUnavailableException
from app.dependencies import get_db, get_current_active_user, get_user_has_roles
from app.models import UserRole, RecordingStatus
from app.schemas import (
    MessageResponse,
    RecordingCreate,
    RecordingResponse,
    RecordingSearch,
    RecordingUpdate,
    TokenData,
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=RecordingResponse, status_code=status.HTTP_201_CREATED, summary="Create a new recording metadata entry")
async def create_recording(
    recording_in: RecordingCreate,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Creates a new recording metadata entry in the database.
    Requires authentication.
    """
    logger.info(f"User {current_user.email} attempting to create recording metadata for LAN ID: {recording_in.lan_id}")
    recording = crud.create_recording(db=db, recording=recording_in, uploader_id=current_user.user_id)
    return recording

@router.get("/", response_model=List[RecordingResponse], summary="Get all recording metadata (Admin only)")
async def read_all_recordings(
    skip: int = 0,
    limit: int = 100,
    current_user: TokenData = Depends(get_user_has_roles([UserRole.ADMIN])), # Only admins can see all
    db: Session = Depends(get_db)
):
    """
    Retrieves a list of all recording metadata entries.
    Requires Admin role.
    """
    logger.info(f"Admin user {current_user.email} requesting all recording metadata.")
    recordings = crud.get_recordings(db, skip=skip, limit=limit)
    return recordings

@router.post("/search", response_model=List[RecordingResponse], summary="Search and filter recording metadata")
async def search_recordings(
    search_params: RecordingSearch,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Searches and filters recording metadata based on provided criteria.
    Users can only search for recordings they uploaded unless they are an Admin.
    Admins can search all recordings.
    """
    logger.info(f"User {current_user.email} searching recordings with params: {search_params.model_dump_json()}")

    # If not admin, restrict search to own uploads
    if UserRole.ADMIN not in current_user.roles:
        if search_params.uploader_id is not None and search_params.uploader_id != current_user.user_id:
            raise ForbiddenException("You can only search your own uploads.")
        search_params.uploader_id = current_user.user_id # Force filter by current user's ID

    recordings = crud.search_recordings(db, search_params)
    return recordings

@router.get("/{recording_id}", response_model=RecordingResponse, summary="Get recording metadata by ID")
async def read_recording(
    recording_id: int = Path(..., description="The ID of the recording to retrieve"),
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single recording metadata entry by its ID.
    Users can only view their own recordings unless they are an Admin.
    """
    logger.info(f"User {current_user.email} requesting recording ID: {recording_id}")
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise NotFoundException(f"Recording with ID {recording_id} not found.")

    # Check ownership or admin role
    if recording.uploader_id != current_user.user_id and UserRole.ADMIN not in current_user.roles:
        raise ForbiddenException("You do not have permission to view this recording.")

    return recording

@router.put("/{recording_id}", response_model=RecordingResponse, summary="Update recording metadata")
async def update_recording(
    recording_id: int = Path(..., description="The ID of the recording to update"),
    recording_in: RecordingUpdate,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Updates an existing recording metadata entry.
    Only the uploader or an Admin can update.
    Admins can change status to APPROVED.
    """
    logger.info(f"User {current_user.email} attempting to update recording ID: {recording_id}")
    db_recording = crud.get_recording(db, recording_id)
    if not db_recording:
        raise NotFoundException(f"Recording with ID {recording_id} not found.")

    # Check ownership or admin role
    if db_recording.uploader_id != current_user.user_id and UserRole.ADMIN not in current_user.roles:
        raise ForbiddenException("You do not have permission to update this recording.")

    # Special handling for status change to APPROVED
    approver_id = None
    if recording_in.status == RecordingStatus.APPROVED:
        if UserRole.ADMIN not in current_user.roles:
            raise ForbiddenException("Only administrators can approve recordings.")
        approver_id = current_user.user_id
        logger.info(f"Recording {recording_id} status set to APPROVED by Admin {current_user.email}.")

    updated_recording = crud.update_recording(db, recording_id, recording_in, approver_id=approver_id)
    return updated_recording

@router.delete("/{recording_id}", response_model=MessageResponse, summary="Delete recording metadata (Admin only)")
async def delete_recording(
    recording_id: int = Path(..., description="The ID of the recording to delete"),
    current_user: TokenData = Depends(get_user_has_roles([UserRole.ADMIN])), # Only admins can delete
    db: Session = Depends(get_db)
):
    """
    Deletes a recording metadata entry from the database.
    Requires Admin role.
    Note: This only deletes the metadata, not the actual file on NFS.
    """
    logger.warning(f"Admin user {current_user.email} attempting to delete recording ID: {recording_id}")
    crud.delete_recording(db, recording_id)
    return {"message": f"Recording with ID {recording_id} deleted successfully."}

@router.get("/download/{recording_id}", summary="Download a V-KYC recording file")
async def download_recording(
    recording_id: int = Path(..., description="The ID of the recording to download"),
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Streams a V-KYC recording file from the NFS server.
    Users can only download their own recordings unless they are an Admin.
    """
    logger.info(f"User {current_user.email} attempting to download recording ID: {recording_id}")
    recording = crud.get_recording(db, recording_id)
    if not recording:
        raise NotFoundException(f"Recording with ID {recording_id} not found.")

    # Check ownership or admin role
    if recording.uploader_id != current_user.user_id and UserRole.ADMIN not in current_user.roles:
        raise ForbiddenException("You do not have permission to download this recording.")

    file_full_path = os.path.join(settings.NFS_RECORDINGS_PATH, recording.file_path)

    if not os.path.exists(file_full_path):
        logger.error(f"File not found on NFS: {file_full_path} for recording ID {recording_id}")
        raise NotFoundException(f"Recording file for ID {recording_id} not found on server.")

    if not os.path.isfile(file_full_path):
        logger.error(f"Path is not a file: {file_full_path} for recording ID {recording_id}")
        raise BadRequestException(f"Invalid file path for recording ID {recording_id}.")

    try:
        # Use FileResponse for simple file serving. For very large files, consider StreamingResponse
        # with a custom generator for better memory management.
        logger.info(f"Streaming file {file_full_path} for recording ID {recording_id}.")
        return FileResponse(
            path=file_full_path,
            filename=recording.file_name,
            media_type="application/octet-stream" # Or specific video/audio type if known
        )
    except Exception as e:
        logger.exception(f"Error streaming file {file_full_path}: {e}")
        raise ServiceUnavailableException("Failed to stream recording file. Please try again later.")

@router.post("/upload", response_model=MessageResponse, status_code=status.HTTP_200_OK, summary="Upload a V-KYC recording file (Simulated)")
async def upload_recording_file(
    file: UploadFile = File(..., description="The V-KYC recording file to upload"),
    lan_id: str,
    notes: Optional[str] = None,
    current_user: TokenData = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Simulates uploading a V-KYC recording file to the NFS server.
    In a real scenario, this would handle the actual file storage.
    For this example, it just logs the intent and creates metadata.
    """
    logger.info(f"User {current_user.email} attempting to upload file: {file.filename} for LAN ID: {lan_id}")

    # --- SIMULATION OF FILE STORAGE ---
    # In a real application, you would:
    # 1. Generate a unique, secure file name/path on the NFS.
    # 2. Save the uploaded file to that path.
    # 3. Handle potential errors (disk full, permissions, network issues).
    # 4. Potentially run virus scans or other processing.

    # For demonstration, we'll just pretend to save it and use a dummy path.
    # In a real system, ensure `settings.NFS_RECORDINGS_PATH` is correctly mounted and writable.
    relative_file_path = f"{lan_id}/{file.filename}" # Example: lan_id/original_file.mp4
    simulated_full_path = os.path.join(settings.NFS_RECORDINGS_PATH, relative_file_path)

    # Ensure the directory exists (in a real scenario, this would be handled by NFS setup)
    os.makedirs(os.path.dirname(simulated_full_path), exist_ok=True)

    try:
        # Simulate writing the file (optional, depends on if you want actual file writes in dev)
        # with open(simulated_full_path, "wb") as buffer:
        #     while True:
        #         chunk = await file.read(1024 * 1024) # Read 1MB chunks
        #         if not chunk:
        #             break
        #         buffer.write(chunk)
        logger.info(f"Simulated file upload to: {simulated_full_path}")

        # Create metadata entry
        recording_create = RecordingCreate(
            lan_id=lan_id,
            file_name=file.filename,
            file_path=relative_file_path, # Store relative path in DB
            notes=notes
        )
        crud.create_recording(db=db, recording=recording_create, uploader_id=current_user.user_id)

        return {"message": f"File '{file.filename}' for LAN ID '{lan_id}' uploaded and metadata created successfully."}
    except Exception as e:
        logger.exception(f"Failed to process file upload for {file.filename}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process file upload.")