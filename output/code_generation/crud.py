from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from models import VKYCRecord
from schemas import VKYCRecordCreate, VKYCSearchRequest
from utils.exceptions import ServiceException, NotFoundException
from utils.logger import get_logger

logger = get_logger(__name__)

class VKYCCrud:
    """
    CRUD operations for VKYC records.
    Handles all database interactions for VKYCRecord model.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_record_by_lan_id(self, lan_id: str) -> Optional[VKYCRecord]:
        """
        Retrieves a single VKYC record by its LAN ID.
        """
        try:
            stmt = select(VKYCRecord).where(VKYCRecord.lan_id == lan_id)
            result = await self.db_session.execute(stmt)
            record = result.scalars().first()
            return record
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching record by LAN ID {lan_id}: {e}", exc_info=True)
            raise ServiceException(f"Failed to retrieve record for LAN ID {lan_id}.")

    async def search_records(
        self, search_params: VKYCSearchRequest
    ) -> Tuple[List[VKYCRecord], int]:
        """
        Searches VKYC records based on provided criteria with pagination.
        Returns a tuple of (list of records, total count).
        """
        try:
            query = select(VKYCRecord)

            if search_params.lan_id:
                query = query.where(VKYCRecord.lan_id.ilike(f"%{search_params.lan_id}%"))
            if search_params.start_date:
                query = query.where(VKYCRecord.upload_date >= search_params.start_date)
            if search_params.end_date:
                # Add one day to end_date to include records from the entire end_date
                query = query.where(VKYCRecord.upload_date < (search_params.end_date + func.cast('1 day', VKYCRecord.upload_date.type)))
            if search_params.status:
                query = query.where(VKYCRecord.status == search_params.status)
            if search_params.agent_id:
                query = query.where(VKYCRecord.agent_id.ilike(f"%{search_params.agent_id}%"))
            if search_params.customer_name:
                query = query.where(VKYCRecord.customer_name.ilike(f"%{search_params.customer_name}%"))

            # Count total records matching the filter
            count_query = select(func.count()).select_from(query.subquery())
            total_records_result = await self.db_session.execute(count_query)
            total_records = total_records_result.scalar_one()

            # Apply pagination
            query = query.offset((search_params.page - 1) * search_params.page_size).limit(search_params.page_size)
            query = query.order_by(VKYCRecord.upload_date.desc()) # Order by latest first

            result = await self.db_session.execute(query)
            records = result.scalars().all()

            return records, total_records
        except SQLAlchemyError as e:
            logger.error(f"Database error during record search: {e}", exc_info=True)
            raise ServiceException("Failed to search records due to a database error.")

    async def create_record(self, record_data: VKYCRecordCreate) -> VKYCRecord:
        """
        Creates a new VKYC record in the database.
        """
        try:
            new_record = VKYCRecord(**record_data.model_dump())
            self.db_session.add(new_record)
            await self.db_session.commit()
            await self.db_session.refresh(new_record)
            return new_record
        except SQLAlchemyError as e:
            logger.error(f"Database error creating record for LAN ID {record_data.lan_id}: {e}", exc_info=True)
            await self.db_session.rollback()
            raise ServiceException(f"Failed to create record for LAN ID {record_data.lan_id}.")

    async def update_record_status(self, lan_id: str, new_status: str) -> VKYCRecord:
        """
        Updates the status of a VKYC record.
        """
        try:
            record = await self.get_record_by_lan_id(lan_id)
            if not record:
                raise NotFoundException(f"VKYC record with LAN ID '{lan_id}' not found.")
            record.status = new_status
            await self.db_session.commit()
            await self.db_session.refresh(record)
            return record
        except SQLAlchemyError as e:
            logger.error(f"Database error updating status for LAN ID {lan_id}: {e}", exc_info=True)
            await self.db_session.rollback()
            raise ServiceException(f"Failed to update status for LAN ID {lan_id}.")