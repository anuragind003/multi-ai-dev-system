from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.schemas.bulk_download import BulkDownloadRequest, BulkDownloadResponse
from app.schemas.common import APIResponse
from app.services.bulk_download_service import BulkDownloadService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

@router.post(
    "/bulk-download",
    response_model=APIResponse[BulkDownloadResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate Bulk Download Request",
    description="Submits a list of LAN IDs to fetch VKYC recording metadata and check file existence. "
                "Returns a request ID to track the processing status. Max 10 LAN IDs per request.",
    tags=["Bulk Download"]
)
async def initiate_bulk_download(
    request_data: BulkDownloadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Authenticated user
):
    """
    Endpoint to initiate a bulk download request.
    """
    logger.info(f"User '{current_user['username']}' initiating bulk download for {len(request_data.lan_ids)} LAN IDs.")
    
    service = BulkDownloadService(db)
    response_data = await service.process_bulk_request(request_data, current_user['username'])
    
    return APIResponse(
        success=True,
        message="Bulk download request initiated successfully. Use the request ID to check status.",
        data=response_data
    )

@router.get(
    "/bulk-download/{request_id}",
    response_model=APIResponse[BulkDownloadResponse],
    summary="Get Bulk Download Request Status",
    description="Retrieves the status and detailed results for a specific bulk download request.",
    tags=["Bulk Download"]
)
async def get_bulk_download_status(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user) # Authenticated user
):
    """
    Endpoint to get the status of a bulk download request.
    """
    logger.info(f"User '{current_user['username']}' requesting status for bulk download ID: {request_id}")

    service = BulkDownloadService(db)
    response_data = await service.get_bulk_request_status(request_id)
    
    return APIResponse(
        success=True,
        message="Bulk download request status retrieved successfully.",
        data=response_data
    )