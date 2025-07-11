import logging
import csv
from io import StringIO
from typing import List, Dict, Tuple
from fastapi import UploadFile
from sqlalchemy.orm import Session
from config import settings
from core.exceptions import InvalidFileFormatException, InvalidLANIDCountException, FileTooLargeException
from models import FileUpload
from schemas import LANIDValidationDetail
from utils.lan_id_validator import is_valid_lan_id

log = logging.getLogger(__name__)

class FileParserService:
    """
    Service responsible for parsing and validating uploaded files containing LAN IDs.
    """
    def __init__(self, db_session: Session):
        self.db_session = db_session

    async def parse_and_validate_file(self, file: UploadFile, uploaded_by: str) -> Dict:
        """
        Parses the uploaded file (CSV or TXT), extracts LAN IDs,
        validates them, and stores the upload metadata in the database.

        Args:
            file (UploadFile): The uploaded file object.
            uploaded_by (str): The username of the user who uploaded the file.

        Returns:
            Dict: A dictionary containing the processing summary, including
                  valid and invalid LAN IDs and their details.
        """
        log.info(f"Starting file processing for '{file.filename}' (Type: {file.content_type}) by user '{uploaded_by}'")

        # 1. Validate file type and size
        self._validate_file_metadata(file)

        # 2. Read file content
        content = await file.read()
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            log.error(f"Failed to decode file '{file.filename}' as UTF-8.")
            raise InvalidFileFormatException(detail="File content is not valid UTF-8.")

        # 3. Extract LAN IDs based on file type
        lan_ids_raw = self._extract_lan_ids(text_content, file.content_type)
        total_lan_ids = len(lan_ids_raw)
        log.info(f"Extracted {total_lan_ids} raw LAN IDs from '{file.filename}'.")

        # 4. Validate LAN ID count
        self._validate_lan_id_count(total_lan_ids)

        # 5. Validate individual LAN IDs
        valid_lan_ids, invalid_lan_ids_details = self._validate_individual_lan_ids(lan_ids_raw)
        log.info(f"Validation complete: {len(valid_lan_ids)} valid, {len(invalid_lan_ids_details)} invalid.")

        # 6. Persist upload metadata to database
        upload_status = "Completed" if not invalid_lan_ids_details else "Completed with Errors"
        message = "File processed successfully."
        if invalid_lan_ids_details:
            message = f"File processed with {len(invalid_lan_ids_details)} invalid LAN IDs."

        file_upload_record = FileUpload(
            filename=file.filename,
            file_type=file.content_type,
            uploaded_by=uploaded_by,
            status=upload_status,
            total_lan_ids=total_lan_ids,
            valid_lan_ids_count=len(valid_lan_ids),
            invalid_lan_ids_count=len(invalid_lan_ids_details),
            processed_lan_ids=valid_lan_ids, # Store only valid ones for further processing
            invalid_lan_ids_details=[detail.model_dump() for detail in invalid_lan_ids_details],
            message=message
        )
        self.db_session.add(file_upload_record)
        self.db_session.commit()
        self.db_session.refresh(file_upload_record)
        log.info(f"File upload record created in DB with ID: {file_upload_record.id}")

        return {
            "upload_id": file_upload_record.id,
            "filename": file_upload_record.filename,
            "status": file_upload_record.status,
            "message": file_upload_record.message,
            "total_lan_ids": file_upload_record.total_lan_ids,
            "valid_lan_ids_count": file_upload_record.valid_lan_ids_count,
            "invalid_lan_ids_count": file_upload_record.invalid_lan_ids_count,
            "invalid_lan_ids_details": invalid_lan_ids_details,
        }

    def _validate_file_metadata(self, file: UploadFile):
        """Validates the file's content type and size."""
        if file.content_type not in ["text/csv", "text/plain"]:
            log.warning(f"Invalid file format uploaded: {file.content_type}")
            raise InvalidFileFormatException()

        # Check file size (FastAPI's UploadFile.size is not always reliable for large files
        # until content is read. This is a pre-check if available, actual check happens on read.)
        if file.size is not None and file.size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            log.warning(f"File '{file.filename}' size ({file.size} bytes) exceeds limit ({settings.MAX_FILE_SIZE_MB} MB).")
            raise FileTooLargeException()

    def _extract_lan_ids(self, text_content: str, content_type: str) -> List[str]:
        """
        Extracts LAN IDs from the text content based on file type.
        """
        lan_ids = []
        if content_type == "text/csv":
            csv_file = StringIO(text_content)
            reader = csv.reader(csv_file)
            for i, row in enumerate(reader):
                # Assuming LAN IDs are in the first column of CSV
                if row:
                    lan_ids.append(row[0].strip())
                else:
                    log.debug(f"Empty row found in CSV at line {i+1}.")
        elif content_type == "text/plain":
            # Assuming one LAN ID per line for TXT files
            for i, line in enumerate(text_content.splitlines()):
                cleaned_line = line.strip()
                if cleaned_line:
                    lan_ids.append(cleaned_line)
                else:
                    log.debug(f"Empty line found in TXT at line {i+1}.")
        return lan_ids

    def _validate_lan_id_count(self, count: int):
        """Validates the total number of extracted LAN IDs."""
        if not (settings.MIN_LAN_IDS_PER_FILE <= count <= settings.MAX_LAN_IDS_PER_FILE):
            log.warning(f"Invalid LAN ID count: {count}. Expected between {settings.MIN_LAN_IDS_PER_FILE} and {settings.MAX_LAN_IDS_PER_FILE}.")
            raise InvalidLANIDCountException(
                min_count=settings.MIN_LAN_IDS_PER_FILE,
                max_count=settings.MAX_LAN_IDS_PER_FILE,
                actual_count=count
            )

    def _validate_individual_lan_ids(self, lan_ids_raw: List[str]) -> Tuple[List[str], List[LANIDValidationDetail]]:
        """
        Validates each individual LAN ID using the `is_valid_lan_id` utility.
        """
        valid_lan_ids = []
        invalid_lan_ids_details = []
        for i, lan_id in enumerate(lan_ids_raw):
            if is_valid_lan_id(lan_id):
                valid_lan_ids.append(lan_id)
            else:
                reason = "Does not match expected pattern or is empty/whitespace."
                invalid_lan_ids_details.append(
                    LANIDValidationDetail(lan_id=lan_id, reason=reason, line_number=i + 1)
                )
        return valid_lan_ids, invalid_lan_ids_details