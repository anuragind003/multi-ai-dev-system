from fastapi import APIRouter, Depends, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from schemas.bulk_request import BulkRequestCreate, BulkRequestResponse
from schemas.common import HTTPError
from services.bulk_request_service import BulkRequestService
from core.dependencies import get_db, get_current_user, rate_limiter_dependency, CurrentUser
from core.exceptions import NotFoundException, BadRequestException, InternalServerError
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/bulk-requests",
    tags=["Bulk Requests"],
    dependencies=[Depends(rate_limiter_dependency)] # Apply rate limiting to all endpoints in this router
)

@router.post(
    "/",
    response_model=BulkRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a new bulk request for LAN IDs",
    description="Accepts a list of LAN IDs and initiates background processing to retrieve their status. Returns the initial request details.",
    responses={
        status.HTTP_202_ACCEPTED: {"description": "Bulk request accepted for processing."},
        status.HTTP_400_BAD_REQUEST: {"model": HTTPError, "description": "Invalid input or too many LAN IDs."},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Authentication required."},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation error."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal server error."}
    }
)
async def create_bulk_request(
    request_data: BulkRequestCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BulkRequestResponse:
    """
    Endpoint to submit a new bulk request.
    The request is immediately saved, and processing is initiated in the background.
    """
    logger.info(f"User {current_user.id} submitting bulk request for {len(request_data.lan_ids)} LAN IDs.")
    
    # Input validation is handled by Pydantic automatically via BulkRequestCreate schema
    # Additional business logic validation can go here if needed (e.g., check if LAN IDs are valid format)
    if not request_data.lan_ids:
        raise BadRequestException(detail="At least one LAN ID is required for a bulk request.")

    try:
        service = BulkRequestService(db)
        bulk_request = await service.create_bulk_request(request_data, current_user.id)
        logger.info(f"Bulk request {bulk_request.id} successfully initiated.")
        return bulk_request
    except BadRequestException as e:
        raise e # Re-raise specific exception
    except Exception as e:
        logger.error(f"Error creating bulk request for user {current_user.id}: {e}")
        raise InternalServerError(detail="Failed to create bulk request.")

@router.get(
    "/{request_id}",
    response_model=BulkRequestResponse,
    summary="Get status and results of a bulk request",
    description="Retrieves the overall status of a bulk request and the processing status for each individual LAN ID.",
    responses={
        status.HTTP_200_OK: {"description": "Bulk request details retrieved successfully."},
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Authentication required."},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Bulk request not found."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": HTTPError, "description": "Internal server error."}
    }
)
async def get_bulk_request_status(
    request_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> BulkRequestResponse:
    """
    Endpoint to retrieve the status of a specific bulk request by its ID.
    """
    logger.info(f"User {current_user.id} requesting status for bulk request {request_id}.")
    try:
        service = BulkRequestService(db)
        bulk_request = await service.get_bulk_request_by_id(request_id)
        
        # Optional: Add authorization check here if only the owner or specific roles can view
        # if bulk_request.user_id != current_user.id and not current_user.is_admin:
        #     raise ForbiddenException(detail="You do not have permission to view this request.")

        logger.info(f"Bulk request {request_id} status retrieved successfully.")
        return bulk_request
    except NotFoundException as e:
        raise e # Re-raise specific exception
    except Exception as e:
        logger.error(f"Error retrieving bulk request {request_id} for user {current_user.id}: {e}")
        raise InternalServerError(detail="Failed to retrieve bulk request status.")