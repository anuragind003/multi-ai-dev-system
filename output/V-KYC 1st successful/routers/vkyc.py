import logging
import os
from typing import List
from fastapi import APIRouter, Depends, Query, status, BackgroundTasks, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import FileResponse

from database import get_db
from schemas import (
    VKYCSearchParams, VKYCRecordingInDB, BulkUploadRequest,
    BulkDownloadRequest, BulkOperationResponse, ErrorResponse
)
from services import vkyc_recording_service
from middleware.auth import get_current_user, UserInDB
from utils.exceptions import NotFoundException, ValidationException, CustomHTTPException
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/vkyc/recordings",
    response_model=List[VKYCRecordingInDB],
    summary="Search and filter VKYC recordings",
    description="Retrieve a list of VKYC recordings based on various search criteria. Supports pagination.",
    responses={
        200: {"description": "Successfully retrieved recordings."},
        400: {"model": ErrorResponse, "description": "Invalid search parameters."},
        401: {"model": ErrorResponse, "description": "Unauthorized access."},
        403: {"model": ErrorResponse, "description": "Forbidden access."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
async def search_vkyc_recordings(
    search_params: VKYCSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user), # Requires authentication
):
    """
    Search VKYC recordings by LAN ID, date range, status, and active status.
    Supports pagination with `skip` and `limit`.
    """
    logger.info(f"User {current_user.username} searching VKYC recordings with params: {search_params.model_dump()}")
    # Example authorization: Only users with 'viewer' or 'admin' role can search
    if "viewer" not in current_user.roles and "admin" not in current_user.roles:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Permission Denied",
            detail="You do not have permission to search recordings."
        )

    recordings = await vkyc_recording_service.search_recordings(db, search_params)
    return recordings

@router.get(
    "/vkyc/recordings/{lan_id}/download",
    summary="Download a single VKYC recording",
    description="Download a specific VKYC recording file by its LAN ID. Streams the file from NFS.",
    responses={
        200: {"description": "Successfully streamed the recording file.", "content": {"video/mp4": {}}},
        404: {"model": ErrorResponse, "description": "Recording not found."},
        401: {"model": ErrorResponse, "description": "Unauthorized access."},
        403: {"model": ErrorResponse, "description": "Forbidden access."},
        500: {"model": ErrorResponse, "description": "Internal server error (e.g., NFS error)."},
    },
)
async def download_vkyc_recording(
    lan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user), # Requires authentication
):
    """
    Download a VKYC recording file.
    """
    logger.info(f"User {current_user.username} requesting download for LAN ID: {lan_id}")
    # Example authorization: Only users with 'downloader' or 'admin' role can download
    if "downloader" not in current_user.roles and "admin" not in current_user.roles:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Permission Denied",
            detail="You do not have permission to download recordings."
        )

    return await vkyc_recording_service.get_recording_file(db, lan_id)

