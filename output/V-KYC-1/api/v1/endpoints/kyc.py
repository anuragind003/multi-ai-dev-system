from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from database import get_db
from schemas import KYCRecordCreate, KYCRecordUpdate, KYCRecordResponse, BulkUploadRequest, BulkUploadResponse
from services.kyc_service import KYCService
from auth.dependencies import get_current_active_user, get_current_manager_or_admin_user, get_current_auditor_or_higher_user
from core.exceptions import KYCRecordNotFoundException, ForbiddenException, DuplicateEntryException
from models import User, UserRole, KYCStatus
import logging
import csv
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kyc")

@router.post(
    "/",
    response_model=KYCRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new KYC record",
    description="Creates a new KYC record. Requires AUDITOR, MANAGER, or ADMIN role."
)
async def create_kyc_record(
    kyc_in: KYCRecordCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_auditor_or_higher_user)]
):
    """
    Creates a new KYC record.
    The `uploaded_by_user_id` is automatically set to the current user's ID.
    """
    kyc_service = KYCService(db)
    try:
        new_record = await kyc_service.create_kyc_record(kyc_in, uploaded_by_user_id=current_user.id)
        logger.info(f"KYC record {new_record.id} created by user {current_user.username}.")
        return new_record
    except DuplicateEntryException as e:
        logger.warning(f"Failed to create KYC record: {e.detail}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error creating KYC record: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get(
    "/{record_id}",
    response_model=KYCRecordResponse,
    summary="Get KYC record by ID",
    description="Retrieves a specific KYC record by its ID. Requires AUDITOR, MANAGER, or ADMIN role."
)
async def get_kyc_record(
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_auditor_or_higher_user)]
):
    """
    Retrieves a KYC record by its ID.
    """
    kyc_service = KYCService(db)
    try:
        record = await kyc_service.get_kyc_record(record_id)
        logger.info(f"User {current_user.username} fetched KYC record {record_id}.")
        return record
    except KYCRecordNotFoundException as e:
        logger.warning(f"KYC record {record_id} not found: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)

@router.get(
    "/",
    response_model=List[KYCRecordResponse],
    summary="Get all KYC records",
    description="Retrieves a list of all KYC records, with optional filtering. Requires AUDITOR, MANAGER, or ADMIN role."
)
async def get_all_kyc_records(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_auditor_or_higher_user)],
    lan_id: Optional[str] = None,
    status: Optional[KYCStatus] = None,
    customer_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
):
    """
    Retrieves all KYC records, with optional filters for LAN ID, status, and customer name.
    Supports pagination.
    """
    kyc_service = KYCService(db)
    records = await kyc_service.get_all_kyc_records(
        lan_id=lan_id, status=status, customer_name=customer_name, skip=skip, limit=limit
    )
    logger.info(f"User {current_user.username} fetched {len(records)} KYC records.")
    return records

@router.put(
    "/{record_id}",
    response_model=KYCRecordResponse,
    summary="Update a KYC record",
    description="Updates an existing KYC record. Requires MANAGER or ADMIN role to change status or approved_by_user_id. Auditors can only update basic info."
)
async def update_kyc_record(
    record_id: int,
    kyc_update: KYCRecordUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_auditor_or_higher_user)]
):
    """
    Updates an existing KYC record.
    - Managers/Admins can update status and approved_by_user_id.
    - Auditors can only update basic fields (lan_id, customer_name, recording_date, file_path).
    """
    kyc_service = KYCService(db)
    try:
        # Check permissions for status/approval changes
        if (kyc_update.status is not None or kyc_update.approved_by_user_id is not None) and \
           current_user.role not in [UserRole.MANAGER, UserRole.ADMIN]:
            logger.warning(f"User {current_user.username} (Role: {current_user.role}) attempted unauthorized status/approval update for record {record_id}.")
            raise ForbiddenException(detail="Only Managers or Admins can change KYC record status or approval.")

        # If auditor, ensure they are not trying to update restricted fields
        if current_user.role == UserRole.AUDITOR:
            if kyc_update.status is not None or kyc_update.approved_by_user_id is not None:
                raise ForbiddenException(detail="Auditors cannot change KYC record status or approval.")
            # Ensure auditor is not trying to set approved_by_user_id to themselves
            if kyc_update.approved_by_user_id is not None and kyc_update.approved_by_user_id == current_user.id:
                 raise ForbiddenException(detail="Auditors cannot approve records.")

        updated_record = await kyc_service.update_kyc_record(
            record_id, kyc_update, current_user_id=current_user.id, current_user_role=current_user.role
        )
        logger.info(f"KYC record {record_id} updated by user {current_user.username}.")
        return updated_record
    except KYCRecordNotFoundException as e:
        logger.warning(f"KYC record {record_id} not found for update: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except ForbiddenException as e:
        logger.warning(f"Forbidden update attempt on KYC record {record_id}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=e.detail)
    except DuplicateEntryException as e:
        logger.warning(f"Failed to update KYC record {record_id}: {e.detail}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.detail)
    except Exception as e:
        logger.error(f"Error updating KYC record {record_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a KYC record",
    description="Deletes a KYC record by ID. Requires MANAGER or ADMIN role."
)
async def delete_kyc_record(
    record_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_manager_or_admin_user)]
):
    """
    Deletes a KYC record by its ID. Accessible only by MANAGER or ADMIN users.
    """
    kyc_service = KYCService(db)
    try:
        await kyc_service.delete_kyc_record(record_id)
        logger.info(f"KYC record {record_id} deleted by user {current_user.username}.")
        return {"message": "KYC record deleted successfully."}
    except KYCRecordNotFoundException as e:
        logger.warning(f"KYC record {record_id} not found for deletion: {e.detail}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.detail)
    except Exception as e:
        logger.error(f"Error deleting KYC record {record_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.post(
    "/bulk-upload",
    response_model=BulkUploadResponse,
    summary="Bulk upload KYC records via CSV",
    description="Uploads multiple KYC records from a CSV file. Requires AUDITOR, MANAGER, or ADMIN role."
)
async def bulk_upload_kyc_records(
    file: Annotated[UploadFile, File(description="CSV file containing KYC records")],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_auditor_or_higher_user)]
):
    """
    Handles bulk upload of KYC records from a CSV file.
    Expected CSV columns: lan_id, customer_name, recording_date, file_path.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are allowed.")

    content = await file.read()
    csv_file = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_file)

    records_to_create: List[BulkUploadRequest] = []
    for i, row in enumerate(reader):
        try:
            # Basic validation for required fields
            if not all(k in row and row[k] for k in ['lan_id', 'recording_date', 'file_path']):
                logger.warning(f"Skipping row {i+1} due to missing required fields: {row}")
                continue

            # Attempt to parse recording_date
            try:
                recording_date = datetime.fromisoformat(row['recording_date'].replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"Skipping row {i+1} due to invalid recording_date format: {row['recording_date']}")
                continue

            records_to_create.append(BulkUploadRequest(
                lan_id=row['lan_id'],
                customer_name=row.get('customer_name'),
                recording_date=recording_date,
                file_path=row['file_path']
            ))
        except Exception as e:
            logger.error(f"Error processing row {i+1} in bulk upload: {row} - {e}", exc_info=True)
            # Continue processing other rows

    if not records_to_create:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid records found in the CSV file.")

    kyc_service = KYCService(db)
    results = await kyc_service.bulk_upload_kyc_records(records_to_create, uploaded_by_user_id=current_user.id)
    logger.info(f"User {current_user.username} performed bulk upload: {results.successful_uploads} successful, {results.failed_uploads} failed.")
    return results