import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.bulk_download import DownloadRequest, FileMetadata
from app.schemas.bulk_download import BulkDownloadRequest, BulkDownloadResponse, FileMetadataSchema, DownloadStatus
from app.core.exceptions import NotFoundException, ServiceUnavailableException, BadRequestException
from app.utils.file_operations import check_file_exists, get_file_metadata, generate_mock_file_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

class BulkDownloadService:
    """
    Service layer for handling bulk download requests.
    Encapsulates business logic, interacts with database and file system (NFS simulation).
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def process_bulk_request(self, request_data: BulkDownloadRequest, requested_by: str) -> BulkDownloadResponse:
        """
        Processes a new bulk download request.
        - Creates a new download request record.
        - Iterates through LAN IDs, checks file existence and fetches metadata (simulated NFS).
        - Updates the request status and stores individual file metadata.
        """
        request_id = str(uuid.uuid4())
        total_lan_ids = len(request_data.lan_ids)

        # 1. Create initial download request record
        new_request = DownloadRequest(
            id=request_id,
            status=DownloadStatus.PROCESSING.value,
            requested_by=requested_by,
            total_lan_ids=total_lan_ids
        )
        self.db_session.add(new_request)
        await self.db_session.commit()
        await self.db_session.refresh(new_request) # Refresh to get default values like requested_at

        processed_files_data: List[FileMetadataSchema] = []
        successful_files_count = 0

        # 2. Process each LAN ID
        for lan_id in request_data.lan_ids:
            file_path = generate_mock_file_path(lan_id) # Simulate path generation
            file_exists = False
            file_size_bytes = None
            last_modified_at = None
            error_message = None

            try:
                # Simulate NFS interaction
                file_exists = await check_file_exists(file_path)
                if file_exists:
                    metadata = await get_file_metadata(file_path)
                    file_size_bytes = metadata.get("size")
                    last_modified_at = metadata.get("last_modified")
                    successful_files_count += 1
                else:
                    error_message = "File not found on NFS."
                    logger.warning(f"File not found for LAN ID: {lan_id} at {file_path}")

            except ServiceUnavailableException as e:
                error_message = f"NFS service unavailable: {e.message}"
                logger.error(f"NFS service unavailable during processing for LAN ID {lan_id}: {e}")
            except Exception as e:
                error_message = f"Unexpected error during file check: {str(e)}"
                logger.error(f"Unexpected error for LAN ID {lan_id}: {e}", exc_info=True)

            file_metadata_record = FileMetadata(
                request_id=request_id,
                lan_id=lan_id,
                file_path=file_path,
                file_exists=file_exists,
                file_size_bytes=file_size_bytes,
                last_modified_at=last_modified_at,
                error_message=error_message
            )
            self.db_session.add(file_metadata_record)
            processed_files_data.append(FileMetadataSchema.model_validate(file_metadata_record))

        # 3. Update request status
        new_request.processed_at = datetime.now(timezone.utc)
        if successful_files_count == total_lan_ids:
            new_request.status = DownloadStatus.COMPLETED.value
        elif successful_files_count > 0:
            new_request.status = DownloadStatus.PARTIAL_SUCCESS.value
        else:
            new_request.status = DownloadStatus.FAILED.value
        
        await self.db_session.commit()
        await self.db_session.refresh(new_request)

        logger.info(f"Bulk download request {request_id} processed with status: {new_request.status}")
        return BulkDownloadResponse(
            request_id=new_request.id,
            status=DownloadStatus(new_request.status),
            requested_at=new_request.requested_at,
            processed_at=new_request.processed_at,
            total_lan_ids=new_request.total_lan_ids,
            processed_files=processed_files_data
        )

    async def get_bulk_request_status(self, request_id: str) -> BulkDownloadResponse:
        """
        Retrieves the status and results of a specific bulk download request.
        """
        stmt = select(DownloadRequest).where(DownloadRequest.id == request_id)
        result = await self.db_session.execute(stmt)
        download_request = result.scalar_one_or_none()

        if not download_request:
            raise NotFoundException(resource_name="Bulk Download Request", details={"request_id": request_id})

        # Load related file metadata
        await self.db_session.refresh(download_request, attribute_names=["files_metadata"])

        processed_files_schema = [
            FileMetadataSchema.model_validate(file_meta)
            for file_meta in download_request.files_metadata
        ]

        return BulkDownloadResponse(
            request_id=download_request.id,
            status=DownloadStatus(download_request.status),
            requested_at=download_request.requested_at,
            processed_at=download_request.processed_at,
            total_lan_ids=download_request.total_lan_ids,
            processed_files=processed_files_schema
        )