from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models.recording import Recording
from app.schemas.recordings import RecordingFilter
from app.utils.logger import logger

class RecordingCRUD:
    """
    CRUD operations for VKYC Recordings.
    """
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_recording_by_id(self, recording_id: str) -> Optional[Recording]:
        """Retrieve a single recording by its unique recording_id."""
        try:
            result = await self.db_session.execute(
                select(Recording).filter(Recording.recording_id == recording_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching recording by ID {recording_id}: {e}")
            raise

    async def get_recordings(
        self,
        filters: RecordingFilter,
        skip: int = 0,
        limit: int = 10
    ) -> Tuple[List[Recording], int]:
        """
        Retrieve a list of recordings with optional filters and pagination.
        Returns a tuple of (list of recordings, total count).
        """
        query = select(Recording)
        count_query = select(func.count()).select_from(Recording)
        conditions = []

        if filters.lan_id:
            conditions.append(Recording.lan_id.ilike(f"%{filters.lan_id}%"))
        if filters.start_date:
            conditions.append(Recording.recorded_at >= filters.start_date)
        if filters.end_date:
            conditions.append(Recording.recorded_at <= filters.end_date)
        if filters.status:
            conditions.append(Recording.status == filters.status)
        if filters.agent_id:
            conditions.append(Recording.agent_id.ilike(f"%{filters.agent_id}%"))
        if filters.customer_name:
            conditions.append(Recording.customer_name.ilike(f"%{filters.customer_name}%"))

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        try:
            # Get total count
            total_count_result = await self.db_session.execute(count_query)
            total_count = total_count_result.scalar_one()

            # Get paginated items
            query = query.offset(skip).limit(limit).order_by(Recording.recorded_at.desc())
            result = await self.db_session.execute(query)
            recordings = result.scalars().all()

            return recordings, total_count
        except Exception as e:
            logger.error(f"Error fetching recordings: {e}")
            raise

    async def get_recordings_by_lan_ids(self, lan_ids: List[str]) -> List[Recording]:
        """Retrieve recordings for a list of LAN IDs."""
        try:
            result = await self.db_session.execute(
                select(Recording).filter(Recording.lan_id.in_(lan_ids))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching recordings by LAN IDs {lan_ids}: {e}")
            raise

    async def create_recording(self, recording_data: dict) -> Recording:
        """Create a new recording entry in the database."""
        try:
            new_recording = Recording(**recording_data)
            self.db_session.add(new_recording)
            await self.db_session.commit()
            await self.db_session.refresh(new_recording)
            return new_recording
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error creating recording: {e}")
            raise