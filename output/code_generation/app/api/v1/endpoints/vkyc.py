import base64
import os
import uuid
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, status, Response, Request
from fastapi.responses import StreamingResponse
from fastapi_limiter.depends import RateLimiter
from loguru import logger

from app.schemas.vkyc_record import (
    VKYCRecordCreate, VKYCRecordUpdate, VKYCRecordResponse,
    BulkUploadRequest, BulkUploadResult, BulkDownloadRequest, BulkDownloadResponse,
    ErrorResponse
)
from app.services.vkyc_service import VKYCService
from app.dependencies import DBSession, CurrentUser, require_roles
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException, InternalServerErrorException
from config import get_settings

router = APIRouter(prefix="/vkyc", tags=["VKYC Records"])
settings = get_settings()

# Dependency to inject VKYCService
async def get_vkyc_service(db_session: DBSession) -> VKYCService:
    return VKYCService(db_session)

VKYCServiceDep = Depends(get_vkyc_service)

@router.post(
    "/",
    response_model=VKYCRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKYC record",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid input"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Record already exists"}
    },
    dependencies=[Depends(require_roles(["team_lead", "admin"]))] # Only Team Leads and Admins can create
)
async def create_vkyc_record(
    record_data: VKYCRecordCreate,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Creates a new VKYC record in the database.
    Requires 'team_lead' or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to create VKYC record for LAN ID: {record_data.lan_id}")
    return await vkyc_service.create_record(record_data)

@router.get(
    "/{record_id}",
    response_model=VKYCRecordResponse,
    summary="Get a VKYC record by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Record not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
    },
    dependencies=[Depends(require_roles(["user", "team_lead", "admin"]))] # All authenticated users can view
)
async def get_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Retrieves a single VKYC record by its unique ID.
    Requires 'user', 'team_lead', or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to get VKYC record with ID: {record_id}")
    return await vkyc_service.get_record_by_id(record_id)

@router.get(
    "/",
    response_model=List[VKYCRecordResponse],
    summary="Get all VKYC records",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
    },
    dependencies=[Depends(require_roles(["user", "team_lead", "admin"]))] # All authenticated users can view
)
async def get_all_vkyc_records(
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Retrieves a list of all VKYC records with pagination and optional search.
    Requires 'user', 'team_lead', or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to get all VKYC records (skip={skip}, limit={limit}, search='{search}')")
    return await vkyc_service.get_all_records(skip=skip, limit=limit, search=search)

@router.put(
    "/{record_id}",
    response_model=VKYCRecordResponse,
    summary="Update a VKYC record",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid input"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Record not found"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "LAN ID already exists"}
    },
    dependencies=[Depends(require_roles(["team_lead", "admin"]))] # Only Team Leads and Admins can update
)
async def update_vkyc_record(
    record_id: int,
    record_data: VKYCRecordUpdate,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Updates an existing VKYC record by its ID.
    Requires 'team_lead' or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to update VKYC record with ID: {record_id}")
    return await vkyc_service.update_record(record_id, record_data)

@router.delete(
    "/{record_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a VKYC record",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Record not found"}
    },
    dependencies=[Depends(require_roles(["admin"]))] # Only Admins can delete
)
async def delete_vkyc_record(
    record_id: int,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Soft deletes a VKYC record by its ID (sets is_active to False).
    Requires 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to soft delete VKYC record with ID: {record_id}")
    return await vkyc_service.delete_record(record_id)

@router.post(
    "/bulk-upload",
    response_model=BulkUploadResult,
    summary="Bulk upload VKYC records metadata from file",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid file content"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
    },
    dependencies=[Depends(require_roles(["team_lead", "admin"])), Depends(RateLimiter(times=5, seconds=60))] # Limit to 5 uploads per minute
)
async def bulk_upload_vkyc_records(
    upload_request: BulkUploadRequest,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Uploads a file (CSV/TXT) containing LAN IDs for bulk VKYC record creation.
    The file content should be Base64 encoded.
    Requires 'team_lead' or 'admin' role.
    """
    logger.info(f"User {current_user.username} initiating bulk upload for file: {upload_request.file_name}")
    return await vkyc_service.bulk_upload_records(upload_request)

@router.post(
    "/bulk-download",
    response_model=BulkDownloadResponse,
    summary="Initiate bulk download of VKYC recordings",
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid LAN IDs list"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden"}
    },
    dependencies=[Depends(require_roles(["user", "team_lead", "admin"])), Depends(RateLimiter(times=10, seconds=60))] # Limit to 10 bulk download requests per minute
)
async def bulk_download_vkyc_recordings(
    request: Request,
    download_request: BulkDownloadRequest,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Initiates a bulk download process for VKYC recordings based on a list of LAN IDs.
    Returns temporary download URLs for each successful record.
    Requires 'user', 'team_lead', or 'admin' role.
    """
    logger.info(f"User {current_user.username} initiating bulk download for {len(download_request.lan_ids)} LAN IDs.")
    # Construct base URL for download links
    base_url = str(request.base_url).rstrip('/')
    results = await vkyc_service.bulk_download_records(download_request.lan_ids, base_url)
    return BulkDownloadResponse(
        request_id=str(uuid.uuid4()), # Unique ID for this bulk request
        total_requested=len(download_request.lan_ids),
        results=results
    )

@router.get(
    "/{record_id}/download",
    summary="Download a specific VKYC recording file",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Record or file not found"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Forbidden access to file"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse, "description": "File download error"}
    },
    dependencies=[Depends(require_roles(["user", "team_lead", "admin"]))] # All authenticated users can download
)
async def download_vkyc_recording(
    record_id: int,
    vkyc_service: VKYCService = VKYCServiceDep,
    current_user: CurrentUser = Depends()
):
    """
    Downloads a specific VKYC recording file associated with a record ID.
    This endpoint streams the file content.
    Requires 'user', 'team_lead', or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to download recording for record ID: {record_id}")
    try:
        record = await vkyc_service.get_record_by_id(record_id)
        file_content = await vkyc_service.simulate_nfs_file_download(record.file_path)

        # Determine content type (simplified, could use mimetypes.guess_type)
        content_type = "video/mp4" if record.file_path.endswith(".mp4") else "application/octet-stream"
        file_name = os.path.basename(record.file_path)

        logger.info(f"Streaming file {file_name} for record ID {record_id}")
        return StreamingResponse(
            io.BytesIO(file_content),
            media_type=content_type,
            headers={"Content-Disposition": f"attachment; filename={file_name}"}
        )
    except NotFoundException as e:
        raise e # Re-raise custom exception for global handler
    except Exception as e:
        logger.error(f"Failed to download file for record ID {record_id}: {e}")
        raise InternalServerErrorException(detail=f"Failed to download file: {e}")