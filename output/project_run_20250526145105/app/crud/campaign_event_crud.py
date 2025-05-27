import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_event import CampaignEvent
from app.schemas.campaign_event_schema import CampaignEventCreate, CampaignEventResponse


async def create_campaign_event(
    db: AsyncSession, event_in: CampaignEventCreate
) -> CampaignEvent:
    """
    Creates a new campaign event record in the database.
    """
    db_event = CampaignEvent(
        event_id=uuid.uuid4(),
        customer_id=event_in.customer_id,
        offer_id=event_in.offer_id,
        event_source=event_in.event_source,
        event_type=event_in.event_type,
        event_details=event_in.event_details,
        event_timestamp=datetime.utcnow(),  # Use UTC for consistency
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def get_campaign_event_by_id(
    db: AsyncSession, event_id: uuid.UUID
) -> Optional[CampaignEvent]:
    """
    Retrieves a single campaign event by its ID.
    """
    result = await db.execute(
        select(CampaignEvent).where(CampaignEvent.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def get_campaign_events_for_customer(
    db: AsyncSession, customer_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> List[CampaignEvent]:
    """
    Retrieves a list of campaign events for a specific customer, with pagination.
    """
    result = await db.execute(
        select(CampaignEvent)
        .where(CampaignEvent.customer_id == customer_id)
        .offset(skip)
        .limit(limit)
        .order_by(CampaignEvent.event_timestamp.desc())
    )
    return result.scalars().all()


async def get_campaign_events_by_filters(
    db: AsyncSession,
    event_source: Optional[str] = None,
    event_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[CampaignEvent]:
    """
    Retrieves a list of campaign events based on various filters, with pagination.
    Filters include event source, event type, and a date range for event timestamp.
    """
    query = select(CampaignEvent)

    if event_source:
        query = query.where(CampaignEvent.event_source == event_source)
    if event_type:
        query = query.where(CampaignEvent.event_type == event_type)
    if start_date:
        query = query.where(CampaignEvent.event_timestamp >= start_date)
    if end_date:
        query = query.where(CampaignEvent.event_timestamp <= end_date)

    query = query.offset(skip).limit(limit).order_by(CampaignEvent.event_timestamp.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def delete_campaign_event(db: AsyncSession, event_id: uuid.UUID) -> Optional[uuid.UUID]:
    """
    Deletes a campaign event by its ID.
    Returns the ID of the deleted event if successful, None otherwise.
    """
    event = await get_campaign_event_by_id(db, event_id)
    if event:
        await db.delete(event)
        await db.commit()
        return event_id
    return None