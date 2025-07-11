import logging
import os
import asyncio
import zipfile
import io
from typing import List, Optional, Tuple
from datetime import datetime

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.models import VKYCRecording
from app.schemas import VKYCSearchRequest, VKYCRecordingResponse
from app.exceptions import NotFoundException, ServiceUnavailableException, FileOperationException
from app.utils.cache import SimpleCache # Using a simple in-memory cache

logger = logging.getLogger(__name__)

# Initialize a simple in-memory cache for search results
search_cache = SimpleCache(ttl=settings.CACHE_TTL_SECONDS)

class VKYCService:
    """
    Business logic service for VKYC recording operations.
    Handles search, single download, and bulk download.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_recordings(self, request: VKYCSearchRequest) -> Tuple[List[VKYCRecordingResponse], int]:
        """
        Searches VKYC recordings based on various criteria with pagination.
        Includes caching for performance optimization.
        """
        cache_key = f"search:{request.model_dump_json()}"
        cached_result = search_cache.get(cache_key)
        if cached_result:
            logger.info(f"Serving search results from cache for query: {request.query}")
            return cached_result

        logger.info(f"Searching recordings with criteria: {request.model_dump()}")
        
        query_filters = []
        if request.query:
            # General search across multiple fields
            query_filters.append(or_(
                VKYCRecording.lan_id.ilike(f"%{request.query}%"),
                VKYCRecording.customer_name.ilike(f"%{request.query}%"),
                VKYCRecording.agent_id.ilike(f"%{request.query}%")
            ))
        if request.lan_id:
            query_filters.append(VKYCRecording.lan_id.ilike(f"%{request.lan_id}%"))
        if request.agent_id:
            query_filters.append(VKYCRecording.agent_id.ilike(f"%{request.agent_id}%"))
        if request.customer_name:
            query_filters.append(VKYCRecording.customer_name.ilike(f"%{request.customer_name}%"))
        if request.status:
            query_filters.append(VKYCRecording.status == request.status)
        
        if request.start_date and request.end_date:
            # Validate date format (YYYY-MM-DD)
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
                datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationException(detail="Invalid date format. Use YYYY-MM-DD.")
            query_filters.append(and_(
                VKYCRecording.upload_date >= request.start_date,
                VKYCRecording.upload_date <= request.end_date
            ))
        elif request.start_date:
            try:
                datetime.strptime(request.start_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationException(detail="Invalid start_date format. Use YYYY-MM-DD.")
            query_filters.append(VKYCRecording.upload_date >= request.start_date)
        elif request.end_date:
            try:
                datetime.strptime(request.end_date, "%Y-%m-%d")
            except ValueError:
                raise ValidationException(detail="Invalid end_date format. Use YYYY-MM-DD.")
            query_filters.append(VKYCRecording.upload_date <= request.end_date)

        try:
            # Count total records
            count_stmt = select(VKYCRecording).filter(*query_filters)
            total_records_result = await self.db.execute(count_stmt)
            total_records = len(total_records_result.scalars().all())

            # Fetch paginated records
            offset = (request.page - 1) * request.page_size
            stmt = select(VKYCRecording).filter(*query_filters).offset(offset).limit(request.page_size)
            result = await self.db.execute(stmt)
            recordings = result.scalars().all()

            response_records = [VKYCRecordingResponse.model_validate(rec) for rec in recordings]
            
            search_cache.set(cache_key, (response_records, total_records))
            logger.info(f"Found {len(response_records)} records (total: {total_records}) for query: {request.query}")
            return response_records, total_records
        except SQLAlchemyError as e:
            logger.error(f"Database error during search: {e}", exc_info=True)
            raise ServiceUnavailableException(detail="Database service is unavailable.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during search: {e}", exc_info=True)
            raise

    async def get_recording_by_lan_id(self, lan_id: str) -> VKYCRecording:
        """
        Retrieves a single VKYC recording by its LAN ID.
        """
        logger.info(f"Fetching recording for LAN ID: {lan_id}")
        try:
            stmt = select(VKYCRecording).where(VKYCRecording.lan_id == lan_id)
            result = await self.db.execute(stmt)
            recording = result.scalars().first()
            if not recording:
                logger.warning(f"Recording with LAN ID '{lan_id}' not found.")
                raise NotFoundException(detail=f"Recording with LAN ID '{lan_id}' not found.")
            return recording
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching recording by LAN ID: {e}", exc_info=True)
            raise ServiceUnavailableException(detail="Database service is unavailable.")
        except Exception as e:
            logger.error(f"An unexpected error occurred fetching recording by LAN ID: {e}", exc_info=True)
            raise

    async def download_recording(self, lan_id: str) -> Tuple[str, str]:
        """
        Simulates downloading a single VKYC recording file from NFS.
        Returns the full file path and the filename.
        """
        recording = await self.get_recording_by_lan_id(lan_id)
        
        file_full_path = os.path.join(settings.NFS_SIMULATION_PATH, recording.file_path)
        file_name = recording.file_path

        if not os.path.exists(file_full_path):
            logger.error(f"File not found on simulated NFS: {file_full_path}")
            raise FileOperationException(detail=f"Recording file for LAN ID '{lan_id}' not found.", status_code=404)
        
        # Simulate network/disk latency
        if settings.NFS_SIMULATION_DELAY_MS > 0:
            await asyncio.sleep(settings.NFS_SIMULATION_DELAY_MS / 1000)
        
        logger.info(f"Simulated download of file: {file_full_path}")
        return file_full_path, file_name

    async def bulk_download_recordings(self, lan_ids: List[str]) -> Tuple[io.BytesIO, str]:
        """
        Simulates bulk downloading multiple VKYC recording files from NFS
        and zipping them into a single archive.
        """
        if not lan_ids:
            raise ValidationException(detail="No LAN IDs provided for bulk download.")
        if len(lan_ids) > 10:
            raise ValidationException(detail="Maximum 10 LAN IDs allowed for bulk download.")

        logger.info(f"Initiating bulk download for LAN IDs: {lan_ids}")
        
        zip_buffer = io.BytesIO()
        zip_file_name = f"vkyc_recordings_bulk_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        
        found_files = []
        missing_lan_ids = []

        for lan_id in lan_ids:
            try:
                recording = await self.get_recording_by_lan_id(lan_id)
                file_full_path = os.path.join(settings.NFS_SIMULATION_PATH, recording.file_path)
                if os.path.exists(file_full_path):
                    found_files.append((file_full_path, recording.file_path))
                else:
                    logger.warning(f"File for LAN ID '{lan_id}' not found on simulated NFS: {file_full_path}")
                    missing_lan_ids.append(lan_id)
            except NotFoundException:
                logger.warning(f"Recording metadata for LAN ID '{lan_id}' not found in DB.")
                missing_lan_ids.append(lan_id)
            except Exception as e:
                logger.error(f"Error processing LAN ID '{lan_id}' for bulk download: {e}", exc_info=True)
                missing_lan_ids.append(lan_id)

        if not found_files:
            if missing_lan_ids:
                raise NotFoundException(detail=f"No files found for the provided LAN IDs. Missing: {', '.join(missing_lan_ids)}")
            else:
                raise FileOperationException(detail="No files available for download.", status_code=500)

        try:
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for full_path, file_name in found_files:
                    # Simulate network/disk latency for each file
                    if settings.NFS_SIMULATION_DELAY_MS > 0:
                        await asyncio.sleep(settings.NFS_SIMULATION_DELAY_MS / 1000)
                    zf.write(full_path, arcname=file_name)
            
            zip_buffer.seek(0) # Rewind the buffer to the beginning
            logger.info(f"Successfully created zip file with {len(found_files)} recordings. Missing: {missing_lan_ids}")
            return zip_buffer, zip_file_name
        except Exception as e:
            logger.error(f"Error creating zip file for bulk download: {e}", exc_info=True)
            raise FileOperationException(detail="Failed to create bulk download archive.")