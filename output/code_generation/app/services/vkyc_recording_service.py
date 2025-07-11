import csv
import io
from datetime import datetime
from typing import List, Optional, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.vkyc_recording import VKYCRecording
from app.schemas.vkyc_recording import VKYCRecordingCreate, VKYCRecordingUpdate, CSVUploadResult
from app.core.exceptions import NotFoundException, ConflictException, UnprocessableEntityException, InternalServerErrorException

logger = logging.getLogger(__name__)

class VKYCRecordingService:
    """
    Service layer for VKYC recording metadata operations.
    Handles business logic, database interactions, and error handling.
    """
    def __init__(self, db: Session):
        self.db = db

    def create_recording(self, recording_data: VKYCRecordingCreate, uploaded_by: str) -> VKYCRecording:
        """
        Creates a new VKYC recording entry in the database.
        Raises ConflictException if LAN ID already exists.
        """
        existing_record = self.db.query(VKYCRecording).filter(VKYCRecording.lan_id == recording_data.lan_id).first()
        if existing_record:
            logger.warning(f"Attempted to create duplicate LAN ID: {recording_data.lan_id}")
            raise ConflictException(detail=f"VKYC recording with LAN ID '{recording_data.lan_id}' already exists.")

        db_recording = VKYCRecording(
            **recording_data.model_dump(),
            uploaded_by=uploaded_by
        )
        try:
            self.db.add(db_recording)
            self.db.commit()
            self.db.refresh(db_recording)
            logger.info(f"Created VKYC recording with ID: {db_recording.id}, LAN ID: {db_recording.lan_id}")
            return db_recording
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create VKYC recording for LAN ID {recording_data.lan_id}: {e}", exc_info=True)
            raise InternalServerErrorException(detail="Failed to create VKYC recording due to a database error.") from e

    def get_recording_by_id(self, recording_id: int) -> VKYCRecording:
        """
        Retrieves a VKYC recording by its database ID.
        Raises NotFoundException if record does not exist.
        """
        record = self.db.query(VKYCRecording).filter(VKYCRecording.id == recording_id).first()
        if not record:
            logger.warning(f"VKYC recording with ID {recording_id} not found.")
            raise NotFoundException(detail=f"VKYC recording with ID {recording_id} not found.")
        return record

    def get_recordings(
        self,
        lan_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[VKYCRecording], int]:
        """
        Retrieves a list of VKYC recordings with optional filters and pagination.
        Returns a tuple of (list of records, total count).
        """
        query = self.db.query(VKYCRecording)

        if lan_id:
            query = query.filter(VKYCRecording.lan_id.ilike(f"%{lan_id}%"))
        if status:
            query = query.filter(VKYCRecording.status == status)
        if start_date:
            query = query.filter(VKYCRecording.recording_date >= start_date)
        if end_date:
            query = query.filter(VKYCRecording.recording_date <= end_date)

        total_count = query.count()
        records = query.offset(skip).limit(limit).all()
        logger.info(f"Retrieved {len(records)} VKYC recordings (total: {total_count}) with filters.")
        return records, total_count

    def update_recording(self, recording_id: int, update_data: VKYCRecordingUpdate) -> VKYCRecording:
        """
        Updates an existing VKYC recording.
        Raises NotFoundException if record does not exist.
        Raises ConflictException if new LAN ID already exists for another record.
        """
        db_recording = self.get_recording_by_id(recording_id) # Reuses get_recording_by_id for existence check

        if update_data.lan_id and update_data.lan_id != db_recording.lan_id:
            existing_record = self.db.query(VKYCRecording).filter(VKYCRecording.lan_id == update_data.lan_id).first()
            if existing_record and existing_record.id != recording_id:
                logger.warning(f"Attempted to update LAN ID to an existing one: {update_data.lan_id}")
                raise ConflictException(detail=f"LAN ID '{update_data.lan_id}' already exists for another recording.")

        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(db_recording, field, value)

        try:
            self.db.add(db_recording)
            self.db.commit()
            self.db.refresh(db_recording)
            logger.info(f"Updated VKYC recording with ID: {recording_id}, LAN ID: {db_recording.lan_id}")
            return db_recording
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to update VKYC recording with ID {recording_id}: {e}", exc_info=True)
            raise InternalServerErrorException(detail="Failed to update VKYC recording due to a database error.") from e

    def delete_recording(self, recording_id: int):
        """
        Deletes a VKYC recording by its ID.
        Raises NotFoundException if record does not exist.
        """
        db_recording = self.get_recording_by_id(recording_id) # Reuses get_recording_by_id for existence check
        try:
            self.db.delete(db_recording)
            self.db.commit()
            logger.info(f"Deleted VKYC recording with ID: {recording_id}, LAN ID: {db_recording.lan_id}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete VKYC recording with ID {recording_id}: {e}", exc_info=True)
            raise InternalServerErrorException(detail="Failed to delete VKYC recording due to a database error.") from e

    def ingest_csv_data(self, csv_file_content: bytes, uploaded_by: str) -> CSVUploadResult:
        """
        Ingests VKYC recording metadata from a CSV file.
        Performs validation and either creates new records or updates existing ones.
        """
        successful_ingestions = 0
        failed_ingestions = 0
        errors = []
        total_records = 0

        csv_file = io.StringIO(csv_file_content.decode('utf-8'))
        reader = csv.DictReader(csv_file)

        # Expected CSV headers (case-insensitive for robustness)
        expected_headers = {
            "lan_id": "lan_id",
            "recording_date": "recording_date",
            "file_path": "file_path",
            "status": "status"
        }
        
        # Map actual headers to expected schema fields
        header_map = {}
        if reader.fieldnames:
            for field in reader.fieldnames:
                normalized_field = field.strip().lower().replace(" ", "_")
                if normalized_field in expected_headers:
                    header_map[field] = expected_headers[normalized_field]
        
        if not all(key in header_map for key in expected_headers.values()):
            missing_headers = [h for h in expected_headers.values() if h not in header_map.values()]
            error_msg = f"Missing required CSV headers: {', '.join(missing_headers)}. Expected: {', '.join(expected_headers.keys())}"
            logger.error(error_msg)
            raise UnprocessableEntityException(detail=error_msg)

        records_to_process = []
        for i, row in enumerate(reader):
            total_records += 1
            try:
                # Map CSV row to schema fields using the header_map
                mapped_row = {header_map[k]: v for k, v in row.items() if k in header_map}

                # Basic validation and type conversion
                lan_id = mapped_row.get("lan_id")
                recording_date_str = mapped_row.get("recording_date")
                file_path = mapped_row.get("file_path")
                status = mapped_row.get("status", "PENDING") # Default status if not provided

                if not lan_id or not recording_date_str or not file_path:
                    raise ValueError("Missing required fields (lan_id, recording_date, file_path).")

                try:
                    # Attempt to parse common date formats
                    recording_date = datetime.fromisoformat(recording_date_str)
                except ValueError:
                    try:
                        recording_date = datetime.strptime(recording_date_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        raise ValueError(f"Invalid recording_date format: '{recording_date_str}'. Expected ISO format (YYYY-MM-DDTHH:MM:SS) or YYYY-MM-DD HH:MM:SS.")

                # Create Pydantic model for validation
                record_data = VKYCRecordingCreate(
                    lan_id=lan_id,
                    recording_date=recording_date,
                    file_path=file_path,
                    status=status
                )
                records_to_process.append((record_data, i + 2)) # Store data and original row number (for error reporting)

            except Exception as e:
                failed_ingestions += 1
                errors.append(f"Row {i + 2}: {e}")
                logger.warning(f"Skipping row {i + 2} due to validation error: {e}")
                continue

        if not records_to_process:
            if total_records == 0:
                raise UnprocessableEntityException(detail="CSV file is empty or contains only headers.")
            else:
                raise UnprocessableEntityException(detail=f"No valid records found in CSV. Total errors: {len(errors)}. Errors: {'; '.join(errors)}")

        # Process records in a single transaction for atomicity
        try:
            for record_data, row_num in records_to_process:
                existing_record = self.db.query(VKYCRecording).filter(VKYCRecording.lan_id == record_data.lan_id).first()
                if existing_record:
                    # Update existing record
                    for field, value in record_data.model_dump(exclude_unset=True).items():
                        setattr(existing_record, field, value)
                    existing_record.uploaded_by = uploaded_by # Update who last touched it
                    self.db.add(existing_record)
                    logger.debug(f"Updated existing record for LAN ID: {record_data.lan_id}")
                else:
                    # Create new record
                    new_record = VKYCRecording(
                        **record_data.model_dump(),
                        uploaded_by=uploaded_by
                    )
                    self.db.add(new_record)
                    logger.debug(f"Created new record for LAN ID: {record_data.lan_id}")
                successful_ingestions += 1
            
            self.db.commit()
            logger.info(f"CSV ingestion complete. Successful: {successful_ingestions}, Failed: {failed_ingestions}")

        except Exception as e:
            self.db.rollback()
            failed_ingestions = total_records - len(errors) # All records in this batch failed
            errors.append(f"Database transaction failed: {e}")
            logger.error(f"CSV ingestion database transaction failed: {e}", exc_info=True)
            raise InternalServerErrorException(detail="Failed to ingest CSV data due to a database transaction error.") from e

        return CSVUploadResult(
            total_records=total_records,
            successful_ingestions=successful_ingestions,
            failed_ingestions=failed_ingestions,
            errors=errors
        )