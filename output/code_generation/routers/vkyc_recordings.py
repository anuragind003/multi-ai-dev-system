from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime
import csv
import io

from database import get_db
from schemas import VKYCRecordingCreate, VKYCRecordingResponse, VKYCSearchFilter, BulkDownloadRequest, VKYCRecordingUpdate
from services import vkyc_recording_service
from auth import require_team_lead_or_higher, require_process_manager_or_admin, require_admin
from utils.errors import NotFoundException, BadRequestException, ConflictException
from utils.logger import logger

router = APIRouter(prefix="/vkyc", tags=["VKYC Recordings"])

@router.post(
    "/recordings",
    response_model=VKYCRecordingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new VKYC recording metadata (Process Manager/Admin only)"
)
async def create_vkyc_recording(
    recording_in: VKYCRecordingCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_process_manager_or_admin)
):
    """
    Adds metadata for a new VKYC recording.
    Requires 'process_manager' or 'admin' role.
    - **lan_id**: Unique LAN ID for the recording.
    - **file_path**: Full path to the recording file on the NFS server.
    - **file_name**: Original name of the recording file.
    - **recording_date**: Optional actual date/time of recording.
    - **size_bytes**: Optional size of the file in bytes.
    - **metadata_json**: Optional additional metadata as JSON string.
    """
    logger.info(f"User {current_user.username} attempting to create recording metadata for LAN ID: {recording_in.lan_id}")
    try:
        new_recording = await vkyc_recording_service.create_recording(db, recording_in)
        logger.info(f"Recording metadata for LAN ID {new_recording.lan_id} created successfully.")
        return new_recording
    except ConflictException as e:
        logger.warning(f"Failed to create recording metadata: {e.detail}")
        raise e
    except BadRequestException as e:
        logger.warning(f"Failed to create recording metadata due to bad request: {e.detail}")
        raise e

@router.get(
    "/recordings/{lan_id}",
    response_model=VKYCRecordingResponse,
    summary="Get VKYC recording metadata by LAN ID (Team Lead or higher)"
)
async def get_vkyc_recording(
    lan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_team_lead_or_higher)
):
    """
    Retrieves the metadata for a specific VKYC recording by its LAN ID.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    logger.info(f"User {current_user.username} fetching recording metadata for LAN ID: {lan_id}")
    try:
        recording = await vkyc_recording_service.get_recording_by_lan_id(db, lan_id)
        return recording
    except NotFoundException as e:
        logger.warning(f"Recording metadata not found for LAN ID {lan_id}: {e.detail}")
        raise e

@router.put(
    "/recordings/{lan_id}",
    response_model=VKYCRecordingResponse,
    summary="Update VKYC recording metadata (Process Manager/Admin only)"
)
async def update_vkyc_recording(
    lan_id: str,
    recording_in: VKYCRecordingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_process_manager_or_admin)
):
    """
    Updates the metadata for an existing VKYC recording.
    Requires 'process_manager' or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to update recording metadata for LAN ID: {lan_id}")
    try:
        updated_recording = await vkyc_recording_service.update_recording(db, lan_id, recording_in)
        logger.info(f"Recording metadata for LAN ID {lan_id} updated successfully.")
        return updated_recording
    except NotFoundException as e:
        logger.warning(f"Failed to update recording metadata: {e.detail}")
        raise e

@router.delete(
    "/recordings/{lan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete VKYC recording metadata (Admin only)"
)
async def delete_vkyc_recording(
    lan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_admin)
):
    """
    Deletes the metadata for a VKYC recording.
    Note: This only deletes the metadata, not the actual file on NFS.
    Requires 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to delete recording metadata for LAN ID: {lan_id}")
    try:
        await vkyc_recording_service.delete_recording(db, lan_id)
        logger.info(f"Recording metadata for LAN ID {lan_id} deleted successfully.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except NotFoundException as e:
        logger.warning(f"Failed to delete recording metadata: {e.detail}")
        raise e

@router.get(
    "/search",
    response_model=List[VKYCRecordingResponse],
    summary="Search and filter VKYC recordings (Team Lead or higher)"
)
async def search_vkyc_recordings(
    lan_id: Optional[str] = Query(None, description="Partial or full LAN ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by recording date from (YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[datetime] = Query(None, description="Filter by recording date to (YYYY-MM-DDTHH:MM:SS)"),
    status: Optional[VKYCRecordingStatus] = Query(None, description="Filter by recording status"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_team_lead_or_higher)
):
    """
    Searches and filters VKYC recording metadata based on various criteria.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    logger.info(f"User {current_user.username} performing search with filters: LAN ID={lan_id}, Start Date={start_date}, End Date={end_date}, Status={status}")
    filters = VKYCSearchFilter(
        lan_id=lan_id,
        start_date=start_date,
        end_date=end_date,
        status=status,
        limit=limit,
        offset=offset
    )
    recordings = await vkyc_recording_service.search_recordings(db, filters)
    logger.info(f"Found {len(recordings)} recordings for search criteria.")
    return recordings

