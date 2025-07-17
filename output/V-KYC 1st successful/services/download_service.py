import os
import re
from typing import List, Dict, Tuple
from uuid import uuid4
from datetime import datetime

from sqlalchemy.orm import Session

from config import settings
from crud import CRUDOperations
from models import DownloadRequest, FileMetadata, DownloadStatus, FileExistenceStatus
from schemas import BulkDownloadRequest, DownloadRequestResponse, FileMetadataSchema, DownloadRequestCreate, DownloadRequestUpdate
from utils.logger import logger
from utils.exceptions import NotFoundException, CustomValidationException, ServiceUnavailableException

class DownloadService:
    def __init__(self, db: Session, crud: CRUDOperations):
        self.db = db
        self.crud = crud
        self.nfs_base_path = settings.NFS_BASE_PATH

    def _validate_lan_id(self, lan_id: str) -> bool:
        """
        Validates the format of a LAN ID.
        Example: LAN IDs are typically alphanumeric, often with a specific length or prefix.
        Assuming a simple alphanumeric check for now.
        """
        if not re.fullmatch(r"^[A-Z0-9]{5,50}$", lan_id):
            logger.warning(f"Invalid LAN ID format: {lan_id}")
            return False
        return True

    def _simulate_fetch_metadata(self, lan_id: str) -> Dict:
        """
        Simulates fetching metadata for a given LAN ID from an external system.
        In a real scenario, this would involve an API call to a VKYC system.
        For this example, we'll use a hardcoded mapping.
        """
        # Example mapping: LAN ID -> potential file name pattern
        # Real metadata would include actual file paths, sizes, dates, etc.
        mock_metadata = {
            "LAN1234567890": {"potential_file_name_pattern": f"LAN1234567890_*.mp4"},
            "LAN0987654321": {"potential_file_name_pattern": f"LAN0987654321_*.mp4"},
            "LAN1122334455": {"potential_file_name_pattern": f"LAN1122334455_*.mp4"},
            "LAN9988776655": {"potential_file_name_pattern": f"LAN9988776655_*.mp4"},
            # Add more as needed for testing
        }
        
        if lan_id in mock_metadata:
            logger.debug(f"Simulated metadata fetched for {lan_id}")
            return mock_metadata[lan_id]
        else:
            logger.warning(f"No mock metadata found for LAN ID: {lan_id}")
            return {}

    def _check_file_existence_on_nfs(self, lan_id: str, potential_file_name_pattern: str) -> Tuple[FileExistenceStatus, Optional[str], Optional[str]]:
        """
        Simulates checking for file existence on the NFS server.
        This involves listing files in the NFS_BASE_PATH and matching the pattern.
        In a real scenario, this might be a direct NFS mount check or an API call to a file server.
        """
        try:
            # Normalize pattern for regex
            regex_pattern = potential_file_name_pattern.replace('*', '.*')
            
            found_file_path = None
            found_file_name = None

            # List files in the simulated NFS directory
            for filename in os.listdir(self.nfs_base_path):
                if re.fullmatch(regex_pattern, filename):
                    found_file_path = os.path.join(self.nfs_base_path, filename)
                    found_file_name = filename
                    logger.info(f"File found for {lan_id}: {found_file_path}")
                    return FileExistenceStatus.EXISTS, found_file_path, found_file_name
            
            logger.info(f"File not found for {lan_id} with pattern {potential_file_name_pattern} in {self.nfs_base_path}")
            return FileExistenceStatus.NOT_FOUND, None, None

        except FileNotFoundError:
            logger.error(f"NFS base path not found: {self.nfs_base_path}")
            return FileExistenceStatus.ERROR, None, "NFS base path not accessible."
        except PermissionError:
            logger.error(f"Permission denied to access NFS base path: {self.nfs_base_path}")
            return FileExistenceStatus.ERROR, None, "Permission denied to access NFS storage."
        except Exception as e:
            logger.error(f"Error checking file existence for {lan_id}: {e}", exc_info=True)
            return FileExistenceStatus.ERROR, None, f"An unexpected error occurred during file check: {e}"

    def process_bulk_download_request(self, request_data: BulkDownloadRequest, requested_by: str) -> DownloadRequestResponse:
        """
        Processes a bulk download request.
        For each LAN ID:
        1. Validates LAN ID format.
        2. Fetches/creates FileMetadata record.
        3. Simulates fetching metadata from an external VKYC system.
        4. Simulates checking file existence on NFS.
        5. Updates FileMetadata record with existence status and path.
        6. Creates a new DownloadRequest record to track the bulk operation.
        """
        if not request_data.lan_ids:
            raise CustomValidationException(detail="No LAN IDs provided for bulk download.")
        if len(request_data.lan_ids) > 10:
            raise CustomValidationException(detail="Maximum 10 LAN IDs allowed per bulk download request.")

        request_uuid = uuid4()
        file_metadata_ids: List[int] = []
        files_details: List[FileMetadataSchema] = []
        
        total_files = len(request_data.lan_ids)
        files_found = 0
        files_not_found = 0
        files_error = 0
        
        # Create initial DownloadRequest in PENDING state
        initial_download_request = self.crud.create_download_request(
            DownloadRequestCreate(
                request_id=request_uuid,
                requested_by=requested_by,
                total_files=total_files,
                status=DownloadStatus.PENDING
            )
        )
        
        for lan_id in request_data.lan_ids:
            if not self._validate_lan_id(lan_id):
                # Create/update metadata for invalid LAN ID
                db_file_meta = self.crud.get_file_metadata_by_lan_id(lan_id)
                if not db_file_meta:
                    db_file_meta = self.crud.create_file_metadata(lan_id=lan_id)
                
                updated_meta = self.crud.update_file_metadata(
                    db_file_meta,
                    {
                        "existence_status": FileExistenceStatus.ERROR,
                        "error_message": "Invalid LAN ID format.",
                        "last_checked_at": datetime.now()
                    }
                )
                files_error += 1
                file_metadata_ids.append(updated_meta.id)
                files_details.append(FileMetadataSchema.model_validate(updated_meta))
                continue # Skip to next LAN ID

            db_file_meta = self.crud.get_file_metadata_by_lan_id(lan_id)
            if not db_file_meta:
                db_file_meta = self.crud.create_file_metadata(lan_id=lan_id)
            
            try:
                # Step 1: Simulate fetching metadata
                metadata = self._simulate_fetch_metadata(lan_id)
                potential_file_name_pattern = metadata.get("potential_file_name_pattern")

                if not potential_file_name_pattern:
                    logger.warning(f"No potential file name pattern found for LAN ID: {lan_id}. Marking as NOT_FOUND.")
                    updated_meta = self.crud.update_file_metadata(
                        db_file_meta,
                        {
                            "existence_status": FileExistenceStatus.NOT_FOUND,
                            "error_message": "No file pattern found in VKYC metadata.",
                            "last_checked_at": datetime.now()
                        }
                    )
                    files_not_found += 1
                else:
                    # Step 2: Simulate checking file existence on NFS
                    existence_status, file_path, file_name = self._check_file_existence_on_nfs(lan_id, potential_file_name_pattern)
                    
                    update_data = {
                        "file_path": file_path,
                        "file_name": file_name,
                        "existence_status": existence_status,
                        "last_checked_at": datetime.now()
                    }
                    if existence_status == FileExistenceStatus.ERROR:
                        update_data["error_message"] = file_name # file_name here holds the error message
                        files_error += 1
                    elif existence_status == FileExistenceStatus.EXISTS:
                        files_found += 1
                    else: # NOT_FOUND
                        files_not_found += 1
                        update_data["error_message"] = "File not found on NFS."

                    updated_meta = self.crud.update_file_metadata(db_file_meta, update_data)
                
                file_metadata_ids.append(updated_meta.id)
                files_details.append(FileMetadataSchema.model_validate(updated_meta))

            except ServiceUnavailableException as e:
                # Handle specific service errors (e.g., NFS down, external metadata service down)
                logger.error(f"Service error processing LAN ID {lan_id}: {e.detail}")
                updated_meta = self.crud.update_file_metadata(
                    db_file_meta,
                    {
                        "existence_status": FileExistenceStatus.ERROR,
                        "error_message": f"Service error: {e.detail}",
                        "last_checked_at": datetime.now()
                    }
                )
                files_error += 1
                file_metadata_ids.append(updated_meta.id)
                files_details.append(FileMetadataSchema.model_validate(updated_meta))
            except Exception as e:
                logger.exception(f"Unhandled error processing LAN ID {lan_id}")
                updated_meta = self.crud.update_file_metadata(
                    db_file_meta,
                    {
                        "existence_status": FileExistenceStatus.ERROR,
                        "error_message": f"An unexpected error occurred: {e}",
                        "last_checked_at": datetime.now()
                    }
                )
                files_error += 1
                file_metadata_ids.append(updated_meta.id)
                files_details.append(FileMetadataSchema.model_validate(updated_meta))

        # Update the main DownloadRequest status based on results
        final_status = DownloadStatus.COMPLETED
        summary_message = "Bulk download request processed."
        if files_error > 0:
            final_status = DownloadStatus.FAILED if files_found == 0 and files_not_found == 0 else DownloadStatus.PARTIAL_SUCCESS
            summary_message = f"Processed with {files_error} errors."
        elif files_not_found > 0 and files_found > 0:
            final_status = DownloadStatus.PARTIAL_SUCCESS
            summary_message = f"Processed with {files_not_found} files not found."
        elif files_not_found == total_files:
            final_status = DownloadStatus.FAILED
            summary_message = "All files not found."
        
        updated_download_request = self.crud.update_download_request(
            initial_download_request,
            DownloadRequestUpdate(
                status=final_status,
                file_metadata_ids=file_metadata_ids,
                files_found=files_found,
                files_not_found=files_not_found,
                files_error=files_error,
                summary_message=summary_message
            )
        )
        
        # Construct the response with detailed file metadata
        response_data = DownloadRequestResponse.model_validate(updated_download_request)
        response_data.files_details = files_details # Attach the collected details

        logger.info(f"Bulk download request {request_uuid} processed with status: {final_status}")
        return response_data

    def get_download_request_status(self, request_id: str) -> DownloadRequestResponse:
        """
        Retrieves the status and details of a specific bulk download request.
        """
        try:
            request_uuid = uuid4(request_id) # Validate UUID format
        except ValueError:
            raise CustomValidationException(detail=f"Invalid request ID format: {request_id}")

        db_request = self.crud.get_download_request(request_uuid)
        if not db_request:
            raise NotFoundException(detail=f"Download request with ID '{request_id}' not found.")
        
        # Fetch associated file metadata details
        files_details = self.crud.get_file_metadata_by_ids(db_request.file_metadata_ids)
        
        response_data = DownloadRequestResponse.model_validate(db_request)
        response_data.files_details = [FileMetadataSchema.model_validate(f) for f in files_details]

        logger.info(f"Retrieved status for download request {request_id}")
        return response_data

# Dependency for DownloadService
def get_download_service(db: Session = Depends(crud.get_db), crud: CRUDOperations = Depends(crud.get_crud)) -> DownloadService:
    """Dependency to provide DownloadService instance."""
    return DownloadService(db, crud)