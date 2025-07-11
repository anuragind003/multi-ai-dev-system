from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from database import get_db
from schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    RecordingCreate, RecordingUpdate, RecordingResponse, RecordingSearch,
    PaginatedRecordingsResponse, ErrorResponse
)
from services.auth_service import AuthService
from services.recording_service import RecordingService
from security.dependencies import get_current_user, has_role
from models import User, UserRole
from core.exceptions import CustomHTTPException
from core.logging_config import setup_logging

logger = setup_logging()

api_router = APIRouter()

# --- Authentication Endpoints ---
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

@auth_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        409: {"model": ErrorResponse, "description": "Conflict - Username or email already exists"},
        422: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new user with the provided details.
    By default, new users are created with 'viewer' role unless specified otherwise (e.g., by an admin).
    """
    auth_service = AuthService(db)
    logger.info(f"API: Registering user {user_data.username}")
    return await auth_service.register_user(user_data)

@auth_router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and get JWT token",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Invalid credentials"},
        403: {"model": ErrorResponse, "description": "Forbidden - User inactive"},
        422: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
async def login_for_access_token(
    user_login: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user with username and password and returns an access token.
    """
    auth_service = AuthService(db)
    logger.info(f"API: User {user_login.username} attempting to log in")
    user = await auth_service.authenticate_user(user_login)
    token = auth_service.create_access_token(
        data={"sub": user.username, "roles": [user.role.value]}
    )
    return token

@auth_router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user details",
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized - Not authenticated"},
        403: {"model": ErrorResponse, "description": "Forbidden - User inactive"}
    }
)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieves the details of the currently authenticated user.
    """
    logger.info(f"API: User {current_user.username} accessing /me endpoint")
    return UserResponse.from_orm(current_user)

# --- Recording Endpoints ---
recordings_router = APIRouter(prefix="/recordings", tags=["Recordings"])

@recordings_router.post(
    "/",
    response_model=RecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new V-KYC recording entry",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        400: {"model": ErrorResponse, "description": "Bad Request - File not found on NFS"},
        409: {"model": ErrorResponse, "description": "Conflict - Duplicate file path"},
        422: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
async def create_recording(
    recording_data: RecordingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new V-KYC recording entry in the system.
    Requires 'admin' or 'manager' role.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} creating recording for LAN ID: {recording_data.lan_id}")
    return await recording_service.create_recording(recording_data, current_user.id)

@recordings_router.get(
    "/",
    response_model=PaginatedRecordingsResponse,
    summary="Get all V-KYC recording entries with pagination",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR, UserRole.VIEWER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"}
    }
)
async def get_all_recordings(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a paginated list of all V-KYC recording entries.
    Accessible by all roles.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} fetching all recordings (skip={skip}, limit={limit})")
    recordings, total = await recording_service.get_all_recordings(skip=skip, limit=limit)
    return PaginatedRecordingsResponse(
        total=total,
        page=skip // limit + 1,
        size=len(recordings),
        items=[RecordingResponse.from_orm(rec) for rec in recordings]
    )

@recordings_router.post(
    "/search",
    response_model=PaginatedRecordingsResponse,
    summary="Search and filter V-KYC recording entries",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR, UserRole.VIEWER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        422: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
async def search_recordings(
    search_params: RecordingSearch,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Searches and filters V-KYC recording entries based on various criteria.
    Accessible by all roles.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} searching recordings with params: {search_params.model_dump()}")
    recordings, total = await recording_service.search_recordings(search_params, skip=skip, limit=limit)
    return PaginatedRecordingsResponse(
        total=total,
        page=skip // limit + 1,
        size=len(recordings),
        items=[RecordingResponse.from_orm(rec) for rec in recordings]
    )

@recordings_router.get(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="Get a V-KYC recording entry by ID",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR, UserRole.VIEWER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Not Found - Recording not found"}
    }
)
async def get_recording_by_id(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a single V-KYC recording entry by its ID.
    Accessible by all roles.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} fetching recording ID: {recording_id}")
    recording = await recording_service.get_recording_by_id(recording_id)
    if not recording:
        logger.warning(f"API: Recording ID {recording_id} not found.")
        raise CustomHTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recording not found.",
            code="RECORDING_NOT_FOUND"
        )
    return RecordingResponse.from_orm(recording)

@recordings_router.put(
    "/{recording_id}",
    response_model=RecordingResponse,
    summary="Update a V-KYC recording entry by ID",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER]))],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Not Found - Recording not found"},
        400: {"model": ErrorResponse, "description": "Bad Request - File not found on NFS"},
        409: {"model": ErrorResponse, "description": "Conflict - Duplicate file path"},
        422: {"model": ErrorResponse, "description": "Validation Error"}
    }
)
async def update_recording(
    recording_id: int,
    update_data: RecordingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Updates an existing V-KYC recording entry.
    Requires 'admin' or 'manager' role.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} updating recording ID: {recording_id}")
    return await recording_service.update_recording(recording_id, update_data)

@recordings_router.delete(
    "/{recording_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a V-KYC recording entry by ID",
    dependencies=[Depends(has_role([UserRole.ADMIN]))],
    responses={
        204: {"description": "No Content - Recording successfully deleted"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Not Found - Recording not found"}
    }
)
async def delete_recording(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes a V-KYC recording entry from the system.
    Requires 'admin' role.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} deleting recording ID: {recording_id}")
    await recording_service.delete_recording(recording_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@recordings_router.get(
    "/{recording_id}/download",
    summary="Get the file path for a V-KYC recording",
    dependencies=[Depends(has_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.AUDITOR]))],
    responses={
        200: {"description": "Success - Returns the file path (in a real app, this would stream the file)"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - Insufficient permissions"},
        404: {"model": ErrorResponse, "description": "Not Found - Recording not found"},
        500: {"model": ErrorResponse, "description": "Internal Server Error - File not accessible"}
    }
)
async def download_recording_file(
    recording_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves the full path to the V-KYC recording file on the NFS server.
    In a real-world scenario, this endpoint would handle streaming the file content
    rather than just returning the path for security and performance reasons.
    Requires 'admin', 'manager', or 'auditor' role.
    """
    recording_service = RecordingService(db)
    logger.info(f"API: User {current_user.username} requesting download path for recording ID: {recording_id}")
    file_path = await recording_service.get_recording_file(recording_id)
    # In a real application, you would use FileResponse or StreamingResponse here
    # from fastapi.responses import FileResponse
    # return FileResponse(path=file_path, filename=os.path.basename(file_path), media_type="video/mp4")
    return {"message": "File path retrieved successfully (in production, this would stream the file)", "file_path": file_path}


# Include routers in the main API router
api_router.include_router(auth_router)
api_router.include_router(recordings_router)