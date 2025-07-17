import asyncio
import base64
import csv
import io
import os
import uuid
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, or_
from loguru import logger

from app.models.vkyc_record import VKYCRecord
from app.schemas.vkyc_record import VKYCRecordCreate, VKYCRecordUpdate, BulkUploadRequest, BulkUploadResult, DownloadStatus
from app.core.exceptions import NotFoundException, BadRequestException, ConflictException, InternalServerErrorException
from config import get_settings

settings = get_settings()

class VKYCService:
    """
    Service layer for VKYC record management.
    Handles business logic, database interactions, and simulated NFS operations.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.nfs_base_path = settings.NFS_BASE_PATH
        self.simulated_file_size_bytes = settings.NFS_SIMULATED_FILE_SIZE_MB * 1024 * 1024

    async def get_record_by_id(self, record_id: int) -> VKYCRecord:
        """Fetches a VKYC record by its ID."""
        logger.info(f"Attempting to fetch VKYC record with ID: {record_id}")
        result = await self.db_session.execute(
            select(VKYCRecord).filter(VKYCRecord.id == record_id, VKYCRecord.is_active == True)
        )
        record = result.scalars().first()
        if not record:
            logger.warning(f"VKYC record with ID {record_id} not found.")
            raise NotFoundException(detail=f"VKYC record with ID {record_id} not found.")
        logger.info(f"Successfully fetched VKYC record with ID: {record_id}")
        return record

    async def get_record_by_lan_id(self, lan_id: str) -> VKYCRecord:
        """Fetches a VKYC record by its LAN ID."""
        logger.info(f"Attempting to fetch VKYC record with LAN ID: {lan_id}")
        result = await self.db_session.execute(
            select(VKYCRecord).filter(VKYCRecord.lan_id == lan_id, VKYCRecord.is_active == True)
        )
        record = result.scalars().first()
        if not record:
            logger.warning(f"VKYC record with LAN ID {lan_id} not found.")
            raise NotFoundException(detail=f"VKYC record with LAN ID {lan_id} not found.")
        logger.info(f"Successfully fetched VKYC record with LAN ID: {lan_id}")
        return record

    async def get_all_records(self, skip: int = 0, limit: int = 100, search: str = None) -> List[VKYCRecord]:
        """Fetches all active VKYC records with pagination and optional search."""
        logger.info(f"Fetching VKYC records (skip={skip}, limit={limit}, search='{search}')")
        query = select(VKYCRecord).filter(VKYCRecord.is_active == True)

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    VKYCRecord.lan_id.ilike(search_pattern),
                    VKYCRecord.customer_name.ilike(search_pattern),
                    VKYCRecord.file_path.ilike(search_pattern)
                )
            )

        query = query.offset(skip).limit(limit).order_by(VKYCRecord.recording_date.desc())
        result = await self.db_session.execute(query)
        records = result.scalars().all()
        logger.info(f"Fetched {len(records)} VKYC records.")
        return records

    async def create_record(self, record_data: VKYCRecordCreate) -> VKYCRecord:
        """Creates a new VKYC record."""
        logger.info(f"Attempting to create VKYC record for LAN ID: {record_data.lan_id}")
        # Check for existing LAN ID to prevent duplicates
        existing_record = await self.db_session.execute(
            select(VKYCRecord).filter(VKYCRecord.lan_id == record_data.lan_id)
        )
        if existing_record.scalars().first():
            logger.warning(f"Conflict: VKYC record with LAN ID {record_data.lan_id} already exists.")
            raise ConflictException(detail=f"VKYC record with LAN ID {record_data.lan_id} already exists.")

        new_record = VKYCRecord(**record_data.model_dump())
        self.db_session.add(new_record)
        await self.db_session.commit()
        await self.db_session.refresh(new_record)
        logger.info(f"Successfully created VKYC record with ID: {new_record.id}, LAN ID: {new_record.lan_id}")
        return new_record

    async def update_record(self, record_id: int, record_data: VKYCRecordUpdate) -> VKYCRecord:
        """Updates an existing VKYC record."""
        logger.info(f"Attempting to update VKYC record with ID: {record_id}")
        record = await self.get_record_by_id(record_id) # Reuses get_record_by_id for existence check

        # If LAN ID is being updated, check for conflict with another existing record
        if record_data.lan_id and record_data.lan_id != record.lan_id:
            existing_record = await self.db_session.execute(
                select(VKYCRecord).filter(VKYCRecord.lan_id == record_data.lan_id)
            )
            if existing_record.scalars().first():
                logger.warning(f"Conflict: Cannot update to LAN ID {record_data.lan_id} as it already exists.")
                raise ConflictException(detail=f"LAN ID {record_data.lan_id} already exists for another record.")

        for field, value in record_data.model_dump(exclude_unset=True).items():
            setattr(record, field, value)

        await self.db_session.commit()
        await self.db_session.refresh(record)
        logger.info(f"Successfully updated VKYC record with ID: {record.id}")
        return record

    async def delete_record(self, record_id: int) -> Dict[str, str]:
        """Soft deletes a VKYC record by setting is_active to False."""
        logger.info(f"Attempting to soft delete VKYC record with ID: {record_id}")
        record = await self.get_record_by_id(record_id) # Reuses get_record_by_id for existence check
        record.is_active = False
        await self.db_session.commit()
        logger.info(f"Successfully soft deleted VKYC record with ID: {record.id}")
        return {"message": f"VKYC record with ID {record_id} soft deleted successfully."}

    async def bulk_upload_records(self, upload_request: BulkUploadRequest) -> BulkUploadResult:
        """
        Processes a bulk upload of LAN IDs from a CSV/TXT file.
        Simulates creating VKYC records for each LAN ID.
        """
        logger.info(f"Starting bulk upload for file: {upload_request.file_name}")
        try:
            decoded_content = base64.b64decode(upload_request.file_content).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decode file content: {e}")
            raise BadRequestException(detail="Invalid file content encoding.")

        lan_ids = []
        try:
            # Assuming CSV or TXT with one LAN ID per line
            if upload_request.file_name.endswith('.csv'):
                reader = csv.reader(io.StringIO(decoded_content))
                for row in reader:
                    if row:
                        lan_ids.append(row[0].strip())
            else: # Assume TXT or other plain text, one ID per line
                lan_ids = [line.strip() for line in decoded_content.splitlines() if line.strip()]
        except Exception as e:
            logger.error(f"Failed to parse file content: {e}")
            raise BadRequestException(detail="Failed to parse file content. Ensure it's a valid CSV/TXT.")

        total_processed = len(lan_ids)
        successful_records = []
        failed_records = []

        for lan_id in lan_ids:
            if not lan_id:
                continue # Skip empty lines

            # Basic validation for LAN ID format
            if not (5 <= len(lan_id) <= 50 and (lan_id.isalnum() or '-' in lan_id)):
                failed_records.append({"lan_id": lan_id, "error": "Invalid LAN ID format or length."})
                continue

            try:
                # Simulate creating a record. In a real scenario, this would involve
                # more complex logic, e.g., fetching actual customer data,
                # assigning a real file path, etc.
                record_data = VKYCRecordCreate(
                    lan_id=lan_id,
                    customer_name=f"Customer {lan_id}", # Placeholder
                    file_path=os.path.join(self.nfs_base_path, f"{lan_id}.mp4"), # Simulated path
                    status="completed"
                )
                await self.create_record(record_data)
                successful_records.append(lan_id)
            except ConflictException:
                failed_records.append({"lan_id": lan_id, "error": "Record already exists."})
            except Exception as e:
                logger.error(f"Error processing LAN ID {lan_id} during bulk upload: {e}")
                failed_records.append({"lan_id": lan_id, "error": str(e)})

        logger.info(f"Bulk upload finished. Processed: {total_processed}, Success: {len(successful_records)}, Failed: {len(failed_records)}")
        return BulkUploadResult(
            total_records_processed=total_processed,
            successful_records=successful_records,
            failed_records=failed_records
        )

    async def simulate_nfs_file_download(self, file_path: str) -> bytes:
        """
        Simulates fetching a file from an NFS server.
        In a real application, this would involve actual file system operations
        or a dedicated file streaming service.
        """
        logger.info(f"Simulating NFS file download for path: {file_path}")
        # Simulate file existence check
        if not file_path.startswith(self.nfs_base_path):
            logger.warning(f"Attempted to access file outside NFS base path: {file_path}")
            raise ForbiddenException(detail="Access to specified file path is forbidden.")

        # Simulate a delay for file transfer
        await asyncio.sleep(0.5) # Simulate network latency/file read time

        # Simulate file content (e.g., a dummy video file)
        # For a real video, you'd stream chunks. Here, we just return dummy bytes.
        simulated_content = b"This is a simulated VKYC video recording content." * (self.simulated_file_size_bytes // 50)
        if len(simulated_content) < self.simulated_file_size_bytes:
            simulated_content += b"X" * (self.simulated_file_size_bytes - len(simulated_content))

        logger.info(f"Simulated download of {len(simulated_content)} bytes for {file_path}")
        return simulated_content

    async def bulk_download_records(self, lan_ids: List[str], base_url: str) -> List[DownloadStatus]:
        """
        Initiates a bulk download process for a list of LAN IDs.
        Returns a list of statuses and temporary download URLs.
        """
        logger.info(f"Initiating bulk download for LAN IDs: {lan_ids}")
        results: List[DownloadStatus] = []

        for lan_id in lan_ids:
            try:
                record = await self.get_record_by_lan_id(lan_id)
                # Generate a temporary download URL. In a real system, this might be:
                # 1. A signed S3 URL for temporary access.
                # 2. A temporary token that allows a direct stream from the backend.
                # For this simulation, we'll provide a direct API endpoint URL.
                download_url = f"{base_url}/api/v1/vkyc/{record.id}/download"
                results.append(DownloadStatus(
                    lan_id=lan_id,
                    status="success",
                    message="File ready for download.",
                    download_url=download_url
                ))
            except NotFoundException:
                results.append(DownloadStatus(
                    lan_id=lan_id,
                    status="not_found",
                    message="VKYC record not found."
                ))
            except Exception as e:
                logger.error(f"Error processing download for LAN ID {lan_id}: {e}")
                results.append(DownloadStatus(
                    lan_id=lan_id,
                    status="error",
                    message=f"An error occurred: {str(e)}"
                ))
        logger.info(f"Bulk download status generated for {len(lan_ids)} records.")
        return results