import io
import csv
import json
from datetime import date, datetime, timezone
from typing import List, Dict, Optional, Union
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, func, and_
from sqlalchemy.sql import or_ # Import or_ for OR conditions

from app.database import get_db
from app.models.models import Customer, Offer, OfferHistory, CampaignEvent
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.offer import OfferCreate, OfferUpdate, OfferStatus
from app.schemas.integration import OffermartRecord, RealtimeLeadData, MoengageRecord

# Define a simple logger for demonstration purposes
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

class IntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_customer_by_identifiers(self, data: Dict) -> Optional[Customer]:
        """
        Helper to find an existing customer by various identifiers.
        Prioritizes unique identifiers.
        """
        query_conditions = []
        if data.get("mobile_number"):
            query_conditions.append(Customer.mobile_number == data["mobile_number"])
        if data.get("pan_number"):
            query_conditions.append(Customer.pan_number == data["pan_number"])
        if data.get("aadhaar_ref_number"):
            query_conditions.append(Customer.aadhaar_ref_number == data["aadhaar_ref_number"])
        if data.get("ucid_number"):
            query_conditions.append(Customer.ucid_number == data["ucid_number"])
        if data.get("previous_loan_app_number"):
            query_conditions.append(Customer.previous_loan_app_number == data["previous_loan_app_number"])

        if not query_conditions:
            return None

        # Combine conditions with OR
        stmt = select(Customer).where(or_(*query_conditions))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _deduplicate_and_get_or_create_customer(self, customer_data: Dict) -> Customer:
        """
        Deduplicates customer based on FR3, FR4, FR5.
        FR5 (Customer 360) is assumed to be handled by checking within CDP's customer table
        as a proxy for "live book".
        """
        existing_customer = await self._get_customer_by_identifiers(customer_data)

        if existing_customer:
            logger.info(f"Deduplication: Found existing customer {existing_customer.customer_id}")
            # Update existing customer attributes if necessary
            update_data = {k: v for k, v in customer_data.items() if v is not None and hasattr(existing_customer, k) and getattr(existing_customer, k) != v}
            if update_data:
                update_data["updated_at"] = datetime.now(timezone.utc)
                stmt = update(Customer).where(Customer.customer_id == existing_customer.customer_id).values(**update_data)
                await self.db.execute(stmt)
                await self.db.refresh(existing_customer)
                logger.info(f"Updated existing customer {existing_customer.customer_id} with new data.")
            return existing_customer
        else:
            new_customer_id = uuid4()
            customer_create_data = CustomerCreate(
                customer_id=new_customer_id,
                mobile_number=customer_data.get("mobile_number"),
                pan_number=customer_data.get("pan_number"),
                aadhaar_ref_number=customer_data.get("aadhaar_ref_number"),
                ucid_number=customer_data.get("ucid_number"),
                previous_loan_app_number=customer_data.get("previous_loan_app_number"),
                customer_attributes=customer_data.get("customer_attributes", {}),
                customer_segments=customer_data.get("customer_segments", []),
                propensity_flag=customer_data.get("propensity_flag"),
                dnd_status=customer_data.get("dnd_status", False)
            )
            new_customer = Customer(**customer_create_data.dict())
            self.db.add(new_customer)
            await self.db.flush() # To get the customer_id if not explicitly set
            logger.info(f"Deduplication: Created new customer {new_customer.customer_id}")
            return new_customer

    async def _apply_offer_precedence_and_status(self, customer: Customer, new_offer_data: Dict) -> Optional[Dict]:
        """
        Applies offer precedence rules (FR15, FR16, FR25-FR32) and sets initial status (FR18).
        Returns the offer data to be created/updated, or None if the new offer cannot be uploaded.
        """
        new_offer_product_type = new_offer_data.get("product_type")
        new_offer_is_insta_cleag = new_offer_product_type in ["Insta", "E-aggregator"]

        # Fetch all active offers for the customer
        stmt = select(Offer).where(
            and_(
                Offer.customer_id == customer.customer_id,
                Offer.offer_status == OfferStatus.ACTIVE.value
            )
        )
        active_offers = (await self.db.execute(stmt)).scalars().all()

        # FR15: Prevent modification if loan application journey started
        # If an existing offer has journey started, it takes precedence.
        for existing_offer in active_offers:
            if existing_offer.is_journey_started:
                # FR26, FR27, FR28: If journey started, new offer should not replace.
                logger.warning(f"Customer {customer.customer_id} has an active offer ({existing_offer.offer_id}) with journey started. New offer for {new_offer_product_type} will not prevail.")
                # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
                if new_offer_data.get("offer_type") == "Enrich":
                    logger.warning(f"Enrich offer for customer {customer.customer_id} cannot flow as journey has started for existing offer.")
                    return None # New offer cannot be uploaded/processed

                # For other cases, the new offer might be marked as duplicate or inactive,
                # but for now, we'll simply prevent it from becoming active.
                new_offer_data["offer_status"] = OfferStatus.INACTIVE.value # Or DUPLICATE
                return new_offer_data # Allow creation but as inactive/duplicate

        # FR29-FR32: Strict "cannot be uploaded" rules based on existing offer types
        # Define a simplified precedence order for "cannot upload" scenarios:
        # Higher number means higher precedence.
        product_precedence = {
            "Employee Loan": 5,
            "TW Loyalty": 4,
            "Top-up": 3,
            "Preapproved": 2, # Covers Pre-approved E-aggregator and Prospect
            "E-aggregator": 2,
            "Prospect": 1,
            "Insta": 0 # Insta/CLEAG are generally considered new leads, often overriding lower priority
        }

        new_offer_priority = product_precedence.get(new_offer_product_type, -1)

        for existing_offer in active_offers:
            existing_offer_priority = product_precedence.get(existing_offer.product_type, -1)

            if new_offer_is_insta_cleag:
                if existing_offer.product_type in ["Preapproved", "Prospect", "E-aggregator"] and not existing_offer.is_journey_started:
                    # FR25: If pre-approved base (prospect or E-aggregator) with no journey started,
                    # and same customer comes via CLEAG/Insta, CLEAG/Insta journey shall prevail,
                    # and the uploaded pre-approved offer will expire.
                    logger.info(f"FR25: New Insta/E-aggregator offer ({new_offer_product_type}) prevails over existing non-journey pre-approved offer ({existing_offer.product_type}). Expiring old offer.")
                    await self._update_offer_status(existing_offer.offer_id, OfferStatus.EXPIRED, "Replaced by new Insta/E-aggregator offer (FR25)")
                    # Continue checking other active offers, but this one is handled.
                else:
                    # If existing is not pre-approved or has journey started, Insta/CLEAG might not prevail.
                    # If an existing offer is active and has a higher or equal priority,
                    # and it's not a non-journey pre-approved offer being overridden by Insta/CLEAG,
                    # then the new offer is marked as duplicate/inactive.
                    if existing_offer_priority >= new_offer_priority:
                        logger.warning(f"New offer ({new_offer_product_type}) cannot be uploaded as existing offer ({existing_offer.product_type}) has higher or equal precedence and is active.")
                        new_offer_data["offer_status"] = OfferStatus.DUPLICATE.value
                        return new_offer_data # Allow creation but as duplicate
            else:
                # For non-Insta/CLEAG new offers, apply strict "cannot upload" rules
                # If existing offer has higher or equal priority, new offer cannot be uploaded.
                if existing_offer_priority >= new_offer_priority:
                    logger.warning(f"New offer ({new_offer_product_type}) cannot be uploaded as existing offer ({existing_offer.product_type}) has higher or equal precedence and is active.")
                    return None # New offer cannot be uploaded at all

        # FR20: If an Enrich offer's journey has not started, it shall flow to CDP, and the previous offer will be moved to Duplicate.
        if new_offer_data.get("offer_type") == "Enrich":
            # Find previous active offer for the same customer and product type, if any, that has no journey started
            stmt = select(Offer).where(
                and_(
                    Offer.customer_id == customer.customer_id,
                    Offer.product_type == new_offer_product_type,
                    Offer.offer_status == OfferStatus.ACTIVE.value,
                    Offer.is_journey_started == False
                )
            )
            previous_offer = (await self.db.execute(stmt)).scalars().first()
            if previous_offer:
                logger.info(f"FR20: Enrich offer for {new_offer_product_type}. Moving previous offer {previous_offer.offer_id} to Duplicate.")
                await self._update_offer_status(previous_offer.offer_id, OfferStatus.DUPLICATE, "Replaced by Enrich offer (FR20)")

        # If no specific rule prevented upload or marked as duplicate, default to Active
        if "offer_status" not in new_offer_data:
            new_offer_data["offer_status"] = OfferStatus.ACTIVE.value

        return new_offer_data

    async def _update_offer_status(self, offer_id: UUID, new_status: OfferStatus, reason: str = None):
        """Helper to update offer status and log history."""
        stmt = select(Offer).where(Offer.offer_id == offer_id)
        offer = (await self.db.execute(stmt)).scalars().first()

        if offer and offer.offer_status != new_status.value:
            old_status = offer.offer_status
            offer.offer_status = new_status.value
            offer.updated_at = datetime.now(timezone.utc)
            self.db.add(offer) # Mark for update

            # Log offer history (FR23)
            history_entry = OfferHistory(
                history_id=uuid4(),
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=old_status,
                new_offer_status=new_status.value,
                change_reason=reason,
                snapshot_offer_details=offer.offer_details # Snapshot current details
            )
            self.db.add(history_entry)
            logger.info(f"Offer {offer_id} status changed from {old_status} to {new_status.value}. Reason: {reason}")
            await self.db.flush() # Ensure changes are flushed before commit

    async def process_offermart_daily_feed(self, records: List[OffermartRecord]) -> Dict:
        """
        Processes daily batch data from Offermart (FR9, NFR5).
        Performs basic column-level validation (FR1, NFR3), deduplication (FR2-FR6),
        and applies offer precedence rules (FR25-FR32).
        """
        processed_count = 0
        success_count = 0
        error_count = 0
        errors = []

        for record_data in records:
            try:
                # Basic column-level validation (FR1, NFR3)
                # Pydantic schema `OffermartRecord` handles initial validation.
                if not record_data.mobile_number and not record_data.pan_number and not record_data.aadhaar_ref_number and \
                   not record_data.ucid_number and not record_data.previous_loan_app_number:
                    raise ValueError("Record must have at least one unique identifier (mobile, pan, aadhaar, UCID, previous loan app number).")

                # 1. Deduplicate and get/create customer (FR2-FR6)
                customer_data = record_data.customer_data.dict(exclude_unset=True) if record_data.customer_data else {}
                customer_data.update({
                    "mobile_number": record_data.mobile_number,
                    "pan_number": record_data.pan_number,
                    "aadhaar_ref_number": record_data.aadhaar_ref_number,
                    "ucid_number": record_data.ucid_number,
                    "previous_loan_app_number": record_data.previous_loan_app_number,
                    "dnd_status": record_data.dnd_status # FR34: Avoid DND customers - this flag is stored. Actual avoidance logic is in Moengage file generation.
                })
                customer = await self._deduplicate_and_get_or_create_customer(customer_data)

                # 2. Process offer data
                offer_data = record_data.offer_data.dict(exclude_unset=True) if record_data.offer_data else {}
                offer_data.update({
                    "customer_id": customer.customer_id,
                    "product_type": record_data.product_type,
                    "offer_type": record_data.offer_type,
                    "offer_start_date": record_data.offer_start_date,
                    "offer_end_date": record_data.offer_end_date,
                    "is_journey_started": record_data.is_journey_started,
                    "loan_application_id": record_data.loan_application_id
                })

                # Apply offer precedence and determine final status (FR15, FR16, FR18, FR20, FR21, FR25-FR32)
                processed_offer_data = await self._apply_offer_precedence_and_status(customer, offer_data)

                if processed_offer_data is None:
                    # Offer cannot be uploaded due to precedence rules
                    error_count += 1
                    errors.append({"record": record_data.dict(), "error": "Offer cannot be uploaded due to precedence rules."})
                    continue

                # Check if an existing offer needs to be updated (FR8)
                # This implies finding an existing offer for the same customer and product type.
                existing_offer_stmt = select(Offer).where(
                    and_(
                        Offer.customer_id == customer.customer_id,
                        Offer.product_type == processed_offer_data["product_type"],
                        Offer.offer_status == OfferStatus.ACTIVE.value # Only consider active offers for update
                    )
                )
                existing_offer = (await self.db.execute(existing_offer_stmt)).scalars().first()

                if existing_offer:
                    # FR8: Update old offers in Analytics Offermart with new data received from CDP
                    # This means updating the existing offer in CDP DB.
                    logger.info(f"Updating existing offer {existing_offer.offer_id} for customer {customer.customer_id}.")
                    update_values = {
                        k: v for k, v in processed_offer_data.items()
                        if k in Offer.__table__.columns.keys() and k not in ["offer_id", "customer_id", "created_at"]
                    }
                    update_values["updated_at"] = datetime.now(timezone.utc)
                    stmt = update(Offer).where(Offer.offer_id == existing_offer.offer_id).values(**update_values)
                    await self.db.execute(stmt)
                    await self._update_offer_status(existing_offer.offer_id, OfferStatus(processed_offer_data["offer_status"]), "Offer updated from Offermart feed")
                else:
                    # Create new offer
                    new_offer_id = uuid4()
                    offer_create_data = OfferCreate(
                        offer_id=new_offer_id,
                        customer_id=customer.customer_id,
                        offer_type=processed_offer_data.get("offer_type"),
                        offer_status=processed_offer_data.get("offer_status"),
                        product_type=processed_offer_data.get("product_type"),
                        offer_details=processed_offer_data.get("offer_details", {}),
                        offer_start_date=processed_offer_data.get("offer_start_date"),
                        offer_end_date=processed_offer_data.get("offer_end_date"),
                        is_journey_started=processed_offer_data.get("is_journey_started", False),
                        loan_application_id=processed_offer_data.get("loan_application_id")
                    )
                    new_offer = Offer(**offer_create_data.dict())
                    self.db.add(new_offer)
                    await self.db.flush() # To get the offer_id if not explicitly set
                    logger.info(f"Created new offer {new_offer.offer_id} for customer {customer.customer_id}.")
                    # Log initial offer status
                    await self._update_offer_status(new_offer.offer_id, OfferStatus(new_offer.offer_status), "New offer created from Offermart feed")

                success_count += 1

            except Exception as e:
                error_count += 1
                errors.append({"record": record_data.dict(), "error": str(e)})
                logger.error(f"Error processing Offermart record: {e}", exc_info=True)
            finally:
                processed_count += 1

        await self.db.commit() # Commit all changes for the batch
        logger.info(f"Offermart feed processing complete. Processed: {processed_count}, Success: {success_count}, Errors: {error_count}")
        return {
            "processed_count": processed_count,
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors
        }

    async def process_realtime_lead(self, lead_data: RealtimeLeadData) -> Dict:
        """
        Receives real-time lead generation data from external aggregators/Insta (FR11, FR12, NFR7).
        Processes it, performs deduplication, applies offer precedence, and stores in CDP.
        """
        try:
            # 1. Deduplicate and get/create customer
            customer_data = lead_data.customer_data.dict(exclude_unset=True) if lead_data.customer_data else {}
            customer_data.update({
                "mobile_number": lead_data.mobile_number,
                "pan_number": lead_data.pan_number,
                "aadhaar_ref_number": lead_data.aadhaar_ref_number,
                "ucid_number": lead_data.ucid_number,
                "previous_loan_app_number": lead_data.previous_loan_app_number,
                "dnd_status": lead_data.dnd_status
            })
            customer = await self._deduplicate_and_get_or_create_customer(customer_data)

            # 2. Process offer data
            offer_data = lead_data.offer_data.dict(exclude_unset=True) if lead_data.offer_data else {}
            offer_data.update({
                "customer_id": customer.customer_id,
                "product_type": lead_data.product_type,
                "offer_type": lead_data.offer_type,
                "offer_start_date": lead_data.offer_start_date,
                "offer_end_date": lead_data.offer_end_date,
                "is_journey_started": lead_data.is_journey_started,
                "loan_application_id": lead_data.loan_application_id
            })

            # Apply offer precedence and determine final status
            processed_offer_data = await self._apply_offer_precedence_and_status(customer, offer_data)

            if processed_offer_data is None:
                await self.db.rollback()
                return {"status": "failed", "message": "Offer cannot be processed due to precedence rules.", "customer_id": str(customer.customer_id)}

            # Check if an existing offer needs to be updated (similar to Offermart feed, but for real-time)
            existing_offer_stmt = select(Offer).where(
                and_(
                    Offer.customer_id == customer.customer_id,
                    Offer.product_type == processed_offer_data["product_type"],
                    Offer.offer_status == OfferStatus.ACTIVE.value
                )
            )
            existing_offer = (await self.db.execute(existing_offer_stmt)).scalars().first()

            if existing_offer:
                logger.info(f"Updating existing offer {existing_offer.offer_id} for customer {customer.customer_id} from real-time lead.")
                update_values = {
                    k: v for k, v in processed_offer_data.items()
                    if k in Offer.__table__.columns.keys() and k not in ["offer_id", "customer_id", "created_at"]
                }
                update_values["updated_at"] = datetime.now(timezone.utc)
                stmt = update(Offer).where(Offer.offer_id == existing_offer.offer_id).values(**update_values)
                await self.db.execute(stmt)
                await self._update_offer_status(existing_offer.offer_id, OfferStatus(processed_offer_data["offer_status"]), "Offer updated from real-time lead")
                offer_id = existing_offer.offer_id
            else:
                new_offer_id = uuid4()
                offer_create_data = OfferCreate(
                    offer_id=new_offer_id,
                    customer_id=customer.customer_id,
                    offer_type=processed_offer_data.get("offer_type"),
                    offer_status=processed_offer_data.get("offer_status"),
                    product_type=processed_offer_data.get("product_type"),
                    offer_details=processed_offer_data.get("offer_details", {}),
                    offer_start_date=processed_offer_data.get("offer_start_date"),
                    offer_end_date=processed_offer_data.get("offer_end_date"),
                    is_journey_started=processed_offer_data.get("is_journey_started", False),
                    loan_application_id=processed_offer_data.get("loan_application_id")
                )
                new_offer = Offer(**offer_create_data.dict())
                self.db.add(new_offer)
                await self.db.flush()
                logger.info(f"Created new offer {new_offer.offer_id} for customer {customer.customer_id} from real-time lead.")
                await self._update_offer_status(new_offer.offer_id, OfferStatus(new_offer.offer_status), "New offer created from real-time lead")
                offer_id = new_offer.offer_id

            # Log event (FR33) - Lead Generation
            event_id = uuid4()
            campaign_event = CampaignEvent(
                event_id=event_id,
                customer_id=customer.customer_id,
                offer_id=offer_id,
                event_source="E-aggregator/Insta API",
                event_type="LEAD_GENERATED",
                event_details=lead_data.dict()
            )
            self.db.add(campaign_event)

            await self.db.commit()
            logger.info(f"Real-time lead processed successfully for customer {customer.customer_id}, offer {offer_id}")
            return {"status": "success", "message": "Lead processed and stored", "customer_id": str(customer.customer_id), "offer_id": str(offer_id)}

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing real-time lead: {e}", exc_info=True)
            return {"status": "failed", "message": f"Error processing lead: {str(e)}"}

    async def generate_moengage_file(self) -> io.StringIO:
        """
        Generates the Moengage format file in .csv format (FR54, FR55).
        Filters out DND customers (FR34).
        """
        # Select active offers for non-DND customers
        stmt = select(Customer, Offer).join(Offer, Customer.customer_id == Offer.customer_id).where(
            and_(
                Offer.offer_status == OfferStatus.ACTIVE.value,
                Customer.dnd_status == False
            )
        )
        result = await self.db.execute(stmt)
        records = result.all()

        output = io.StringIO()
        writer = csv.writer(output)

        # Moengage file format (example headers, actual headers need to be confirmed from BRD Q10)
        # Assuming common fields like customer_id, mobile_number, offer_id, product_type, offer_details (flattened)
        headers = [
            "customer_id", "mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number",
            "offer_id", "product_type", "offer_type", "offer_status",
            "offer_start_date", "offer_end_date", "is_journey_started", "loan_application_id",
            "customer_segments", "propensity_flag",
            # Add specific offer_details fields if known, otherwise flatten JSONB
            "offer_details_loan_amount", "offer_details_interest_rate" # Example
        ]
        writer.writerow(headers)

        for customer, offer in records:
            row = [
                str(customer.customer_id),
                customer.mobile_number,
                customer.pan_number,
                customer.aadhaar_ref_number,
                customer.ucid_number,
                str(offer.offer_id),
                offer.product_type,
                offer.offer_type,
                offer.offer_status,
                offer.offer_start_date.isoformat() if offer.offer_start_date else "",
                offer.offer_end_date.isoformat() if offer.offer_end_date else "",
                "TRUE" if offer.is_journey_started else "FALSE",
                offer.loan_application_id,
                ",".join(customer.customer_segments) if customer.customer_segments else "",
                customer.propensity_flag,
                # Flatten offer_details JSONB
                offer.offer_details.get("loan_amount", ""),
                offer.offer_details.get("interest_rate", "")
            ]
            writer.writerow(row)

        output.seek(0)
        logger.info(f"Generated Moengage file with {len(records)} records.")
        return output

    async def push_offers_to_offermart(self, offer_ids: List[UUID]) -> Dict:
        """
        Pushes real-time offers generated for Insta or E-aggregator via APIs into Analytics Offermart
        on an hourly/daily basis (FR7, NFR8).
        This is a placeholder for actual external API call logic.
        """
        logger.info(f"Simulating push of {len(offer_ids)} offers to Offermart.")
        # In a real scenario, this would involve:
        # 1. Fetching offer details from DB for the given offer_ids.
        # 2. Formatting data according to Offermart API requirements.
        # 3. Making an HTTP POST/PUT request to Offermart API.
        # 4. Handling success/failure responses.
        return {"status": "success", "message": f"Successfully simulated push of {len(offer_ids)} offers to Offermart."}

    async def push_daily_reverse_feed_to_offermart(self, report_date: date) -> Dict:
        """
        Pushes daily reverse feed to Offermart, including any Offer data updates from E-aggregators,
        on an hourly/daily basis (FR10, NFR6).
        This is a placeholder for actual external API call logic.
        """
        logger.info(f"Simulating push of daily reverse feed for {report_date} to Offermart.")
        # This would involve:
        # 1. Querying CDP for all relevant updates/new offers/status changes since last feed.
        # 2. Formatting data.
        # 3. Making an HTTP request to Offermart.
        return {"status": "success", "message": f"Successfully simulated push of daily reverse feed for {report_date} to Offermart."}

    async def push_data_to_edw(self, report_date: date) -> Dict:
        """
        Passes all data, including campaign data, from LTFS Offer CDP to EDW on a daily basis by day end (FR35, FR36, NFR11).
        This is a placeholder for actual external data transfer logic.
        """
        logger.info(f"Simulating push of daily data for {report_date} to EDW.")
        # This would involve:
        # 1. Querying CDP for all relevant customer, offer, campaign event data for the day.
        # 2. Formatting data (e.g., CSV, Parquet, JSON) according to EDW requirements (BRD Q5).
        # 3. Transferring data (e.g., SFTP, API, cloud storage).
        return {"status": "success", "message": f"Successfully simulated push of daily data for {report_date} to EDW."}

    async def update_expired_offers(self):
        """
        Marks offers as expired based on offer end dates for non-journey started customers (FR51).
        FR53 (LAN validity expiry) is assumed to be handled by LOS integration updating offer status.
        This would typically be run as a scheduled job.
        """
        current_date = date.today()
        updated_count = 0

        # FR51: Mark offers as expired based on offer end dates for non-journey started customers
        # We need to select offers first to log history correctly.
        stmt_offers_to_expire = select(Offer).where(
            and_(
                Offer.offer_end_date < current_date,
                Offer.is_journey_started == False,
                Offer.offer_status == OfferStatus.ACTIVE.value
            )
        )
        offers_to_expire = (await self.db.execute(stmt_offers_to_expire)).scalars().all()

        for offer in offers_to_expire:
            await self._update_offer_status(offer.offer_id, OfferStatus.EXPIRED, "Offer expired based on end date (FR51)")
            updated_count += 1

        await self.db.commit()
        logger.info(f"Expired offers update complete. {updated_count} offers marked as expired based on end date.")
        return {"status": "success", "message": f"Updated {updated_count} offers as expired."}

    async def check_and_replenish_expired_offers(self):
        """
        Checks for new replenishment offers for loan applications that have expired or been rejected (FR16, FR52).
        This implies a mechanism to trigger new offer generation or lookup.
        This is a placeholder for a complex business logic.
        """
        logger.info("Simulating check for replenishment offers for expired/rejected applications.")
        # This would involve:
        # 1. Identifying customers with recently expired/rejected offers (from offer_history or offer status).
        # 2. Querying an "offer generation" service or Offermart for new eligible offers for these customers.
        # 3. If new offers are found, processing them through the `process_offermart_daily_feed` or similar.
        return {"status": "success", "message": "Replenishment check simulated."}

# Dependency for FastAPI
from fastapi import Depends
async def get_integration_service(db: AsyncSession = Depends(get_db)) -> IntegrationService:
    return IntegrationService(db)