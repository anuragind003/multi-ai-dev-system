from typing import List
from fastapi import APIRouter, Depends, status, Query, Path
from sqlalchemy.orm import Session
from fastapi_limiter.depends import RateLimiter

from database import get_db
from schemas import VKYCRecordingCreate, VKYCRecordingUpdate, VKYCRecordingResponse
from services import VKYCRecordingService
from auth import get_current_active_user, get_current_active_admin_user # Assuming user roles
from schemas import User # For dependency injection type hinting
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/vkyc-recordings",
    tags=["VKYC Recordings"],
    dependencies=[Depends(RateLimiter(times=10, seconds=10))], # Apply rate limit to all endpoints in this router
    responses={404: {"description": "Not found"}},
)

# Dependency to get VKYCRecordingService instance
def get_vkyc_recording_service(db: Session = Depends(get_db)) -> VKYCRecordingService:
    """Provides a VKYCRecordingService instance with a database session."""
    return VKYCRecordingService(db)

@router.post(
    "/",
    response_model=VKYCRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKYC recording",
    description="Creates a new VKYC recording record in the system. Requires 'user' or 'admin' scope.",
    dependencies=[Depends(get_current_active_user)], # Example: only active users can create
)
async def create_vkyc_recording(
    recording_data: VKYCRecordingCreate,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: User = Depends(get_current_active_user) # Inject current user for logging/auditing
):
    """
    Create a VKYC recording with the provided details.
    - **lan_id**: Unique identifier for the recording.
    - **recording_path**: Path to the recording file.
    - **recording_date**: Date and time of the recording.
    - **status**: Current status (e.g., PENDING, COMPLETED).
    - **uploaded_by**: User who uploaded the recording.
    """
    logger.info(f"User {current_user.username} attempting to create VKYC recording with LAN ID: {recording_data.lan_id}")
    new_recording = service.create_recording(recording_data)
    logger.info(f"VKYC recording created successfully with ID: {new_recording.id} by {current_user.username}")
    return new_recording

@router.get(
    "/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Get a VKYC recording by ID",
    description="Retrieves a single VKYC recording by its unique ID. Requires 'user' or 'admin' scope.",
    dependencies=[Depends(get_current_active_user)],
)
async def get_vkyc_recording(
    recording_id: int = Path(..., gt=0, description="The ID of the VKYC recording to retrieve."),
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve details of a specific VKYC recording by its ID.
    """
    logger.info(f"User {current_user.username} requesting VKYC recording with ID: {recording_id}")
    recording = service.get_recording(recording_id)
    return recording

@router.get(
    "/",
    response_model=List[VKYCRecordingResponse],
    summary="Get all VKYC recordings",
    description="Retrieves a list of all VKYC recordings with pagination. Requires 'user' or 'admin' scope.",
    dependencies=[Depends(get_current_active_user)],
)
async def get_all_vkyc_recordings(
    skip: int = Query(0, ge=0, description="Number of records to skip."),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return."),
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve a list of all VKYC recordings.
    - **skip**: Number of records to skip for pagination.
    - **limit**: Maximum number of records to return.
    """
    logger.info(f"User {current_user.username} requesting all VKYC recordings (skip={skip}, limit={limit})")
    recordings = service.get_all_recordings(skip=skip, limit=limit)
    return recordings

@router.put(
    "/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Update a VKYC recording",
    description="Updates an existing VKYC recording by its ID. Requires 'admin' scope.",
    dependencies=[Depends(get_current_active_admin_user)], # Example: only admins can update
)
async def update_vkyc_recording(
    recording_id: int = Path(..., gt=0, description="The ID of the VKYC recording to update."),
    recording_data: VKYCRecordingUpdate,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: User = Depends(get_current_active_admin_user)
):
    """
    Update details of a specific VKYC recording.
    - **recording_id**: The ID of the recording to update.
    - **recording_data**: Fields to update.
    """
    logger.info(f"Admin user {current_user.username} attempting to update VKYC recording with ID: {recording_id}")
    updated_recording = service.update_recording(recording_id, recording_data)
    logger.info(f"VKYC recording ID {recording_id} updated successfully by {current_user.username}")
    return updated_recording

@router.delete(
    "/{recording_id}",
    status_code=status.HTTP_200_OK,
    response_model=VKYCRecordingResponse, # Return the soft-deleted record
    summary="Soft delete a VKYC recording",
    description="Soft deletes a VKYC recording by its ID (sets is_active to False). Requires 'admin' scope.",
    dependencies=[Depends(get_current_active_admin_user)], # Example: only admins can delete
)
async def delete_vkyc_recording(
    recording_id: int = Path(..., gt=0, description="The ID of the VKYC recording to soft delete."),
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: User = Depends(get_current_active_admin_user)
):
    """
    Soft delete a specific VKYC recording.
    The record's `is_active` flag will be set to `False`.
    """
    logger.info(f"Admin user {current_user.username} attempting to soft-delete VKYC recording with ID: {recording_id}")
    deleted_recording = service.delete_recording(recording_id)
    logger.info(f"VKYC recording ID {recording_id} soft-deleted successfully by {current_user.username}")
    return deleted_recording