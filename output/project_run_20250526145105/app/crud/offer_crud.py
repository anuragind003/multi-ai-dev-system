from uuid import UUID
from datetime import datetime, date
from typing import List, Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, delete, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, UUID as PG_UUID
from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey

# Assuming models are defined in app.models.models
from app.models.models import Customer, Offer, OfferHistory, CampaignEvent

# Assuming schemas are defined in app.schemas
from app.schemas.offer_schema import OfferCreate, OfferUpdate
from app.schemas.enums import OfferStatusEnum, OfferTypeEnum, ProductTypeEnum

class OfferCRUD:
    def __init__(self):
        pass

    async def create_offer(self, db: AsyncSession, offer_in: OfferCreate) -> Offer:
        """
        Creates a new offer in the database.
        Handles initial offer status based on business logic (e.g., journey started).
        """
        # Ensure customer exists or handle creation/lookup in a higher layer (service)
        # For CRUD, we assume customer_id is valid and exists.
        
        db_offer = Offer(
            offer_id=offer_in.offer_id,
            customer_id=offer_in.customer_id,
            offer_type=offer_in.offer_type.value,
            offer_status=offer_in.offer_status.value,
            product_type=offer_in.product_type.value,
            offer_details=offer_in.offer_details,
            offer_start_date=offer_in.offer_start_date,
            offer_end_date=offer_in.offer_end_date,
            is_journey_started=offer_in.is_journey_started,
            loan_application_id=offer_in.loan_application_id,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(db_offer)
        await db.commit()
        await db.refresh(db_offer)

        # Record initial offer history
        await self._create_offer_history_entry(
            db,
            offer_id=db_offer.offer_id,
            customer_id=db_offer.customer_id,
            old_status=None,
            new_status=db_offer.offer_status,
            reason="Offer Created",
            snapshot_details=db_offer.offer_details
        )
        return db_offer

    async def get_offer_by_id(self, db: AsyncSession, offer_id: UUID) -> Optional[Offer]:
        """
        Retrieves a single offer by its ID.
        """
        result = await db.execute(
            select(Offer).where(Offer.offer_id == offer_id)
        )
        return result.scalars().first()

    async def get_offers_by_customer_id(self, db: AsyncSession, customer_id: UUID) -> List[Offer]:
        """
        Retrieves all offers associated with a specific customer ID.
        """
        result = await db.execute(
            select(Offer).where(Offer.customer_id == customer_id)
        )
        return result.scalars().all()

    async def get_active_offers_by_customer_id(self, db: AsyncSession, customer_id: UUID) -> List[Offer]:
        """
        Retrieves active offers for a given customer.
        'Active' status is defined by OfferStatusEnum.ACTIVE.
        """
        result = await db.execute(
            select(Offer)
            .where(Offer.customer_id == customer_id)
            .where(Offer.offer_status == OfferStatusEnum.ACTIVE.value)
        )
        return result.scalars().all()

    async def update_offer(self, db: AsyncSession, offer_id: UUID, offer_update: OfferUpdate) -> Optional[Offer]:
        """
        Updates an existing offer. Records offer history if status changes.
        """
        current_offer = await self.get_offer_by_id(db, offer_id)
        if not current_offer:
            return None

        old_status = current_offer.offer_status
        update_data = offer_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.now()

        # Convert enum values to string if present in update_data
        if "offer_type" in update_data:
            update_data["offer_type"] = update_data["offer_type"].value
        if "offer_status" in update_data:
            update_data["offer_status"] = update_data["offer_status"].value
        if "product_type" in update_data:
            update_data["product_type"] = update_data["product_type"].value

        stmt = (
            update(Offer)
            .where(Offer.offer_id == offer_id)
            .values(**update_data)
            .returning(Offer)
        )
        result = await db.execute(stmt)
        updated_offer = result.scalars().first()

        if updated_offer:
            await db.commit()
            await db.refresh(updated_offer)

            # Record offer history if status changed
            if updated_offer.offer_status != old_status:
                await self._create_offer_history_entry(
                    db,
                    offer_id=updated_offer.offer_id,
                    customer_id=updated_offer.customer_id,
                    old_status=old_status,
                    new_status=updated_offer.offer_status,
                    reason=f"Offer status changed from {old_status} to {updated_offer.offer_status}",
                    snapshot_details=updated_offer.offer_details
                )
        return updated_offer

    async def mark_offer_as_expired(self, db: AsyncSession, offer_id: UUID, reason: str = "Offer expired by business logic") -> Optional[Offer]:
        """
        Marks an offer as 'Expired'.
        FR18, FR51, FR53
        """
        offer_update = OfferUpdate(offer_status=OfferStatusEnum.EXPIRED)
        return await self.update_offer(db, offer_id, offer_update)

    async def mark_offer_as_duplicate(self, db: AsyncSession, offer_id: UUID, reason: str = "Marked as duplicate during deduplication") -> Optional[Offer]:
        """
        Marks an offer as 'Duplicate'.
        FR20
        """
        offer_update = OfferUpdate(offer_status=OfferStatusEnum.DUPLICATE)
        return await self.update_offer(db, offer_id, offer_update)

    async def set_offer_journey_started(self, db: AsyncSession, offer_id: UUID, loan_application_id: str) -> Optional[Offer]:
        """
        Sets is_journey_started to True and records the loan_application_id.
        FR15, FR21
        """
        offer_update = OfferUpdate(is_journey_started=True, loan_application_id=loan_application_id)
        return await self.update_offer(db, offer_id, offer_update)

    async def _create_offer_history_entry(
        self,
        db: AsyncSession,
        offer_id: UUID,
        customer_id: UUID,
        old_status: Optional[str],
        new_status: str,
        reason: str,
        snapshot_details: Dict[str, Any]
    ) -> OfferHistory:
        """
        Internal helper to create an offer history entry.
        FR23: Maintain offer history for the past 6 months.
        """
        history_entry = OfferHistory(
            offer_id=offer_id,
            customer_id=customer_id,
            change_timestamp=datetime.now(),
            old_offer_status=old_status,
            new_offer_status=new_status,
            change_reason=reason,
            snapshot_offer_details=snapshot_details
        )
        db.add(history_entry)
        await db.commit()
        await db.refresh(history_entry)
        return history_entry

    async def get_offer_history(self, db: AsyncSession, offer_id: UUID, limit: int = 100) -> List[OfferHistory]:
        """
        Retrieves history for a specific offer.
        """
        result = await db.execute(
            select(OfferHistory)
            .where(OfferHistory.offer_id == offer_id)
            .order_by(OfferHistory.change_timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_customer_offer_history(self, db: AsyncSession, customer_id: UUID, limit: int = 100) -> List[OfferHistory]:
        """
        Retrieves all offer history entries for a specific customer.
        """
        result = await db.execute(
            select(OfferHistory)
            .where(OfferHistory.customer_id == customer_id)
            .order_by(OfferHistory.change_timestamp.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_offers_for_moengage_export(self, db: AsyncSession) -> List[Offer]:
        """
        Retrieves offers suitable for Moengage export.
        This typically means active, campaign-ready offers.
        FR54: Generate a Moengage format file in .csv format.
        """
        # This logic might need refinement based on specific Moengage export criteria
        # For now, let's assume active offers that haven't started a journey
        result = await db.execute(
            select(Offer)
            .where(Offer.offer_status == OfferStatusEnum.ACTIVE.value)
            .where(Offer.is_journey_started == False)
            # Add more filters as per Moengage export requirements (e.g., specific offer types)
        )
        return result.scalars().all()

    async def get_offers_by_status(self, db: AsyncSession, status: OfferStatusEnum) -> List[Offer]:
        """
        Retrieves offers by their status.
        """
        result = await db.execute(
            select(Offer).where(Offer.offer_status == status.value)
        )
        return result.scalars().all()

    async def get_offers_by_product_type(self, db: AsyncSession, product_type: ProductTypeEnum) -> List[Offer]:
        """
        Retrieves offers by their product type.
        """
        result = await db.execute(
            select(Offer).where(Offer.product_type == product_type.value)
        )
        return result.scalars().all()

    async def get_offers_by_offer_type(self, db: AsyncSession, offer_type: OfferTypeEnum) -> List[Offer]:
        """
        Retrieves offers by their offer type.
        """
        result = await db.execute(
            select(Offer).where(Offer.offer_type == offer_type.value)
        )
        return result.scalars().all()

    async def get_offers_for_expiry_check(self, db: AsyncSession) -> List[Offer]:
        """
        Retrieves offers that are candidates for expiry based on offer_end_date
        and not having a journey started.
        FR51: Mark offers as expired based on offer end dates for non-journey started customers.
        """
        today = date.today()
        result = await db.execute(
            select(Offer)
            .where(Offer.offer_status == OfferStatusEnum.ACTIVE.value)
            .where(Offer.is_journey_started == False)
            .where(Offer.offer_end_date < today)
        )
        return result.scalars().all()

    async def get_offers_for_lan_expiry_check(self, db: AsyncSession) -> List[Offer]:
        """
        Retrieves offers that are candidates for expiry based on LAN validity.
        FR53: Mark offers as expired within the offers data if the LAN validity post loan application journey start date is over.
        (Note: LAN validity period needs to be defined, assuming it's part of offer_details or a separate field)
        This implementation assumes 'loan_application_id' is present and 'offer_details' might contain LAN validity info.
        A more robust solution would involve joining with LOS data or having a specific LAN validity field.
        For now, this is a placeholder.
        """
        # This is a simplified placeholder. Real LAN validity check would be more complex.
        # It might involve checking a 'loan_application_status' or a 'lan_expiry_date'
        # within the offer_details JSONB, or even querying the LOS system.
        result = await db.execute(
            select(Offer)
            .where(Offer.offer_status == OfferStatusEnum.ACTIVE.value)
            .where(Offer.is_journey_started == True)
            .where(Offer.loan_application_id.isnot(None))
            # Add logic here to check LAN validity, e.g.,
            # .where(Offer.offer_details["lan_validity_date"].astext.cast(Date) < func.current_date())
        )
        return result.scalars().all()

    async def delete_offer_data_older_than(self, db: AsyncSession, months: int) -> int:
        """
        Deletes offer data older than a specified number of months.
        FR37: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
        This is a hard delete, use with caution. Consider soft delete (status change) first.
        """
        cutoff_date = datetime.now() - func.interval(f'{months} months')
        stmt = delete(Offer).where(Offer.created_at < cutoff_date)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def delete_offer_history_older_than(self, db: AsyncSession, months: int) -> int:
        """
        Deletes offer history data older than a specified number of months.
        FR23: Maintain offer history for the past 6 months for reference purposes.
        """
        cutoff_date = datetime.now() - func.interval(f'{months} months')
        stmt = delete(OfferHistory).where(OfferHistory.change_timestamp < cutoff_date)
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

# Instantiate the CRUD class for use in other modules
offer_crud = OfferCRUD()