import logging
import csv
from io import StringIO
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import UploadFile

from app.models.recording import Recording, RecordingStatus
from app.schemas.recording import RecordingCreate, BulkUploadResponse, BulkUploadRecordDetail
from app.core.exceptions import FileProcessingException, InvalidInputException
from app.utils.file_processor import parse_lan_ids_from_csv, generate_nfs_path
from config import settings

logger = logging.getLogger(__name__)

class RecordingService:
    """
    Service layer for handling VKYC recording business logic.
    """
    def __init__(self, db: Session):
        self.db = db

    async def bulk_upload_recordings(self, file: UploadFile) -> BulkUploadResponse:
        """
        Processes a bulk upload file (CSV/TXT) containing LAN IDs,
        validates them, and stores recording metadata in the database.
        """
        if not file.filename.lower().endswith(('.csv', '.txt')):
            raise InvalidInputException(
                detail="Invalid file type. Only CSV or TXT files are allowed for bulk upload."
            )

        # Read file content
        try:
            contents = await file.read()
            file_content_str = contents.decode('utf-8')
            file_size_mb = len(contents) / (1024 * 1024)
            if file_size_mb > settings.MAX_BULK_UPLOAD_FILE_SIZE_MB:
                raise FileProcessingException(
                    f"File size exceeds limit of {settings.MAX_BULK_UPLOAD_FILE_SIZE_MB} MB."
                )
        except UnicodeDecodeError:
            logger.error(f"Failed to decode file {file.filename}. Ensure it's UTF-8 encoded.", exc_info=True)
            raise FileProcessingException(
                f"Could not decode file '{file.filename}'. Please ensure it is a valid UTF-8 encoded CSV/TXT file."
            )
        except Exception as e:
            logger.error(f"Error reading uploaded file {file.filename}: {e}", exc_info=True)
            raise FileProcessingException(f"Failed to read uploaded file: {e}")

        # Parse LAN IDs from the file
        try:
            lan_ids = parse_lan_ids_from_csv(StringIO(file_content_str))
        except ValueError as e:
            logger.warning(f"File parsing error for {file.filename}: {e}")
            raise InvalidInputException(f"Error parsing file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during file parsing for {file.filename}: {e}", exc_info=True)
            raise FileProcessingException(f"An unexpected error occurred during file parsing: {e}")

        total_records = len(lan_ids)
        if total_records == 0:
            raise InvalidInputException("Uploaded file contains no valid LAN IDs.")
        if total_records > settings.MAX_BULK_UPLOAD_RECORDS:
            raise InvalidInputException(
                f"Number of records ({total_records}) exceeds the maximum allowed ({settings.MAX_BULK_UPLOAD_RECORDS})."
            )

        processed_count = 0
        failed_count = 0
        details: List[BulkUploadRecordDetail] = []
        records_to_add: List[Recording] = []

        for lan_id in lan_ids:
            record_detail = BulkUploadRecordDetail(lan_id=lan_id, status=RecordingStatus.PENDING)
            try:
                # Basic LAN ID format validation (can be more complex)
                if not lan_id or not isinstance(lan_id, str) or len(lan_id) < 5: # Example validation
                    record_detail.status = RecordingStatus.INVALID_LAN_ID
                    record_detail.message = "Invalid LAN ID format or empty."
                    failed_count += 1
                    details.append(record_detail)
                    continue

                # Generate a hypothetical NFS path based on LAN ID
                # In a real system, this might involve a lookup or more complex logic
                file_path = generate_nfs_path(lan_id)

                # Create a Recording object
                recording_data = RecordingCreate(
                    lan_id=lan_id,
                    file_path=file_path,
                    status=RecordingStatus.PENDING # Initial status
                )
                new_recording = Recording(**recording_data.model_dump())
                records_to_add.append(new_recording)

                record_detail.status = RecordingStatus.PROCESSING # Mark as ready for DB insert
                record_detail.message = "Ready for database insertion."
                details.append(record_detail)

            except Exception as e:
                logger.error(f"Error preparing record for LAN ID '{lan_id}': {e}", exc_info=True)
                record_detail.status = RecordingStatus.FAILED
                record_detail.message = f"Internal error preparing record: {e}"
                failed_count += 1
                details.append(record_detail)

        # Batch insert into database
        if records_to_add:
            try:
                self.db.bulk_save_objects(records_to_add)
                self.db.commit()
                for record in records_to_add:
                    # Update status for successfully added records
                    for detail in details:
                        if detail.lan_id == record.lan_id and detail.status == RecordingStatus.PROCESSING:
                            detail.status = RecordingStatus.PROCESSED
                            detail.message = "Successfully added to database."
                            processed_count += 1
                            break
                logger.info(f"Successfully inserted {len(records_to_add)} records into database.")
            except IntegrityError as e:
                self.db.rollback()
                logger.warning(f"Integrity error during bulk insert: {e}. Some LAN IDs might be duplicates.", exc_info=True)
                # Handle duplicates or other integrity errors specifically
                for record in records_to_add:
                    try:
                        # Try to add individually to identify duplicates
                        self.db.add(record)
                        self.db.commit()
                        for detail in details:
                            if detail.lan_id == record.lan_id and detail.status == RecordingStatus.PROCESSING:
                                detail.status = RecordingStatus.PROCESSED
                                detail.message = "Successfully added to database."
                                processed_count += 1
                                break
                    except IntegrityError:
                        self.db.rollback()
                        for detail in details:
                            if detail.lan_id == record.lan_id and detail.status == RecordingStatus.PROCESSING:
                                detail.status = RecordingStatus.FAILED
                                detail.message = "LAN ID already exists in the database."
                                failed_count += 1
                                break
                    except SQLAlchemyError as db_err:
                        self.db.rollback()
                        logger.error(f"Database error for LAN ID '{record.lan_id}': {db_err}", exc_info=True)
                        for detail in details:
                            if detail.lan_id == record.lan_id and detail.status == RecordingStatus.PROCESSING:
                                detail.status = RecordingStatus.FAILED
                                detail.message = f"Database error: {db_err}"
                                failed_count += 1
                                break
            except SQLAlchemyError as e:
                self.db.rollback()
                logger.error(f"Database error during bulk insert: {e}", exc_info=True)
                # Mark all remaining as failed if a batch error occurs
                for detail in details:
                    if detail.status == RecordingStatus.PROCESSING:
                        detail.status = RecordingStatus.FAILED
                        detail.message = f"Database error during batch insert: {e}"
                        failed_count += 1
                raise FileProcessingException(f"Database error during bulk upload: {e}")

        overall_message = f"Bulk upload completed. Total: {total_records}, Processed: {processed_count}, Failed: {failed_count}."
        logger.info(overall_message)

        return BulkUploadResponse(
            total_records=total_records,
            processed_records=processed_count,
            failed_records=failed_count,
            details=details,
            message=overall_message
        )