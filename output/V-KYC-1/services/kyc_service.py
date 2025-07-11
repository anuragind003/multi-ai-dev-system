from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from models import KYCRecord, KYCStatus, User, UserRole
from schemas import KYCRecordCreate, KYCRecordUpdate, BulkUploadRequest, BulkUploadResponse
from core.exceptions import KYCRecordNotFoundException, DuplicateEntryException
import logging
import asyncio # For simulating async operations

logger = logging.getLogger(__name__)

class KYCService:
    """
    Service layer for KYC record-related business logic.
    Handles CRUD operations and bulk uploads for KYC records.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_kyc_record(self, kyc_in: KYCRecordCreate, uploaded_by_user_id: int) -> KYCRecord:
        """
        Creates a new KYC record.

        Args:
            kyc_in (KYCRecordCreate): Pydantic model with KYC record details.
            uploaded_by_user_id (int): ID of the user uploading the record.

        Returns:
            KYCRecord: The newly created KYCRecord ORM object.

        Raises:
            DuplicateEntryException: If a record with the same file_path already exists.
        """
        # Check for duplicate file_path
        existing_record = await self.db.execute(
            select(KYCRecord).filter(KYCRecord.file_path == kyc_in.file_path)
        )
        if existing_record.scalar_one_or_none():
            raise DuplicateEntryException(f"A KYC record with file path '{kyc_in.file_path}' already exists.")

        db_kyc_record = KYCRecord(
            lan_id=kyc_in.lan_id,
            customer_name=kyc_in.customer_name,
            recording_date=kyc_in.recording_date,
            file_path=kyc_in.file_path,
            status=KYCStatus.PENDING, # Default status
            uploaded_by_user_id=uploaded_by_user_id
        )
        self.db.add(db_kyc_record)
        try:
            await self.db.commit()
            await self.db.refresh(db_kyc_record)
            logger.info(f"KYC record for LAN ID '{db_kyc_record.lan_id}' created by user {uploaded_by_user_id}.")
            return db_kyc_record
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error during KYC record creation: {e}", exc_info=True)
            raise DuplicateEntryException("A KYC record with this file path already exists.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error during KYC record creation: {e}", exc_info=True)
            raise

    async def get_kyc_record(self, record_id: int) -> KYCRecord:
        """
        Retrieves a single KYC record by its ID.

        Args:
            record_id (int): The ID of the KYC record.

        Returns:
            KYCRecord: The found KYCRecord ORM object.

        Raises:
            KYCRecordNotFoundException: If no record with the given ID is found.
        """
        result = await self.db.execute(
            select(KYCRecord).filter(KYCRecord.id == record_id)
        )
        kyc_record = result.scalar_one_or_none()
        if not kyc_record:
            raise KYCRecordNotFoundException(f"KYC record with ID {record_id} not found.")
        return kyc_record

    async def get_all_kyc_records(
        self,
        lan_id: Optional[str] = None,
        status: Optional[KYCStatus] = None,
        customer_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[KYCRecord]:
        """
        Retrieves all KYC records with optional filtering and pagination.
        """
        query = select(KYCRecord)
        if lan_id:
            query = query.filter(KYCRecord.lan_id.ilike(f"%{lan_id}%"))
        if status:
            query = query.filter(KYCRecord.status == status)
        if customer_name:
            query = query.filter(KYCRecord.customer_name.ilike(f"%{customer_name}%"))

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_kyc_record(
        self,
        record_id: int,
        kyc_update: KYCRecordUpdate,
        current_user_id: int,
        current_user_role: UserRole
    ) -> KYCRecord:
        """
        Updates an existing KYC record.

        Args:
            record_id (int): The ID of the KYC record to update.
            kyc_update (KYCRecordUpdate): Pydantic model with fields to update.
            current_user_id (int): ID of the user performing the update.
            current_user_role (UserRole): Role of the user performing the update.

        Returns:
            KYCRecord: The updated KYCRecord ORM object.

        Raises:
            KYCRecordNotFoundException: If the record is not found.
            DuplicateEntryException: If the updated file_path conflicts with an existing record.
        """
        db_record = await self.get_kyc_record(record_id) # This will raise if not found

        update_data = kyc_update.model_dump(exclude_unset=True)

        # Handle status and approved_by_user_id updates
        if "status" in update_data and update_data["status"] != db_record.status:
            # Only Managers/Admins can change status
            if current_user_role not in [UserRole.MANAGER, UserRole.ADMIN]:
                raise ForbiddenException("Only Managers or Admins can change KYC record status.")
            # If status is changing to APPROVED, set approved_by_user_id
            if update_data["status"] == KYCStatus.APPROVED:
                update_data["approved_by_user_id"] = current_user_id
            else:
                update_data["approved_by_user_id"] = None # Clear approver if status changes from approved

        # If approved_by_user_id is explicitly set, ensure user has permission
        if "approved_by_user_id" in update_data and update_data["approved_by_user_id"] is not None:
            if current_user_role not in [UserRole.MANAGER, UserRole.ADMIN]:
                raise ForbiddenException("Only Managers or Admins can set approved_by_user_id.")
            # Ensure the approver ID is valid (e.g., exists in User table) - omitted for brevity, but good practice

        # Check for duplicate file_path if it's being updated
        if "file_path" in update_data and update_data["file_path"] != db_record.file_path:
            existing_record_with_new_path = await self.db.execute(
                select(KYCRecord).filter(KYCRecord.file_path == update_data["file_path"], KYCRecord.id != record_id)
            )
            if existing_record_with_new_path.scalar_one_or_none():
                raise DuplicateEntryException(f"A KYC record with file path '{update_data['file_path']}' already exists.")

        stmt = update(KYCRecord).where(KYCRecord.id == record_id).values(**update_data)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            await self.db.refresh(db_record) # Refresh to get updated values
            logger.info(f"KYC record {record_id} updated by user {current_user_id}.")
            return db_record
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error during KYC record update: {e}", exc_info=True)
            raise DuplicateEntryException("A KYC record with this file path already exists.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error during KYC record update: {e}", exc_info=True)
            raise

    async def delete_kyc_record(self, record_id: int):
        """
        Deletes a KYC record by its ID.

        Args:
            record_id (int): The ID of the KYC record to delete.

        Raises:
            KYCRecordNotFoundException: If no record with the given ID is found.
        """
        # Check if record exists first
        existing_record = await self.get_kyc_record(record_id) # This will raise if not found

        stmt = delete(KYCRecord).where(KYCRecord.id == record_id)
        try:
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"KYC record {record_id} deleted.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting KYC record {record_id}: {e}", exc_info=True)
            raise

    async def bulk_upload_kyc_records(self, records_in: List[BulkUploadRequest], uploaded_by_user_id: int) -> BulkUploadResponse:
        """
        Handles bulk creation of KYC records.

        Args:
            records_in (List[BulkUploadRequest]): List of Pydantic models for KYC records.
            uploaded_by_user_id (int): ID of the user performing the bulk upload.

        Returns:
            BulkUploadResponse: Summary of successful and failed uploads.
        """
        total_records = len(records_in)
        successful_uploads = 0
        failed_uploads = 0
        details = []

        for i, record_data in enumerate(records_in):
            try:
                # Simulate NFS interaction (e.g., check if file exists on NFS)
                # In a real scenario, this would involve network calls to the NFS server.
                # For now, we'll just assume the file path is valid.
                await asyncio.sleep(0.01) # Simulate I/O delay

                # Check for duplicate file_path before attempting to create
                existing_record = await self.db.execute(
                    select(KYCRecord).filter(KYCRecord.file_path == record_data.file_path)
                )
                if existing_record.scalar_one_or_none():
                    raise DuplicateEntryException(f"File path '{record_data.file_path}' already exists.")

                db_kyc_record = KYCRecord(
                    lan_id=record_data.lan_id,
                    customer_name=record_data.customer_name,
                    recording_date=record_data.recording_date,
                    file_path=record_data.file_path,
                    status=KYCStatus.PENDING,
                    uploaded_by_user_id=uploaded_by_user_id
                )
                self.db.add(db_kyc_record)
                await self.db.flush() # Flush to detect integrity errors early without committing
                await self.db.refresh(db_kyc_record) # Refresh to get ID if needed
                successful_uploads += 1
                details.append({"lan_id": record_data.lan_id, "status": "success", "message": "Record created", "id": db_kyc_record.id})
                logger.info(f"Bulk upload: Successfully processed LAN ID '{record_data.lan_id}'.")
            except DuplicateEntryException as e:
                failed_uploads += 1
                details.append({"lan_id": record_data.lan_id, "status": "failed", "message": e.detail})
                logger.warning(f"Bulk upload: Failed to process LAN ID '{record_data.lan_id}' due to duplicate: {e.detail}")
            except Exception as e:
                failed_uploads += 1
                details.append({"lan_id": record_data.lan_id, "status": "failed", "message": f"Processing error: {e}"})
                logger.error(f"Bulk upload: Unexpected error processing LAN ID '{record_data.lan_id}': {e}", exc_info=True)
            finally:
                # Rollback individual record if failed, but continue for others
                # For bulk operations, it's often better to collect errors and commit successful ones in a batch
                # Or, if atomicity is critical, wrap the entire loop in a single transaction and rollback on *any* error.
                # Here, we're doing a "best effort" approach.
                pass # No explicit rollback per item, rely on final commit/rollback

        try:
            await self.db.commit() # Commit all successfully added records
            logger.info(f"Bulk upload transaction committed. Total: {total_records}, Success: {successful_uploads}, Failed: {failed_uploads}.")
        except Exception as e:
            await self.db.rollback() # Rollback everything if commit fails
            logger.error(f"Final commit failed for bulk upload: {e}", exc_info=True)
            # Mark all successful as failed if the final commit fails
            for detail in details:
                if detail["status"] == "success":
                    detail["status"] = "failed"
                    detail["message"] = f"Transaction failed: {e}"
            successful_uploads = 0
            failed_uploads = total_records # All failed if commit fails

        return BulkUploadResponse(
            total_records=total_records,
            successful_uploads=successful_uploads,
            failed_uploads=failed_uploads,
            details=details
        )