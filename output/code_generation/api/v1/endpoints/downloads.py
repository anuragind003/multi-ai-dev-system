from fastapi import APIRouter, Depends, status, Body
from fastapi.responses import JSONResponse
from fastapi_limiter.depends import RateLimiter
from typing import List
from uuid import UUID

from schemas import BulkDownloadRequest, DownloadRequestResponse, User
from services.download_service import DownloadService, get_download_service
from middleware.auth import get_current_user, RoleChecker
from utils.logger import logger
from utils.exceptions import CustomValidationException, NotFoundException, ServiceUnavailableException

router = APIRouter()

# Define roles for authorization
# Assuming 'admin' can do anything, 'process_manager' can initiate/view, 'team_lead' can view
REQUIRED_ROLES_BULK_DOWNLOAD = ["admin", "process_manager"]
REQUIRED_ROLES_VIEW_STATUS = ["admin", "process_manager", "team_lead"]

@router.post(
    "/downloads/bulk",
    response_model=DownloadRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate a bulk download request",
    description="Processes a list of LAN IDs to check file existence and metadata. Max 10 LAN IDs per request.",
    dependencies=[
        Depends(RateLimiter(times=10, seconds=60)), # 10 requests per minute per user/IP
        Depends(RoleChecker(REQUIRED_ROLES_BULK_DOWNLOAD))
    ]
)
async def initiate_bulk_download(
    request: BulkDownloadRequest = Body(..., description="List of LAN IDs for bulk download."),
    current_user: User = Depends(get_current_user),
    download_service: DownloadService = Depends(get_download_service)
):
    """
    Initiates a bulk download request for VKYC recordings.
    
    - **lan_ids**: A list of LAN IDs (max 10) to process.
    
    The API will:
    1. Validate input LAN IDs.
    2. Fetch/create metadata for each LAN ID.
    3. Check the existence of associated files on the NFS server.
    4. Return a summary of the request status and details for each file.
    """
    logger.info(f"User '{current_user.username}' initiating bulk download for {len(request.lan_ids)} LAN IDs.")
    try:
        response = download_service.process_bulk_download_request(request, current_user.username)
        return response
    except CustomValidationException as e:
        logger.warning(f"Validation error for bulk download by {current_user.username}: {e.detail}")
        raise e
    except ServiceUnavailableException as e:
        logger.error(f"Service unavailable during bulk download by {current_user.username}: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error during bulk download by {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request."
        )

@router.get(
    "/downloads/{request_id}",
    response_model=DownloadRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get bulk download request status",
    description="Retrieves the current status and details of a previously initiated bulk download request.",
    dependencies=[
        Depends(RateLimiter(times=30, seconds=60)), # 30 requests per minute per user/IP
        Depends(RoleChecker(REQUIRED_ROLES_VIEW_STATUS))
    ]
)
async def get_bulk_download_status(
    request_id: UUID,
    current_user: User = Depends(get_current_user),
    download_service: DownloadService = Depends(get_download_service)
):
    """
    Retrieves the status and detailed information for a specific bulk download request.
    
    - **request_id**: The unique identifier (UUID) of the bulk download request.
    """
    logger.info(f"User '{current_user.username}' requesting status for download ID: {request_id}")
    try:
        response = download_service.get_download_request_status(str(request_id))
        return response
    except NotFoundException as e:
        logger.warning(f"Download request {request_id} not found for user {current_user.username}: {e.detail}")
        raise e
    except CustomValidationException as e:
        logger.warning(f"Validation error for download request ID {request_id} by {current_user.username}: {e.detail}")
        raise e
    except ServiceUnavailableException as e:
        logger.error(f"Service unavailable while fetching status for {request_id} by {current_user.username}: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"Unhandled error fetching status for download request {request_id} by {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving request status."
        )