@router.get(
    "/download/{lan_id}",
    summary="Download a VKYC recording file (Team Lead or higher)",
    response_description="Binary stream of the recording file"
)
async def download_vkyc_recording(
    lan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_team_lead_or_higher)
):
    """
    Downloads a specific VKYC recording file by its LAN ID.
    The file is streamed directly from the NFS server.
    Requires 'team_lead', 'process_manager', or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to download file for LAN ID: {lan_id}")
    try:
        return await vkyc_recording_service.stream_recording_file(db, lan_id)
    except NotFoundException as e:
        logger.warning(f"Download failed for LAN ID {lan_id}: {e.detail}")
        raise e
    except BadRequestException as e:
        logger.error(f"Download failed for LAN ID {lan_id} due to bad request: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during download for LAN ID {lan_id}.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during file download.")

@router.post(
    "/bulk-download",
    summary="Initiate bulk download of VKYC recordings (Process Manager/Admin only)",
    response_model=dict # In a real app, this would return a job ID
)
async def bulk_download_vkyc_recordings(
    request: BulkDownloadRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_process_manager_or_admin)
):
    """
    Initiates a bulk download process for multiple VKYC recordings based on a list of LAN IDs.
    Currently, this is a simulated process. In a production environment, this would
    likely trigger a background job (e.g., using Celery) that zips files and provides a download link.
    Maximum 10 LAN IDs per request.
    Requires 'process_manager' or 'admin' role.
    """
    logger.info(f"User {current_user.username} initiating bulk download for {len(request.lan_ids)} LAN IDs.")
    try:
        result = await vkyc_recording_service.process_bulk_download(db, request.lan_ids)
        return result
    except NotFoundException as e:
        logger.warning(f"Bulk download failed: {e.detail}")
        raise e
    except Exception as e:
        logger.exception(f"An unexpected error occurred during bulk download initiation.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during bulk download initiation.")

@router.post(
    "/upload-metadata-csv",
    status_code=status.HTTP_201_CREATED,
    summary="Upload VKYC recording metadata via CSV (Process Manager/Admin only)",
    response_model=dict
)
async def upload_vkyc_metadata_csv(
    file: UploadFile = File(..., description="CSV file containing VKYC recording metadata"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_process_manager_or_admin)
):
    """
    Uploads VKYC recording metadata from a CSV file.
    The CSV should have columns matching `VKYCRecordingCreate` schema fields (e.g., lan_id, file_path, file_name, recording_date, size_bytes, metadata_json).
    Requires 'process_manager' or 'admin' role.
    """
    logger.info(f"User {current_user.username} attempting to upload metadata CSV: {file.filename}")
    if not file.filename.endswith(".csv"):
        raise BadRequestException(detail="Only CSV files are allowed.")

    contents = await file.read()
    sio = io.StringIO(contents.decode('utf-8'))
    reader = csv.DictReader(sio)

    processed_count = 0
    failed_entries = []

    for i, row in enumerate(reader):
        try:
            # Convert types as necessary, e.g., recording_date from string to datetime
            if 'recording_date' in row and row['recording_date']:
                row['recording_date'] = datetime.fromisoformat(row['recording_date'])
            if 'size_bytes' in row and row['size_bytes']:
                row['size_bytes'] = int(row['size_bytes'])
            if 'status' in row and row['status']:
                row['status'] = VKYCRecordingStatus(row['status'])

            recording_data = VKYCRecordingCreate(**row)
            await vkyc_recording_service.create_recording(db, recording_data)
            processed_count += 1
        except Exception as e:
            logger.error(f"Failed to process row {i+1} from CSV: {row}. Error: {e}")
            failed_entries.append({"row_number": i + 1, "data": row, "error": str(e)})
            # Rollback transaction for this specific entry if needed, or handle in service layer
            # For bulk operations, it's often better to collect failures and report.

    if failed_entries:
        raise HTTPException(
            status_code=status.HTTP_207_MULTI_STATUS,
            detail={
                "message": f"Processed {processed_count} records. {len(failed_entries)} failed.",
                "failed_entries": failed_entries
            }
        )
    logger.info(f"Successfully processed {processed_count} records from CSV.")
    return {"message": f"Successfully processed {processed_count} records."}