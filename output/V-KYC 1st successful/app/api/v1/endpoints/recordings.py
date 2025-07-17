import logging
from fastapi import APIRouter, Depends, UploadFile, File, status, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from app.core.dependencies import get_current_active_user
from app.schemas.recording import BulkUploadResponse
from app.services.recording_service import RecordingService
from app.core.exceptions import FileProcessingException, InvalidInputException

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/recordings/bulk-upload",
    response_model=BulkUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk upload VKYC recording metadata",
    description="Uploads a CSV or TXT file containing a list of LAN IDs for VKYC recordings. "
                "The system will process these IDs, validate them, and store their metadata "
                "in the database, associating them with hypothetical NFS file paths. "
                "This endpoint is for metadata ingestion, not actual video file upload.",
    responses={
        status.HTTP_200_OK: {"description": "Bulk upload processed successfully."},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid file format or content."},
        status.HTTP_401_UNAUTHORIZED: {"description": "Not authenticated."},
        status.HTTP_403_FORBIDDEN: {"description": "Not authorized to perform this action."},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error during processing."}
    }
)
async def bulk_upload_recordings(
    file: UploadFile = File(..., description="CSV or TXT file containing LAN IDs, one per line or comma-separated."),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_active_user) # Requires authentication
):
    """
    Handles the bulk upload of VKYC recording metadata.
    """
    logger.info(f"User '{current_user['username']}' initiated bulk upload for file: {file.filename}")

    # Basic role check (example: only 'admin' or 'process_manager' can upload)
    # In a real system, roles would be more granular and managed.
    if current_user.get("role") not in ["admin", "process_manager"]:
        logger.warning(f"User '{current_user['username']}' (role: {current_user.get('role')}) attempted unauthorized bulk upload.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform bulk upload. Requires 'admin' or 'process_manager' role."
        )

    recording_service = RecordingService(db)
    try:
        response = await recording_service.bulk_upload_recordings(file)
        logger.info(f"Bulk upload for {file.filename} completed. Processed: {response.processed_records}, Failed: {response.failed_records}.")
        return response
    except InvalidInputException as e:
        logger.warning(f"Bulk upload failed due to invalid input for {file.filename}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.detail)
    except FileProcessingException as e:
        logger.error(f"File processing error during bulk upload for {file.filename}: {e.detail}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"File processing failed: {e.detail}")
    except Exception as e:
        logger.critical(f"Unhandled error during bulk upload for {file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during bulk upload.")