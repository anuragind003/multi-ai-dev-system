import os
from typing import List
from fastapi import APIRouter, Depends, status, Response, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import VKYCSearchRequest, VKYCSearchResponse, VKYCDownloadRequest, VKYCRecordResponse
from services import VKYCService, get_vkyc_service
from crud import VKYCCrud
from middleware.auth import get_current_user
from utils.logger import get_logger
from utils.exceptions import NotFoundException, FileOperationException, CustomValidationException
from middleware.security import limiter

logger = get_logger(__name__)

router = APIRouter()

# Dependency to get VKYCCrud instance
def get_vkyc_crud(db: AsyncSession = Depends(get_db)) -> VKYCCrud:
    return VKYCCrud(db)

# Dependency to get VKYCService instance
def get_vkyc_service_with_crud(
    crud: VKYCCrud = Depends(get_vkyc_crud)
) -> VKYCService:
    return get_vkyc_service(crud)

@router.post(
    "/search",
    response_model=VKYCSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Search VKYC Records",
    description="Searches for VKYC records based on various criteria with pagination.",
    responses={
        status.HTTP_200_OK: {"description": "Successfully retrieved VKYC records."},
        status.HTTP_400_BAD_REQUEST: {"model": dict, "description": "Invalid search parameters."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error."}
    }
)
@limiter.limit("100/minute") # Apply rate limit
async def search_vkyc_records(
    request: VKYCSearchRequest,
    vkyc_service: VKYCService = Depends(get_vkyc_service_with_crud),
    current_user: str = Depends(get_current_user) # Requires authentication
):
    """
    Endpoint to search VKYC records.
    - **lan_id**: Partial or full LAN ID.
    - **start_date**: Filter by upload date (from).
    - **end_date**: Filter by upload date (to).
    - **status**: Filter by record status.
    - **page**: Page number (default 1).
    - **page_size**: Records per page (default 10, max 100).
    """
    logger.info(f"User '{current_user}' searching VKYC records with params: {request.model_dump_json()}")
    records, total_records = await vkyc_service.search_vkyc_records(request)
    return VKYCSearchResponse(
        total_records=total_records,
        page=request.page,
        page_size=request.page_size,
        records=records
    )

@router.get(
    "/download/{lan_id}",
    status_code=status.HTTP_200_OK,
    summary="Download Single VKYC Record",
    description="Downloads a single VKYC recording file by its LAN ID.",
    responses={
        status.HTTP_200_OK: {"content": {"video/mp4": {}}, "description": "Successfully streamed the VKYC recording."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_404_NOT_FOUND: {"description": "VKYC record or file not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error during file operation."}
    }
)
@limiter.limit("60/minute") # Apply rate limit
async def download_single_vkyc_record(
    lan_id: str,
    vkyc_service: VKYCService = Depends(get_vkyc_service_with_crud),
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint to download a single VKYC recording file.
    - **lan_id**: The unique LAN ID of the record to download.
    """
    logger.info(f"User '{current_user}' requesting download for single LAN ID: {lan_id}")
    file_path, filename = await vkyc_service.download_single_vkyc_record(lan_id)
    
    # Use the NFSClient directly for streaming
    nfs_client = vkyc_service.nfs_client
    
    # Get file size for Content-Length header
    file_size = await nfs_client.get_file_size(file_path)

    return StreamingResponse(
        nfs_client.get_file_stream(file_path),
        media_type="video/mp4", # Assuming MP4, adjust as needed
        headers={
            "Content-Disposition": f"attachment; filename={filename}.mp4",
            "Content-Length": str(file_size)
        }
    )

@router.post(
    "/download/bulk",
    status_code=status.HTTP_200_OK,
    summary="Download Bulk VKYC Records",
    description="Initiates a bulk download of multiple VKYC recording files as a ZIP archive.",
    responses={
        status.HTTP_200_OK: {"content": {"application/zip": {}}, "description": "Successfully generated and streamed the ZIP archive."},
        status.HTTP_400_BAD_REQUEST: {"model": dict, "description": "Invalid LAN IDs or too many IDs provided."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error during bulk file operation."}
    }
)
@limiter.limit("10/hour") # Apply a stricter rate limit for bulk downloads
async def download_bulk_vkyc_records(
    request: VKYCDownloadRequest,
    background_tasks: BackgroundTasks,
    vkyc_service: VKYCService = Depends(get_vkyc_service_with_crud),
    current_user: str = Depends(get_current_user)
):
    """
    Endpoint to download multiple VKYC recording files as a ZIP archive.
    - **lan_ids**: A list of LAN IDs (max 10) to include in the bulk download.
    """
    logger.info(f"User '{current_user}' requesting bulk download for LAN IDs: {request.lan_ids}")
    
    # Validate input before processing
    if not request.lan_ids:
        raise CustomValidationException("No LAN IDs provided for bulk download.")
    if len(request.lan_ids) > 10:
        raise CustomValidationException("Maximum 10 LAN IDs allowed for bulk download.", errors=[{"loc": ["lan_ids"], "msg": "Too many IDs"}])

    zip_file_path = await vkyc_service.download_bulk_vkyc_records(request.lan_ids)

    # Add a background task to clean up the temporary zip file after it's sent
    background_tasks.add_task(os.remove, zip_file_path)
    logger.info(f"Generated zip file for bulk download: {zip_file_path}")

    return FileResponse(
        path=zip_file_path,
        media_type="application/zip",
        filename=os.path.basename(zip_file_path),
        headers={
            "Content-Disposition": f"attachment; filename={os.path.basename(zip_file_path)}"
        }
    )