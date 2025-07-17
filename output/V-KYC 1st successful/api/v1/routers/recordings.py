from fastapi import APIRouter, Depends, status, Path
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db_session
from db.models import RecordingResponse
from services.recording_service import RecordingService
from security.auth import get_current_user
from security.permissions import RoleChecker
from core.exceptions import NotFoundException, ForbiddenException
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Define roles for access control
# In a real system, these would come from a central enum or config
ROLES_VIEW_RECORDING = ["admin", "process_manager", "team_lead"]

@router.get(
    "/recordings/{recording_id}",
    response_model=RecordingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single VKYC recording by ID",
    description="Retrieves detailed information for a specific VKYC recording using its unique database ID. Requires authentication and appropriate role (Admin, Process Manager, Team Lead)."
)
async def get_recording_details(
    recording_id: int = Path(..., gt=0, description="The unique ID of the recording to retrieve."),
    db: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user), # Authenticates user
    # Authorizes user based on roles
    authorize: bool = Depends(RoleChecker(allowed_roles=ROLES_VIEW_RECORDING)) 
):
    """
    Endpoint to retrieve details of a single VKYC recording.

    Args:
        recording_id (int): The unique ID of the recording.
        db (Session): Database session dependency.
        current_user (dict): Authenticated user information.
        authorize (bool): Dependency to check user roles.

    Returns:
        RecordingResponse: The recording details.

    Raises:
        NotFoundException: If the recording with the given ID is not found.
        ForbiddenException: If the authenticated user does not have the required role.
        UnauthorizedException: If no valid authentication token is provided.
    """
    logger.info(f"User '{current_user['username']}' (Roles: {current_user['roles']}) attempting to retrieve recording with ID: {recording_id}")
    
    recording_service = RecordingService(db)
    
    recording = recording_service.get_recording_by_id(recording_id)
    
    if not recording:
        logger.warning(f"Recording with ID {recording_id} not found.")
        raise NotFoundException(detail=f"Recording with ID {recording_id} not found.")
    
    logger.info(f"Successfully retrieved recording ID {recording_id} for user '{current_user['username']}'.")
    return recording

# Example of another endpoint (not required by prompt, but good for context)
# @router.get(
#     "/recordings",
#     response_model=List[RecordingResponse],
#     status_code=status.HTTP_200_OK,
#     summary="Get all VKYC recordings",
#     description="Retrieves a list of all VKYC recordings. Requires authentication and appropriate role."
# )
# async def get_all_recordings(
#     db: Session = Depends(get_db_session),
#     current_user: dict = Depends(get_current_user),
#     authorize: bool = Depends(RoleChecker(allowed_roles=ROLES_VIEW_RECORDING))
# ):
#     logger.info(f"User '{current_user['username']}' attempting to retrieve all recordings.")
#     recording_service = RecordingService(db)
#     recordings = recording_service.get_all_recordings()
#     logger.info(f"Successfully retrieved {len(recordings)} recordings for user '{current_user['username']}'.")
#     return recordings