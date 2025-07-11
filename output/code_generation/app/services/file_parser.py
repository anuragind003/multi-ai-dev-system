import logging
import re
from io import StringIO
from typing import List, Tuple, Dict, Any

from fastapi import UploadFile
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import InvalidFileContentError, LANIDCountExceededError, FileProcessingError, DatabaseError
from app.db.models import ParsedFile
from app.schemas.file_parsing import LANIDValidationResult

logger = logging.getLogger(__name__)

class FileParserService:
    """
    Service layer for handling file parsing, LAN ID validation, and database operations.
    """
    MIN_LAN_IDS = 2
    MAX_LAN_IDS = 50
    # Example LAN ID format: "LAN" followed by 7 digits. Adjust regex as per actual requirement.
    LAN_ID_REGEX = re.compile(r"^LAN\d{7}$")

    def __init__(self, db: Session):
        self.db = db

    async def parse_and_validate_file(self, file: UploadFile) -> Dict[str, Any]:
        """
        Parses an uploaded CSV/TXT file, validates LAN IDs, and stores the results.

        Args:
            file: The uploaded file object (FastAPI UploadFile).

        Returns:
            A dictionary containing the processing results, including validation details.

        Raises:
            InvalidFileContentError: If the file content is unreadable or malformed.
            LANIDCountExceededError: If the number of LAN IDs is outside the allowed range.
            FileProcessingError: For other general file processing issues.
            DatabaseError: If there's an issue saving to the database.
        """
        filename = file.filename
        logger.info(f"Starting file parsing and validation for: {filename}")

        try:
            # Read file content
            content = await file.read()
            content_str = content.decode('utf-8').strip()
            if not content_str:
                raise InvalidFileContentError(detail="Uploaded file is empty.")

            # Split content into lines and filter out empty lines
            lan_ids_raw = [line.strip() for line in StringIO(content_str).readlines() if line.strip()]
            total_lan_ids = len(lan_ids_raw)

            # Validate LAN ID count
            if not (self.MIN_LAN_IDS <= total_lan_ids <= self.MAX_LAN_IDS):
                raise LANIDCountExceededError(total_lan_ids, self.MIN_LAN_IDS, self.MAX_LAN_IDS)

            validation_results: List[LANIDValidationResult] = []
            valid_lan_ids: List[str] = []
            invalid_lan_id_errors: List[str] = []

            # Validate each LAN ID
            for lan_id in lan_ids_raw:
                is_valid, error_msg = self._validate_lan_id(lan_id)
                validation_results.append(LANIDValidationResult(
                    lan_id=lan_id,
                    is_valid=is_valid,
                    error_message=error_msg
                ))
                if is_valid:
                    valid_lan_ids.append(lan_id)
                else:
                    invalid_lan_id_errors.append(f"{lan_id}: {error_msg}")

            # Determine overall status
            status_str = "success"
            message = "File processed successfully. All LAN IDs are valid."
            if invalid_lan_id_errors:
                status_str = "partial_success" if valid_lan_ids else "failed"
                message = "File processed with some invalid LAN IDs." if valid_lan_ids else "File processing failed: All LAN IDs are invalid."

            # Save results to database
            parsed_file_record = ParsedFile(
                filename=filename,
                status=status_str,
                lan_ids=valid_lan_ids,
                errors=invalid_lan_id_errors
            )
            try:
                self.db.add(parsed_file_record)
                self.db.commit()
                self.db.refresh(parsed_file_record)
                logger.info(f"File parsing results for '{filename}' saved to DB with ID: {parsed_file_record.id}")
            except SQLAlchemyError as db_exc:
                self.db.rollback()
                logger.error(f"Database error saving parsed file '{filename}': {db_exc}", exc_info=True)
                raise DatabaseError(f"Failed to save file processing results for '{filename}'.") from db_exc

            return {
                "filename": filename,
                "status": status_str,
                "message": message,
                "total_lan_ids": total_lan_ids,
                "valid_lan_ids_count": len(valid_lan_ids),
                "invalid_lan_ids_count": len(invalid_lan_id_errors),
                "validation_results": validation_results,
                "parsed_file_id": parsed_file_record.id
            }

        except InvalidFileContentError as e:
            logger.warning(f"File content error for '{filename}': {e.detail}")
            raise
        except LANIDCountExceededError as e:
            logger.warning(f"LAN ID count error for '{filename}': {e.detail}")
            raise
        except UnicodeDecodeError as e:
            logger.warning(f"UnicodeDecodeError for '{filename}': {e}. File might not be UTF-8 encoded.", exc_info=True)
            raise InvalidFileContentError(detail="File encoding error. Please ensure it's UTF-8 encoded.") from e
        except Exception as e:
            logger.error(f"Unexpected error processing file '{filename}': {e}", exc_info=True)
            raise FileProcessingError(f"An unexpected error occurred while processing '{filename}'.") from e

    def _validate_lan_id(self, lan_id: str) -> Tuple[bool, str]:
        """
        Validates a single LAN ID against the defined regex.
        """
        if not lan_id:
            return False, "LAN ID cannot be empty."
        if not self.LAN_ID_REGEX.match(lan_id):
            return False, "Invalid format. Expected 'LAN' followed by 7 digits (e.g., LAN1234567)."
        return True, ""