@router.post(
    "/vkyc/recordings/bulk-upload",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Bulk upload VKYC recording metadata",
    description="Upload a list of LAN IDs (e.g., from a CSV/TXT file) to process recording metadata.",
    responses={
        202: {"description": "Bulk upload initiated successfully."},
        400: {"model": ErrorResponse, "description": "Invalid input data or file format."},
        401: {"model": ErrorResponse, "description": "Unauthorized access."},
        403: {"model": ErrorResponse, "description": "Forbidden access."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
async def bulk_upload_vkyc_metadata(
    file: UploadFile = File(..., description="CSV or TXT file containing LAN IDs, one per line."),
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user), # Requires authentication
):
    """
    Accepts a CSV/TXT file with LAN IDs for bulk metadata processing.
    Each line in the file should contain a single LAN ID.
    """
    logger.info(f"User {current_user.username} initiating bulk metadata upload for file: {file.filename}")
    # Example authorization: Only users with 'uploader' or 'admin' role can bulk upload
    if "uploader" not in current_user.roles and "admin" not in current_user.roles:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Permission Denied",
            detail="You do not have permission to bulk upload metadata."
        )

    if file.content_type not in ["text/csv", "text/plain"]:
        raise ValidationException(
            message="Invalid file type",
            detail="Only CSV or plain text files are accepted for bulk upload."
        )

    content = await file.read()
    lan_ids_raw = content.decode("utf-8").splitlines()
    lan_ids = [lan_id.strip() for lan_id in lan_ids_raw if lan_id.strip()]

    if not lan_ids:
        raise ValidationException(
            message="Empty file",
            detail="The uploaded file contains no valid LAN IDs."
        )

    # Validate LAN IDs using Pydantic schema
    try:
        bulk_request = BulkUploadRequest(lan_ids=lan_ids)
    except Exception as e:
        raise ValidationException(
            message="Invalid LAN ID format in file",
            detail=f"One or more LAN IDs in the file are malformed: {e}"
        )

    response = await vkyc_recording_service.process_bulk_upload(db, bulk_request.lan_ids)
    return response

@router.post(
    "/vkyc/recordings/bulk-download",
    response_model=BulkOperationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate bulk download of VKYC recordings",
    description=f"Initiate an asynchronous bulk download of up to {settings.MAX_BULK_DOWNLOAD_RECORDS} VKYC recordings. "
                "A link to the zipped file will be provided upon initiation.",
    responses={
        202: {"description": "Bulk download initiated successfully."},
        400: {"model": ErrorResponse, "description": "Invalid input data or too many records requested."},
        401: {"model": ErrorResponse, "description": "Unauthorized access."},
        403: {"model": ErrorResponse, "description": "Forbidden access."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
async def bulk_download_vkyc_recordings(
    request_body: BulkDownloadRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_user), # Requires authentication
):
    """
    Initiate a bulk download of VKYC recording files.
    The actual zipping and file preparation happens in a background task.
    """
    logger.info(f"User {current_user.username} initiating bulk download for {len(request_body.lan_ids)} LAN IDs.")
    # Example authorization: Only users with 'downloader' or 'admin' role can bulk download
    if "downloader" not in current_user.roles and "admin" not in current_user.roles:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Permission Denied",
            detail="You do not have permission to initiate bulk downloads."
        )

    response = await vkyc_recording_service.initiate_bulk_download(
        db, request_body.lan_ids, background_tasks
    )
    return response

@router.get(
    "/vkyc/recordings/bulk-download/status",
    summary="Check status or retrieve bulk download file",
    description="Check the status of a bulk download or retrieve the completed zip file.",
    responses={
        200: {"description": "Returns the zip file if ready, or status message."},
        404: {"model": ErrorResponse, "description": "File not found or download not initiated."},
        401: {"model": ErrorResponse, "description": "Unauthorized access."},
        403: {"model": ErrorResponse, "description": "Forbidden access."},
        500: {"model": ErrorResponse, "description": "Internal server error."},
    },
)
async def get_bulk_download_status(
    filename: str = Query(..., description="The filename of the bulk download zip file."),
    current_user: UserInDB = Depends(get_current_user), # Requires authentication
):
    """
    Endpoint to check the status of a bulk download or retrieve the completed file.
    """
    logger.info(f"User {current_user.username} checking bulk download status for file: {filename}")
    if "downloader" not in current_user.roles and "admin" not in current_user.roles:
        raise CustomHTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Permission Denied",
            detail="You do not have permission to access bulk downloads."
        )

    file_path = os.path.join(settings.BULK_DOWNLOAD_TEMP_DIR, filename)

    if not os.path.exists(file_path):
        raise NotFoundException(
            message="Bulk download file not found",
            detail="The requested bulk download file is not yet ready or does not exist. Please try again later."
        )

    # In a real system, you might also check if the file is complete and not still being written.
    # For simplicity, we assume if it exists, it's ready.
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/zip",
        background=BackgroundTasks([lambda: os.remove(file_path)]) # Clean up after download
    )