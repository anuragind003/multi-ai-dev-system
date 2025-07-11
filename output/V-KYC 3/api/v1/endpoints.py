from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from schemas import (
    VKYCRecordingCreate,
    VKYCRecordingUpdate,
    VKYCRecordingResponse,
    VKYCRecordingListResponse,
    UserCreate,
    UserResponse,
    Token,
    UserLogin
)
from services import VKYCRecordingService, UserService
from auth import get_current_user, require_role, require_any_role, authenticate_user, create_access_token
from models import UserRole, VKYCRecordingStatus
from logger import logger
from config import get_settings
from slowapi.ext.fastapi_limiter.decorators import rate_limit

settings = get_settings()

router = APIRouter(prefix="/api/v1", tags=["VKYC Recordings", "Authentication", "Users"])

# Dependency for VKYCRecordingService
def get_vkyc_recording_service(db: Session = Depends(get_db)) -> VKYCRecordingService:
    return VKYCRecordingService(db)

# Dependency for UserService
def get_user_service(db: Session = Depends(get_db)) -> UserService:
    return UserService(db)

# --- Authentication Endpoints ---
@router.post(
    "/token",
    response_model=Token,
    summary="Authenticate User",
    description="Authenticates a user and returns an access token.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def login_for_access_token(
    user_login: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Authenticates a user with username and password.
    On successful authentication, returns a JWT access token.
    """
    logger.info(f"Attempting login for user: {user_login.username}")
    user = authenticate_user(db, user_login.username, user_login.password)
    if not user:
        logger.warning(f"Failed login attempt for user: {user_login.username}")
        raise_unauthorized_exception()
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": [user.role.value]},
        expires_delta=access_token_expires
    )
    logger.info(f"User {user_login.username} successfully logged in.")
    return {"access_token": access_token, "token_type": "bearer"}

@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get Current User",
    description="Retrieves details of the currently authenticated user.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def read_users_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Returns the details of the authenticated user.
    Requires a valid JWT token.
    """
    logger.info(f"User '{current_user.username}' requested their own profile.")
    return current_user

# --- User Management Endpoints (Admin Only) ---
@router.post(
    "/users",
    response_model=UserResponse,
    summary="Create New User",
    description="Creates a new user. Requires 'admin' role.",
    status_code=status.HTTP_201_CREATED
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_user_endpoint(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(require_role(UserRole.ADMIN)) # Admin only
):
    """
    Creates a new user with the provided details.
    Only users with 'admin' role can perform this action.
    """
    logger.info(f"Admin user '{current_user.username}' creating new user: {user_data.username}")
    return user_service.create_user(user_data)

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get User by ID",
    description="Retrieves a user by their ID. Requires 'admin' or 'auditor' role.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_user_by_id_endpoint(
    user_id: int,
    user_service: UserService = Depends(get_user_service),
    current_user: UserResponse = Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Retrieves a user's details by their ID.
    Only users with 'admin' or 'auditor' roles can perform this action.
    """
    logger.info(f"User '{current_user.username}' requested user details for ID: {user_id}")
    return user_service.get_user_by_id(user_id)


# --- VKYC Recording Endpoints ---
@router.post(
    "/vkyc-recordings",
    response_model=VKYCRecordingResponse,
    summary="Create VKYC Recording",
    description="Creates a new VKYC recording entry. Requires 'admin' or 'auditor' role.",
    status_code=status.HTTP_201_CREATED
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_vkyc_recording(
    recording_data: VKYCRecordingCreate,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: UserResponse = Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Creates a new VKYC recording entry in the system.
    The `lan_id` must be unique.
    Requires 'admin' or 'auditor' role.
    """
    logger.info(f"User '{current_user.username}' creating VKYC recording for LAN ID: {recording_data.lan_id}")
    return service.create_recording(recording_data)

@router.get(
    "/vkyc-recordings/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Get VKYC Recording by ID",
    description="Retrieves a specific VKYC recording by its ID. Requires 'admin', 'auditor', or 'viewer' role.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def get_vkyc_recording_by_id(
    recording_id: int,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: UserResponse = Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR, UserRole.VIEWER]))
):
    """
    Retrieves a VKYC recording by its unique ID.
    Requires 'admin', 'auditor', or 'viewer' role.
    """
    logger.info(f"User '{current_user.username}' retrieving VKYC recording ID: {recording_id}")
    return service.get_recording_by_id(recording_id)

@router.get(
    "/vkyc-recordings",
    response_model=VKYCRecordingListResponse,
    summary="List VKYC Recordings",
    description="Retrieves a paginated list of VKYC recordings with optional filters. Requires 'admin', 'auditor', or 'viewer' role.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def list_vkyc_recordings(
    skip: int = Query(0, ge=0, description="Number of items to skip (for pagination)"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of items to return (for pagination)"),
    lan_id: Optional[str] = Query(None, min_length=3, max_length=50, description="Filter by LAN ID (partial match)"),
    status: Optional[VKYCRecordingStatus] = Query(None, description="Filter by recording status"),
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: UserResponse = Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR, UserRole.VIEWER]))
):
    """
    Retrieves a list of VKYC recordings.
    Supports pagination (`skip`, `limit`) and filtering by `lan_id` (partial match) and `status`.
    Requires 'admin', 'auditor', or 'viewer' role.
    """
    logger.info(f"User '{current_user.username}' listing VKYC recordings with filters: lan_id={lan_id}, status={status}, skip={skip}, limit={limit}")
    recordings, total_count = service.get_all_recordings(skip=skip, limit=limit, lan_id_filter=lan_id, status_filter=status)
    return VKYCRecordingListResponse(
        total=total_count,
        page=skip // limit + 1,
        page_size=limit,
        items=recordings
    )

@router.put(
    "/vkyc-recordings/{recording_id}",
    response_model=VKYCRecordingResponse,
    summary="Update VKYC Recording",
    description="Updates an existing VKYC recording. Requires 'admin' or 'auditor' role.",
    status_code=status.HTTP_200_OK
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def update_vkyc_recording(
    recording_id: int,
    update_data: VKYCRecordingUpdate,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: UserResponse = Depends(require_any_role([UserRole.ADMIN, UserRole.AUDITOR]))
):
    """
    Updates an existing VKYC recording identified by `recording_id`.
    Only provided fields will be updated.
    Requires 'admin' or 'auditor' role.
    """
    logger.info(f"User '{current_user.username}' updating VKYC recording ID: {recording_id}")
    return service.update_recording(recording_id, update_data)

@router.delete(
    "/vkyc-recordings/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete VKYC Recording",
    description="Deletes a VKYC recording. Requires 'admin' role.",
)
@rate_limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def delete_vkyc_recording(
    recording_id: int,
    service: VKYCRecordingService = Depends(get_vkyc_recording_service),
    current_user: UserResponse = Depends(require_role(UserRole.ADMIN)) # Admin only
):
    """
    Deletes a VKYC recording from the system.
    Requires 'admin' role.
    """
    logger.info(f"Admin user '{current_user.username}' deleting VKYC recording ID: {recording_id}")
    service.delete_recording(recording_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Helper for unauthorized exceptions
def raise_unauthorized_exception():
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )