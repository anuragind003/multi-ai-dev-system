from fastapi import APIRouter, Depends, UploadFile, File, Query, status, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from services import VKYCRecordingService
from schemas import VKYCRecordingCreate, VKYCRecordingResponse, CSVUploadResponse, VKYCRecordingUpdate
from models import VKYCRecordingStatus
from middleware.auth import APIKeyAuth
from utils.exceptions import NotFoundException, InvalidInputException, ConflictException
from utils.logger import log

router = APIRouter(
    prefix="/vkyc-recordings",
    tags=["VKYC Recordings"],
    dependencies=[Depends(APIKeyAuth)], # Apply API Key authentication to all endpoints in this router
    responses={401: {"description": "Unauthorized"}, 403: {"description": "Forbidden"}}
)

@router.post(
    "/upload-csv",
    response_model=CSVUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload VKYC recording metadata via CSV",
    description="Ingests VKYC recording metadata from a CSV file. "
                "Expected columns: `lan_id`, `recording_date` (YYYY-MM-DD), `file_path`. "
                "Optional column: `metadata_json` (JSON string)."
)
async def upload_vkyc_metadata_csv(
    file: UploadFile = File(..., description="CSV file containing VKYC recording metadata"),
    db: Session = Depends(get_db)
):
    """
    Handles the upload of a CSV file containing VKYC recording metadata.
    Parses the CSV, validates records, and performs bulk ingestion into the database.
    """
    if not file.filename.endswith(".csv"):
        log.warning(f"Invalid file format uploaded: {file.filename}. Only CSV files are allowed.")
        raise InvalidInputException(detail="Only CSV files are allowed.")

    try:
        csv_content = (await file.read()).decode("utf-8")
        service = VKYCRecordingService(db)
        response = service.ingest_csv_metadata(csv_content)
        log.info(f"CSV upload processed for {file.filename}. Success: {response.successfully_ingested}, Failed: {response.failed_to_ingest}")
        return response
    except InvalidInputException as e:
        log.error(f"Validation error during CSV upload: {e.detail}")
        raise e
    except Exception as e:
        log.exception(f"Failed to process CSV upload for {file.filename}: {e}")
        raise status.HTTP_500_INTERNAL_SERVER_ERROR(detail="Failed to process CSV file.")

@router.get(
    "/",
    response_model=List[VKYCRecordingResponse],
    summary="List all VKYC recordings",
    description="Retrieves a paginated list of VKYC recording metadata. Can be filtered by status."
)
async def list_vkyc_recordings(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    status: Optional[VKYCRecordingStatus] = Query(None, description="Filter by recording status"),
    db: Session = Depends(get_db)
):
    """
    Retrieves a list of VKYC recording metadata entries from the database.
    Supports pagination and filtering by status.
    """
    service = VKYCRecordingService(db)
    recordings = service.list_recordings(skip=skip, limit=limit, status=status)
    log.info(f"Retrieved {len(recordings)} VKYC recordings with skip={skip}, limit={limit}, status={status}")
    return recordings

@router.get(
    "/{lan_id}",
    response_model=VKYCRecordingResponse,
    summary="Get VKYC recording by LAN ID",
    description="Retrieves detailed metadata for a single VKYC recording using its LAN ID."
)
async def get_vkyc_recording_by_lan_id(
    lan_id: str = Query(..., min_length=5, max_length=50, description="The LAN ID of the VKYC recording"),
    db: Session = Depends(get_db)
):
    """
    Retrieves a single VKYC recording entry by its unique LAN ID.
    """
    service = VKYCRecordingService(db)
    try:
        recording = service.get_recording_details(lan_id)
        log.info(f"Retrieved VKYC recording for LAN ID: {lan_id}")
        return recording
    except NotFoundException as e:
        log.warning(f"VKYC recording not found for LAN ID: {lan_id}")
        raise e

@router.put(
    "/{lan_id}",
    response_model=VKYCRecordingResponse,
    summary="Update VKYC recording status",
    description="Updates the status or other metadata of an existing VKYC recording by its LAN ID."
)
async def update_vkyc_recording(
    lan_id: str = Query(..., min_length=5, max_length=50, description="The LAN ID of the VKYC recording to update"),
    recording_update: VKYCRecordingUpdate = ...,
    db: Session = Depends(get_db)
):
    """
    Updates an existing VKYC recording entry identified by its LAN ID.
    """
    service = VKYCRecordingService(db)
    try:
        updated_recording = service.crud.update_recording(lan_id, recording_update)
        log.info(f"Updated VKYC recording for LAN ID: {lan_id}")
        return VKYCRecordingResponse.model_validate(updated_recording)
    except NotFoundException as e:
        log.warning(f"Attempted to update non-existent VKYC recording for LAN ID: {lan_id}")
        raise e
    except Exception as e:
        log.exception(f"Failed to update VKYC recording for LAN ID {lan_id}: {e}")
        raise status.HTTP_500_INTERNAL_SERVER_ERROR(detail="Failed to update VKYC recording.")

@router.delete(
    "/{lan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete VKYC recording",
    description="Deletes a VKYC recording entry by its LAN ID."
)
async def delete_vkyc_recording(
    lan_id: str = Query(..., min_length=5, max_length=50, description="The LAN ID of the VKYC recording to delete"),
    db: Session = Depends(get_db)
):
    """
    Deletes a VKYC recording entry from the database using its LAN ID.
    Returns 204 No Content on successful deletion.
    """
    service = VKYCRecordingService(db)
    try:
        service.delete_recording_entry(lan_id)
        log.info(f"Deleted VKYC recording for LAN ID: {lan_id}")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        log.warning(f"Attempted to delete non-existent VKYC recording for LAN ID: {lan_id}")
        raise e
    except Exception as e:
        log.exception(f"Failed to delete VKYC recording for LAN ID {lan_id}: {e}")
        raise status.HTTP_500_INTERNAL_SERVER_ERROR(detail="Failed to delete VKYC recording.")