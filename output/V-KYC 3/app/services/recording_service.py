import os
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.models import Recording, User, BulkRequest
from app.schemas import RecordingCreate, RecordingUpdate, BulkRequestCreate
from app.exceptions import NotFoundException, ConflictException, InvalidInputException, ServiceUnavailableException
from app.logger import logger

class RecordingService:
    """
    Service layer for managing V-KYC recording metadata and simulating NFS interactions.
    """
    def __init__(self, db: Session):
        self.db = db

    def _simulate_nfs_access(self, file_path: str, operation: str = "read") -> bool:
        """
        Simulates access to an NFS server.
        In a real application, this would involve actual network file system calls.
        For this simulation, it checks if the file exists in the configured local path.
        """
        full_path = os.path.join(settings.NFS_SERVER_PATH, file_path.lstrip('/'))
        if operation == "read":
            if not os.path.exists(full_path):
                logger.warning(f"NFS simulation: File not found at {full_path}")
                return False
            if not os.path.isfile(full_path):
                logger.warning(f"NFS simulation: Path is not a file at {full_path}")
                return False
            return True
        elif operation == "write":
            try:
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f: # Create a dummy file
                    f.write("Simulated recording content.")
                logger.info(f"NFS simulation: Created dummy file at {full_path}")
                return True
            except OSError as e:
                logger.error(f"NFS simulation: Failed to write file at {full_path}: {e}")
                return False
        elif operation == "delete":
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                    logger.info(f"NFS simulation: Deleted file at {full_path}")
                    return True
                except OSError as e:
                    logger.error(f"NFS simulation: Failed to delete file at {full_path}: {e}")
                    return False
            return True # Consider it successful if file doesn't exist to begin with
        return False

    def get_recording_by_id(self, recording_id: int) -> Optional[Recording]:
        """Retrieves a recording by its ID."""
        recording = self.db.query(Recording).filter(Recording.id == recording_id).first()
        if not recording:
            logger.info(f"Recording with ID {recording_id} not found.")
            raise NotFoundException(detail=f"Recording with ID {recording_id} not found.")
        return recording

    def get_all_recordings(self, skip: int = 0, limit: int = 100, lan_id: Optional[str] = None) -> List[Recording]:
        """Retrieves a list of all recordings with pagination and optional filtering by LAN ID."""
        query = self.db.query(Recording)
        if lan_id:
            query = query.filter(Recording.lan_id == lan_id)
        return query.offset(skip).limit(limit).all()

    def create_recording(self, recording_data: RecordingCreate, uploader_id: int) -> Recording:
        """
        Creates a new recording metadata entry.
        Simulates file creation on NFS.
        Raises ConflictException if a recording with the same file_path already exists.
        Raises ServiceUnavailableException if NFS simulation fails.
        """
        if self.db.query(Recording).filter(Recording.file_path == recording_data.file_path).first():
            logger.warning(f"Attempted to create recording with existing file path: {recording_data.file_path}")
            raise ConflictException(detail=f"Recording with file path '{recording_data.file_path}' already exists.")

        if not self._simulate_nfs_access(recording_data.file_path, operation="write"):
            logger.error(f"Failed to simulate NFS write for {recording_data.file_path}")
            raise ServiceUnavailableException(detail="Failed to create file on storage server (NFS simulation).")

        db_recording = Recording(
            lan_id=recording_data.lan_id,
            file_name=recording_data.file_name,
            file_path=recording_data.file_path,
            file_size_bytes=recording_data.file_size_bytes,
            recording_date=recording_data.recording_date,
            status=recording_data.status,
            metadata_json=recording_data.metadata_json,
            uploader_id=uploader_id
        )
        try:
            self.db.add(db_recording)
            self.db.commit()
            self.db.refresh(db_recording)
            logger.info(f"Recording '{db_recording.file_name}' created successfully by user {uploader_id}.")
            return db_recording
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during recording creation: {e}")
            raise ConflictException(detail=f"A database conflict occurred, possibly duplicate LAN ID or file path.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating recording {recording_data.file_name}: {e}")
            raise InvalidInputException(detail=f"Failed to create recording due to invalid input or server error: {e}")

    def update_recording(self, recording_id: int, recording_data: RecordingUpdate) -> Recording:
        """
        Updates an existing recording's metadata.
        Raises NotFoundException if the recording does not exist.
        Raises ConflictException if attempting to change file_path to an already existing one.
        """
        db_recording = self.get_recording_by_id(recording_id) # This will raise NotFoundException if not found

        if recording_data.file_path and recording_data.file_path != db_recording.file_path:
            if self.db.query(Recording).filter(Recording.file_path == recording_data.file_path).first():
                logger.warning(f"Attempted to update recording {recording_id} to existing file path: {recording_data.file_path}")
                raise ConflictException(detail=f"File path '{recording_data.file_path}' is already used by another recording.")
            # If file path changes, simulate deletion of old file and creation of new one
            self._simulate_nfs_access(db_recording.file_path, operation="delete")
            if not self._simulate_nfs_access(recording_data.file_path, operation="write"):
                logger.error(f"Failed to simulate NFS write for new path {recording_data.file_path}")
                raise ServiceUnavailableException(detail="Failed to update file on storage server (NFS simulation).")

        update_data = recording_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_recording, key, value)

        try:
            self.db.commit()
            self.db.refresh(db_recording)
            logger.info(f"Recording '{db_recording.file_name}' (ID: {recording_id}) updated successfully.")
            return db_recording
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Database integrity error during recording update for ID {recording_id}: {e}")
            raise ConflictException(detail=f"A database conflict occurred during update, possibly duplicate LAN ID or file path.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating recording {recording_id}: {e}")
            raise InvalidInputException(detail=f"Failed to update recording due to invalid input or server error: {e}")

    def delete_recording(self, recording_id: int) -> None:
        """
        Deletes a recording metadata entry and simulates file deletion on NFS.
        Raises NotFoundException if the recording does not exist.
        Raises ServiceUnavailableException if NFS simulation fails.
        """
        db_recording = self.get_recording_by_id(recording_id) # This will raise NotFoundException if not found

        if not self._simulate_nfs_access(db_recording.file_path, operation="delete"):
            logger.error(f"Failed to simulate NFS delete for {db_recording.file_path}")
            raise ServiceUnavailableException(detail="Failed to delete file from storage server (NFS simulation).")

        try:
            self.db.delete(db_recording)
            self.db.commit()
            logger.info(f"Recording '{db_recording.file_name}' (ID: {recording_id}) deleted successfully.")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting recording {recording_id}: {e}")
            raise InvalidInputException(detail=f"Failed to delete recording due to server error: {e}")

    def download_recording_file(self, recording_id: int) -> str:
        """
        Simulates downloading a recording file.
        Raises NotFoundException if the recording metadata is not found.
        Raises ServiceUnavailableException if the file is not accessible on NFS.
        Returns the simulated file path for streaming.
        """
        db_recording = self.get_recording_by_id(recording_id)

        if not self._simulate_nfs_access(db_recording.file_path, operation="read"):
            logger.error(f"Recording file not found or inaccessible on NFS: {db_recording.file_path}")
            raise ServiceUnavailableException(detail="Recording file not found or inaccessible on storage server.")

        # In a real scenario, you would return a file stream or a path that FastAPI can stream
        # For simulation, we return the full path to the dummy file
        full_path = os.path.join(settings.NFS_SERVER_PATH, db_recording.file_path.lstrip('/'))
        logger.info(f"Simulating download of recording file: {full_path}")
        return full_path

    def create_bulk_request(self, bulk_request_data: BulkRequestCreate, requester_id: int) -> BulkRequest:
        """
        Creates a new bulk request entry.
        This is a placeholder for actual bulk processing logic.
        """
        db_bulk_request = BulkRequest(
            request_type=bulk_request_data.request_type,
            status=bulk_request_data.status,
            parameters_json=bulk_request_data.parameters_json,
            requested_by_id=requester_id
        )
        try:
            self.db.add(db_bulk_request)
            self.db.commit()
            self.db.refresh(db_bulk_request)
            logger.info(f"Bulk request '{db_bulk_request.request_type}' created by user {requester_id}.")
            return db_bulk_request
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating bulk request: {e}")
            raise InvalidInputException(detail=f"Failed to create bulk request due to invalid input or server error: {e}")

    def get_bulk_request_by_id(self, request_id: int) -> Optional[BulkRequest]:
        """Retrieves a bulk request by its ID."""
        bulk_request = self.db.query(BulkRequest).filter(BulkRequest.id == request_id).first()
        if not bulk_request:
            logger.info(f"Bulk request with ID {request_id} not found.")
            raise NotFoundException(detail=f"Bulk request with ID {request_id} not found.")
        return bulk_request

    def get_all_bulk_requests(self, skip: int = 0, limit: int = 100, status: Optional[str] = None) -> List[BulkRequest]:
        """Retrieves a list of all bulk requests with pagination and optional filtering by status."""
        query = self.db.query(BulkRequest)
        if status:
            query = query.filter(BulkRequest.status == status)
        return query.offset(skip).limit(limit).all()

    # Placeholder for actual bulk processing logic
    def process_bulk_download(self, request_id: int):
        """
        Simulates processing a bulk download request.
        In a real system, this would trigger an asynchronous task.
        """
        bulk_request = self.get_bulk_request_by_id(request_id)
        if bulk_request.request_type != "download":
            raise InvalidInputException(detail="Request type is not 'download'.")

        bulk_request.status = "processing"
        self.db.commit()
        logger.info(f"Simulating processing for bulk download request {request_id}.")

        try:
            params = json.loads(bulk_request.parameters_json)
            lan_ids = params.get("lan_ids", [])
            
            successful_downloads = []
            failed_downloads = []

            for lan_id in lan_ids:
                # In a real scenario, you'd query recordings by LAN ID and attempt download
                # For this simulation, we just log success/failure
                recordings = self.db.query(Recording).filter(Recording.lan_id == lan_id).all()
                if recordings:
                    for rec in recordings:
                        if self._simulate_nfs_access(rec.file_path, operation="read"):
                            successful_downloads.append({"lan_id": lan_id, "file_name": rec.file_name, "status": "success"})
                        else:
                            failed_downloads.append({"lan_id": lan_id, "file_name": rec.file_name, "status": "failed", "reason": "NFS access failed"})
                else:
                    failed_downloads.append({"lan_id": lan_id, "status": "failed", "reason": "No recording found for LAN ID"})

            bulk_request.status = "completed"
            bulk_request.completed_at = datetime.now()
            bulk_request.result_json = json.dumps({
                "successful_downloads": successful_downloads,
                "failed_downloads": failed_downloads,
                "total_requested": len(lan_ids),
                "total_processed": len(successful_downloads) + len(failed_downloads)
            })
            self.db.commit()
            logger.info(f"Bulk download request {request_id} completed.")
        except Exception as e:
            self.db.rollback()
            bulk_request.status = "failed"
            bulk_request.completed_at = datetime.now()
            bulk_request.result_json = json.dumps({"error": str(e)})
            self.db.commit()
            logger.error(f"Bulk download request {request_id} failed: {e}")
            raise ServiceUnavailableException(detail=f"Bulk download processing failed: {e}")