import io
import csv
import json
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, insert, func, text

# Assuming these models and schemas exist in app/models and app/schemas
# These imports are crucial for the service to function.
# In a real project, these would be defined in their respective files.
from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.models.campaign_event import CampaignEvent # Assuming this model exists for campaign_events table

from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerProfileView
from app.schemas.offer import OfferCreate, OfferUpdate, OfferDetails
from app.schemas.lead import LeadCreate
# from app.core.config import settings # Uncomment if settings are needed, e.g., for DND list
from app.core.exceptions import OfferProcessingException, CustomerNotFoundException, FileProcessingException

# --- Constants and Configurations ---
DEDUPLICATION_IDENTIFIERS = [
    "mobile_number",
    "pan_number",
    "aadhaar_ref_number",
    "ucid_number",
    "previous_loan_app_number",
]

# Define offer statuses
OFFER_STATUS_ACTIVE = "Active"
OFFER_STATUS_INACTIVE = "Inactive"
OFFER_STATUS_EXPIRED = "Expired"
OFFER_STATUS_DUPLICATE = "Duplicate"
OFFER_STATUS_REJECTED = "Rejected" # For offers that don't pass precedence rules

# Define offer types (for campaigning)
OFFER_TYPE_FRESH = "Fresh"
OFFER_TYPE_ENRICH = "Enrich"
OFFER_TYPE_NEW_OLD = "New-old"
OFFER_TYPE_NEW_NEW = "New-new"

# Define product types and their precedence (higher index means higher precedence)
# This order is derived from FR29-FR32, where certain existing offers prevent new ones.
# The order here implies that if a customer has an offer of a type higher in this list,
# a new offer of a type lower in this list cannot be uploaded.
PRODUCT_PRECEDENCE_ORDER = [
    "Prospect",
    "Preapproved",
    "E-aggregator",
    "Insta", # Assuming Insta is similar to E-aggregator in precedence
    "Top-up",
    "TW Loyalty",
    "Employee Loan",
]

# Mapping for easier lookup
PRODUCT_PRECEDENCE_MAP = {
    product: i for i, product in enumerate(PRODUCT_PRECEDENCE_ORDER)
}

class OfferService:
    def __init__(self, db: AsyncSession):
        self.db = db
        # In a real app, DND list might come from a DB or external service
        # For MVP, this is a placeholder.
        # self.dnd_customers: List[str] = settings.DND_MOBILE_NUMBERS # Example if using settings
        self.dnd_customers: List[str] = [] # Placeholder for DND list (FR34)

    async def _get_customer_by_identifiers(self, identifiers: Dict[str, str]) -> Optional[Customer]:
        """
        Finds a customer by any of the deduplication identifiers.
        """
        query_conditions = []
        for key, value in identifiers.items():
            if key in DEDUPLICATION_IDENTIFIERS and value:
                query_conditions.append(getattr(Customer, key) == value)

        if not query_conditions:
            return None

        # Use OR to find if any identifier matches
        stmt = select(Customer).where(func.or_(*query_conditions))
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def _create_customer(self, customer_data: CustomerCreate) -> Customer:
        """
        Creates a new customer record.
        """
        new_customer = Customer(**customer_data.dict(exclude_unset=True), customer_id=uuid4())
        self.db.add(new_customer)
        await self.db.flush() # Flush to get the customer_id
        return new_customer

    async def _create_offer(self, offer_data: OfferCreate) -> Offer:
        """
        Creates a new offer record.
        """
        new_offer = Offer(**offer_data.dict(exclude_unset=True), offer_id=uuid4())
        self.db.add(new_offer)
        await self.db.flush()
        return new_offer

    async def _update_offer_status(
        self,
        offer: Offer,
        new_status: str,
        change_reason: str,
        snapshot_details: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Updates an offer's status and logs the change in offer_history.
        """
        old_status = offer.offer_status
        offer.offer_status = new_status
        offer.updated_at = datetime.now()
        self.db.add(offer) # Mark as dirty for update

        history_entry = OfferHistory(
            history_id=uuid4(),
            offer_id=offer.offer_id,
            customer_id=offer.customer_id,
            old_offer_status=old_status,
            new_offer_status=new_status,
            change_reason=change_reason,
            snapshot_offer_details=snapshot_details if snapshot_details is not None else offer.offer_details,
            change_timestamp=datetime.now()
        )
        self.db.add(history_entry)
        await self.db.flush() # Flush to ensure history is recorded

    async def _apply_deduplication_and_precedence(
        self,
        new_offer_data: OfferCreate,
        customer_identifiers: Dict[str, str],
        is_realtime_api: bool = False # Flag to differentiate between API and batch/upload
    ) -> Tuple[Customer, Offer, str]: # Returns customer, offer, and status message
        """
        Applies deduplication, DND check, and offer precedence rules.
        Returns the processed customer, the final offer (new or existing), and a status message.
        """
        # FR34: Check DND status
        if customer_identifiers.get("mobile_number") in self.dnd_customers:
            raise OfferProcessingException("Customer is on DND list. Offer cannot be processed.")

        customer = await self._get_customer_by_identifiers(customer_identifiers)
        new_offer_product_type = new_offer_data.product_type
        new_offer_type = new_offer_data.offer_type

        if not customer:
            # No existing customer, create new customer and offer
            customer_create_data = CustomerCreate(
                mobile_number=customer_identifiers.get("mobile_number"),
                pan_number=customer_identifiers.get("pan_number"),
                aadhaar_ref_number=customer_identifiers.get("aadhaar_ref_number"),
                ucid_number=customer_identifiers.get("ucid_number"),
                previous_loan_app_number=customer_identifiers.get("previous_loan_app_number"),
                customer_attributes=new_offer_data.customer_attributes,
                customer_segments=new_offer_data.customer_segments,
                propensity_flag=new_offer_data.propensity_flag,
                dnd_status=False # Default to False, can be updated later
            )
            customer = await self._create_customer(customer_create_data)
            new_offer_data.customer_id = customer.customer_id
            offer = await self._create_offer(new_offer_data)
            await self._update_offer_status(offer, OFFER_STATUS_ACTIVE, "New customer and offer created.")
            return customer, offer, "New customer and offer created."

        # Customer exists, proceed with deduplication and precedence
        # Update customer attributes if new data is richer (FR8 implies updating old offers/data)
        # Only update if new data is present and different
        if new_offer_data.customer_attributes:
            customer.customer_attributes = new_offer_data.customer_attributes
        if new_offer_data.customer_segments:
            customer.customer_segments = new_offer_data.customer_segments
        if new_offer_data.propensity_flag:
            customer.propensity_flag = new_offer_data.propensity_flag
        self.db.add(customer) # Mark customer as dirty for update

        # Get all active offers for this customer
        stmt_active_offers = select(Offer).where(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == OFFER_STATUS_ACTIVE
        )
        active_offers_result = await self.db.execute(stmt_active_offers)
        existing_active_offers: List[Offer] = active_offers_result.scalars().all()

        # FR15: Prevent modification if journey started for any active offer
        for existing_offer in existing_active_offers:
            if existing_offer.is_journey_started:
                # FR16: Check for replenishment offers for expired/rejected journeys
                # This logic needs more context on how replenishment offers are identified.
                # For now, if journey started, new offer is generally rejected unless it's a specific replenishment.
                # Assuming replenishment offers would have a specific flag or context.
                # If not a replenishment, and journey started, new offer is rejected.
                # The BRD states "allow checking for new replenishment offers for loan applications that have expired or been rejected."
                # This implies that if the *existing* offer's journey is expired/rejected, a new offer *can* come.
                # But if the existing offer is *active* and its journey started, new offers are blocked.
                if existing_offer.offer_status == OFFER_STATUS_ACTIVE:
                    return customer, existing_offer, f"Customer has an active offer with started journey ({existing_offer.loan_application_id}). New offer rejected (FR15)."

        # FR20, FR21: Enrich offer logic
        if new_offer_type == OFFER_TYPE_ENRICH:
            for existing_offer in existing_active_offers:
                if existing_offer.product_type == new_offer_product_type: # Enrich usually for same product
                    if not existing_offer.is_journey_started:
                        # If an Enrich offer's journey has not started, it flows to CDP, previous offer moved to Duplicate.
                        await self._update_offer_status(existing_offer, OFFER_STATUS_DUPLICATE, "Replaced by new Enrich offer (journey not started).")
                        # Continue processing the new enrich offer as if it's a fresh one
                        break # Break from loop, as existing offer is handled, proceed to create new.
                    else:
                        # If an Enrich offer's journey has started, it shall not flow into CDP.
                        return customer, existing_offer, f"Existing Enrich offer journey started. New Enrich offer rejected (FR21)."

        # FR25-FR32: Offer Precedence and Attribution Logic
        # This is the most complex part. Iterate through existing offers and apply rules.
        # The goal is to determine if the new offer should replace an existing one,
        # be rejected, or if the existing one should prevail.

        # Sort existing offers by precedence (highest first)
        existing_active_offers.sort(key=lambda o: PRODUCT_PRECEDENCE_MAP.get(o.product_type, -1), reverse=True)

        for existing_offer in existing_active_offers:
            existing_product_priority = PRODUCT_PRECEDENCE_MAP.get(existing_offer.product_type, -1)
            new_product_priority = PRODUCT_PRECEDENCE_MAP.get(new_offer_product_type, -1)

            # FR29-FR32: If existing offer is of a higher or equal precedence type, new offer cannot be uploaded.
            # This is a strict rule for specific product types.
            if existing_product_priority >= new_product_priority:
                # Special handling for Top-up deduplication (FR6)
                # "deduplicate Top-up loan offers only against other Top-up offers, removing matches found."
                # This implies if a new Top-up comes, it only affects existing Top-ups.
                # If a non-Top-up comes, it doesn't affect existing Top-ups.
                if new_offer_product_type == "Top-up" and existing_offer.product_type == "Top-up":
                    # If new is Top-up and existing is Top-up, then the new one replaces the old one (deduplication).
                    await self._update_offer_status(existing_offer, OFFER_STATUS_DUPLICATE, "Replaced by new Top-up offer (FR6).")
                    # Continue to create the new offer
                    break # Break from loop, as existing offer is handled, proceed to create new.
                elif new_offer_product_type == "Top-up" and existing_offer.product_type != "Top-up":
                    # If new is Top-up but existing is NOT Top-up, FR6 implies no deduplication.
                    # In this case, the general precedence rules (FR29-32) would apply.
                    # If existing is higher priority, new Top-up is rejected.
                    if existing_product_priority > new_product_priority:
                        await self._update_offer_status(new_offer_data, OFFER_STATUS_REJECTED, f"New offer of type '{new_offer_product_type}' rejected due to existing higher precedence offer of type '{existing_offer.product_type}'. (FR29-FR32)")
                        return customer, existing_offer, f"New offer of type '{new_offer_product_type}' rejected due to existing higher precedence offer of type '{existing_offer.product_type}'. Existing offer prevails."
                    else: # existing_product_priority == new_product_priority (shouldn't happen if product types are different)
                        # This case implies same product type, handled below.
                        pass
                elif existing_product_priority > new_product_priority:
                    # General case: Existing offer is of higher precedence, new offer cannot be uploaded.
                    await self._update_offer_status(new_offer_data, OFFER_STATUS_REJECTED, f"New offer of type '{new_offer_product_type}' rejected due to existing higher precedence offer of type '{existing_offer.product_type}'. (FR29-FR32)")
                    return customer, existing_offer, f"New offer of type '{new_offer_product_type}' rejected due to existing higher precedence offer of type '{existing_offer.product_type}'. Existing offer prevails."
                elif existing_product_priority == new_product_priority:
                    # If same product type, it's a duplicate unless it's an enrich offer (handled earlier).
                    await self._update_offer_status(new_offer_data, OFFER_STATUS_DUPLICATE, f"Duplicate offer of same product type '{new_offer_product_type}'.")
                    return customer, existing_offer, f"Duplicate offer of same product type '{new_offer_product_type}'. Existing offer prevails."

            # FR25-FR28: Channel/Journey Precedence
            # These rules are about *which journey prevails* if a customer comes via different channels.
            # They imply that if a journey has started, it takes precedence.
            # If no journey started, CLEAG/Insta might prevail over pre-approved.

            # FR25: Pre-approved (prospect/E-aggregator) with no journey started, same customer via CLEAG/Insta.
            # CLEAG/Insta journey prevails, uploaded pre-approved offer expires.
            if (existing_offer.product_type in ["Preapproved", "Prospect", "E-aggregator"] and not existing_offer.is_journey_started) and \
               (new_offer_product_type in ["Insta", "E-aggregator"] and is_realtime_api): # Assuming CLEAG/Insta are real-time APIs
                await self._update_offer_status(existing_offer, OFFER_STATUS_EXPIRED, "Replaced by new CLEAG/Insta offer (FR25).")
                # Continue to create the new offer
                break # Break from loop, as existing offer is handled, proceed to create new.

            # FR26: Pre-approved (prospect/E-aggregator) with journey started, same customer via CLEAG/Insta.
            # Customer directed to pre-approved offer, attribution remains existing.
            if (existing_offer.product_type in ["Preapproved", "Prospect", "E-aggregator"] and existing_offer.is_journey_started) and \
               (new_offer_product_type in ["Insta", "E-aggregator"] and is_realtime_api):
                return customer, existing_offer, f"Customer has existing pre-approved offer with started journey. New CLEAG/Insta offer rejected (FR26). Existing offer prevails."

            # FR27: Customer already present via CLEAG/Insta, same customer via CLEAG/Insta again (another channel).
            # Customer directed to previous offer, attribution remains existing.
            if (existing_offer.product_type in ["Insta", "E-aggregator"] and is_realtime_api) and \
               (new_offer_product_type in ["Insta", "E-aggregator"] and is_realtime_api):
                return customer, existing_offer, f"Customer has existing CLEAG/Insta offer. New CLEAG/Insta offer rejected (FR27). Existing offer prevails."

            # FR28: Customer has existing TWL, Top-up, or EL offer, then comes via CLEAG/Insta.
            # Customer shown existing offer, directed to pre-approved TW/EL/Topup journey.
            if (existing_offer.product_type in ["TW Loyalty", "Top-up", "Employee Loan"] and is_realtime_api) and \
               (new_offer_product_type in ["Insta", "E-aggregator"] and is_realtime_api):
                return customer, existing_offer, f"Customer has existing TWL/Top-up/EL offer. New CLEAG/Insta offer rejected (FR28). Existing offer prevails."

        # If no existing offer blocked the new one, or was replaced (e.g., by Enrich/FR25), create the new offer.
        new_offer_data.customer_id = customer.customer_id
        offer = await self._create_offer(new_offer_data)
        await self._update_offer_status(offer, OFFER_STATUS_ACTIVE, "New offer created after precedence checks.")
        return customer, offer, "Offer processed successfully."

    async def process_realtime_lead(self, lead_data: LeadCreate) -> Tuple[Customer, Offer, str]:
        """
        Processes a real-time lead generation request.
        (FR11, FR12, API: /api/v1/leads)
        """
        customer_identifiers = {
            "mobile_number": lead_data.mobile_number,
            "pan_number": lead_data.pan_number,
            "aadhaar_ref_number": lead_data.aadhaar_ref_number,
            "ucid_number": lead_data.ucid_number,
            "previous_loan_app_number": lead_data.previous_loan_app_number,
        }

        # Basic validation (FR1, NFR3) - Pydantic models handle this at API layer,
        # but additional business validation can be here.
        if not any(customer_identifiers.values()):
            raise OfferProcessingException("At least one customer identifier (mobile, PAN, Aadhaar, UCID, previous loan app) is required.")

        # Construct OfferCreate from LeadCreate
        offer_create_data = OfferCreate(
            customer_id=None, # Will be set by _apply_deduplication_and_precedence
            offer_type=OFFER_TYPE_FRESH, # Assuming real-time leads are 'Fresh' offers
            offer_status=OFFER_STATUS_ACTIVE, # Initial status
            product_type=lead_data.loan_product,
            offer_details=lead_data.offer_details,
            offer_start_date=date.today(),
            offer_end_date=lead_data.offer_end_date or (date.today() + timedelta(days=30)), # Default 30 days validity
            is_journey_started=False,
            loan_application_id=None,
            customer_attributes=lead_data.customer_attributes,
            customer_segments=lead_data.customer_segments,
            propensity_flag=lead_data.propensity_flag
        )

        customer, offer, status_message = await self._apply_deduplication_and_precedence(
            offer_create_data, customer_identifiers, is_realtime_api=True
        )
        await self.db.commit() # Commit transaction after successful processing
        return customer, offer, status_message

    async def process_uploaded_offers(self, file_content: bytes, file_format: str) -> Tuple[str, str]:
        """
        Processes an uploaded file containing customer offer details.
        (FR43, FR44, FR45, FR46, API: /api/v1/admin/customer_offers/upload)
        Returns paths/content for success and error files.
        """
        success_records = []
        error_records = []
        df = None

        try:
            if file_format == "csv":
                df = pd.read_csv(io.BytesIO(file_content))
            elif file_format == "excel":
                df = pd.read_excel(io.BytesIO(file_content))
            else:
                raise FileProcessingException("Unsupported file format. Only CSV and Excel are supported.")
        except Exception as e:
            raise FileProcessingException(f"Error reading uploaded file: {e}")

        # Expected columns (adjust based on actual template)
        expected_columns = [
            "mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number", "previous_loan_app_number",
            "loan_product", "offer_start_date", "offer_end_date", "offer_details",
            "customer_attributes", "customer_segments", "propensity_flag", "offer_type"
        ]
        # Check if all expected columns are present
        if not all(col in df.columns for col in expected_columns):
            missing_cols = [col for col in expected_columns if col not in df.columns]
            raise FileProcessingException(f"Missing required columns in the uploaded file: {', '.join(missing_cols)}")

        for index, row in df.iterrows():
            try:
                customer_identifiers = {
                    "mobile_number": str(row.get("mobile_number")) if pd.notna(row.get("mobile_number")) else None,
                    "pan_number": str(row.get("pan_number")) if pd.notna(row.get("pan_number")) else None,
                    "aadhaar_ref_number": str(row.get("aadhaar_ref_number")) if pd.notna(row.get("aadhaar_ref_number")) else None,
                    "ucid_number": str(row.get("ucid_number")) if pd.notna(row.get("ucid_number")) else None,
                    "previous_loan_app_number": str(row.get("previous_loan_app_number")) if pd.notna(row.get("previous_loan_app_number")) else None,
                }

                # Basic validation for identifiers
                if not any(customer_identifiers.values()):
                    raise ValueError("At least one customer identifier is required for each row.")

                # Parse dates
                offer_start_date = pd.to_datetime(row.get("offer_start_date")).date() if pd.notna(row.get("offer_start_date")) else date.today()
                offer_end_date = pd.to_datetime(row.get("offer_end_date")).date() if pd.notna(row.get("offer_end_date")) else (date.today() + timedelta(days=30))

                # Parse JSON fields if they are strings
                offer_details = {}
                if pd.notna(row.get("offer_details")):
                    try:
                        offer_details = json.loads(str(row.get("offer_details"))) # Ensure it's a string before loading
                    except json.JSONDecodeError:
                        pass # Keep as empty dict if not valid JSON string

                customer_attributes = {}
                if pd.notna(row.get("customer_attributes")):
                    try:
                        customer_attributes = json.loads(str(row.get("customer_attributes")))
                    except json.JSONDecodeError:
                        pass

                customer_segments = []
                if pd.notna(row.get("customer_segments")):
                    segments_str = str(row.get("customer_segments"))
                    customer_segments = [s.strip() for s in segments_str.split(',') if s.strip()]

                offer_create_data = OfferCreate(
                    customer_id=None,
                    offer_type=row.get("offer_type", OFFER_TYPE_FRESH), # Default to Fresh if not provided
                    offer_status=OFFER_STATUS_ACTIVE,
                    product_type=row.get("loan_product"),
                    offer_details=offer_details,
                    offer_start_date=offer_start_date,
                    offer_end_date=offer_end_date,
                    is_journey_started=False,
                    loan_application_id=None,
                    customer_attributes=customer_attributes,
                    customer_segments=customer_segments,
                    propensity_flag=row.get("propensity_flag")
                )

                customer, offer, status_message = await self._apply_deduplication_and_precedence(
                    offer_create_data, customer_identifiers, is_realtime_api=False
                )
                success_records.append({**row.to_dict(), "status": status_message, "customer_id": str(customer.customer_id), "offer_id": str(offer.offer_id)})
                await self.db.commit() # Commit each row's transaction
            except OfferProcessingException as e:
                error_records.append({**row.to_dict(), "Error Desc": str(e)})
                await self.db.rollback() # Rollback current transaction on error
            except Exception as e:
                error_records.append({**row.to_dict(), "Error Desc": f"Unexpected error: {e}"})
                await self.db.rollback()

        success_df = pd.DataFrame(success_records)
        error_df = pd.DataFrame(error_records)

        # Generate CSV content for success and error files
        success_output = io.StringIO()
        success_df.to_csv(success_output, index=False)
        success_file_content = success_output.getvalue()

        error_output = io.StringIO()
        error_df.to_csv(error_output, index=False)
        error_file_content = error_output.getvalue()

        return success_file_content, error_file_content

    async def get_customer_profile(self, customer_id: UUID) -> CustomerProfileView:
        """
        Retrieves a single profile view of a customer.
        (FR50, API: /api/v1/customers/{customer_id})
        """
        stmt_customer = select(Customer).where(Customer.customer_id == customer_id)
        customer_result = await self.db.execute(stmt_customer)
        customer = customer_result.scalars().first()

        if not customer:
            raise CustomerNotFoundException(f"Customer with ID {customer_id} not found.")

        stmt_offers = select(Offer).where(Offer.customer_id == customer_id).order_by(Offer.created_at.desc())
        offers_result = await self.db.execute(stmt_offers)
        offers = offers_result.scalars().all()

        current_offer: Optional[OfferDetails] = None
        active_offers = [o for o in offers if o.offer_status == OFFER_STATUS_ACTIVE]
        if active_offers:
            # Prioritize the "strongest" active offer as current
            active_offers.sort(key=lambda o: PRODUCT_PRECEDENCE_MAP.get(o.product_type, -1), reverse=True)
            current_offer = OfferDetails.from_orm(active_offers[0])

        offer_history_summary = []
        stmt_history = select(OfferHistory).where(OfferHistory.customer_id == customer_id).order_by(OfferHistory.change_timestamp.desc()).limit(10) # Limit for summary
        history_result = await self.db.execute(stmt_history)
        for hist in history_result.scalars().all():
            offer_history_summary.append({
                "offer_id": str(hist.offer_id),
                "change_timestamp": hist.change_timestamp.isoformat(),
                "old_status": hist.old_offer_status,
                "new_status": hist.new_offer_status,
                "reason": hist.change_reason
            })

        # Determine journey status (simplified for now)
        journey_status = "No active journey"
        if current_offer and current_offer.is_journey_started:
            journey_status = f"Journey started for {current_offer.product_type} (LAN: {current_offer.loan_application_id})"
        elif current_offer:
            journey_status = f"Active offer for {current_offer.product_type}, journey not started"

        return CustomerProfileView(
            customer_id=customer.customer_id,
            mobile_number=customer.mobile_number,
            pan_number=customer.pan_number,
            aadhaar_ref_number=customer.aadhaar_ref_number,
            ucid_number=customer.ucid_number,
            previous_loan_app_number=customer.previous_loan_app_number,
            customer_attributes=customer.customer_attributes,
            customer_segments=customer.customer_segments,
            propensity_flag=customer.propensity_flag,
            dnd_status=customer.dnd_status,
            current_offer=current_offer,
            offer_history_summary=offer_history_summary,
            journey_status=journey_status
        )

    async def generate_moengage_file(self) -> str:
        """
        Generates the Moengage-formatted campaign file in CSV format.
        (FR39, FR54, FR55, API: /api/v1/admin/campaigns/moengage_file)
        """
        # Select active offers that are not DND and have valid end dates
        stmt = select(Customer, Offer).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == OFFER_STATUS_ACTIVE,
            Customer.dnd_status == False,
            Offer.offer_end_date >= date.today()
        )
        results = await self.db.execute(stmt)
        records = results.all()

        # Moengage file format (example, needs to be confirmed by FR54/Q10)
        # Assuming common fields like customer_id, mobile_number, offer_details, product_type, etc.
        moengage_data = []
        for customer, offer in records:
            row = {
                "customer_id": str(customer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan_number": customer.pan_number,
                "product_type": offer.product_type,
                "offer_id": str(offer.offer_id),
                "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                "offer_status": offer.offer_status,
                "offer_type": offer.offer_type,
                "propensity_flag": customer.propensity_flag,
                "customer_segments": ",".join(customer.customer_segments) if customer.customer_segments else "",
                # Flatten offer_details JSON into columns if specific keys are needed by Moengage
                # For now, just include the raw JSON string or specific keys
                "offer_details_json": json.dumps(offer.offer_details) if offer.offer_details else "{}"
            }
            # Add specific offer details as separate columns if required by Moengage
            if offer.offer_details:
                for key, value in offer.offer_details.items():
                    row[f"offer_detail_{key}"] = value # Example: offer_detail_loan_amount

            moengage_data.append(row)

        if not moengage_data:
            return "" # Return empty string if no data

        # Use pandas to easily convert to CSV
        df = pd.DataFrame(moengage_data)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    async def mark_offers_expired(self) -> int:
        """
        Scheduled task to mark offers as expired based on business logic.
        (FR51, FR53)
        """
        # FR51: Mark offers as expired based on offer end dates for non-journey started customers.
        stmt_expire_by_date = select(Offer).where(
            Offer.offer_status == OFFER_STATUS_ACTIVE,
            Offer.is_journey_started == False,
            Offer.offer_end_date < date.today()
        )
        offers_to_expire_by_date_result = await self.db.execute(stmt_expire_by_date)
        offers_to_expire_by_date = offers_to_expire_by_date_result.scalars().all()

        expired_count = 0
        for offer in offers_to_expire_by_date:
            await self._update_offer_status(offer, OFFER_STATUS_EXPIRED, "Offer expired based on end date (FR51).")
            expired_count += 1

        # FR53: Mark offers as expired within the offers data if the LAN validity post loan application journey start date is over.
        # This requires knowing the "LAN validity period" (Q9). Assuming a `loan_application_validity_days` setting.
        # For simplicity, let's assume `offer_end_date` also covers this for offers with started journeys.
        # A more robust solution would query LOS for LAN status or have a dedicated field.
        stmt_expire_by_lan_validity = select(Offer).where(
            Offer.offer_status == OFFER_STATUS_ACTIVE,
            Offer.is_journey_started == True,
            Offer.loan_application_id.isnot(None),
            Offer.offer_end_date < date.today() # Using offer_end_date as a proxy for LAN validity expiry
        )
        offers_to_expire_by_lan_result = await self.db.execute(stmt_expire_by_lan_validity)
        offers_to_expire_by_lan = offers_to_expire_by_lan_result.scalars().all()

        for offer in offers_to_expire_by_lan:
            await self._update_offer_status(offer, OFFER_STATUS_EXPIRED, "Offer expired based on LAN validity (FR53).")
            expired_count += 1

        await self.db.commit()
        return expired_count

    async def update_offer_journey_status(self, offer_id: UUID, is_journey_started: bool, loan_application_id: Optional[str] = None) -> Offer:
        """
        Updates the journey status of an offer. This would be called by LOS integration.
        """
        stmt = select(Offer).where(Offer.offer_id == offer_id)
        result = await self.db.execute(stmt)
        offer = result.scalars().first()

        if not offer:
            raise OfferProcessingException(f"Offer with ID {offer_id} not found.")

        if offer.is_journey_started != is_journey_started:
            old_status_text = "Journey not started" if not offer.is_journey_started else "Journey started"
            new_status_text = "Journey started" if is_journey_started else "Journey not started"
            change_reason = f"Journey status changed from '{old_status_text}' to '{new_status_text}'."

            offer.is_journey_started = is_journey_started
            if is_journey_started and loan_application_id:
                offer.loan_application_id = loan_application_id
            elif not is_journey_started:
                offer.loan_application_id = None # Clear LAN if journey ends/rejected

            offer.updated_at = datetime.now()
            self.db.add(offer)

            history_entry = OfferHistory(
                history_id=uuid4(),
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=offer.offer_status, # Keep offer status same, but log journey change
                new_offer_status=offer.offer_status,
                change_reason=change_reason,
                snapshot_offer_details=offer.offer_details,
                change_timestamp=datetime.now()
            )
            self.db.add(history_entry)
            await self.db.commit()
        return offer

    # Placeholder for other file generation methods (FR40, FR41, FR42)
    async def generate_duplicate_data_file(self) -> str:
        """
        Generates a CSV file containing duplicate customer data. (FR40)
        This would require a more sophisticated deduplication report logic,
        e.g., identifying customers with multiple active offers that should have been deduplicated,
        or customers identified as duplicates during ingestion.
        For now, a placeholder.
        """
        # This would typically involve querying offer_history for 'Duplicate' status changes
        # or identifying customers with multiple active offers that violate rules.
        # For MVP, let's assume it lists customers who had offers marked as DUPLICATE.
        stmt = select(Customer, Offer, OfferHistory).join(Offer, Customer.customer_id == Offer.customer_id).join(
            OfferHistory, Offer.offer_id == OfferHistory.offer_id
        ).where(
            OfferHistory.new_offer_status == OFFER_STATUS_DUPLICATE
        ).distinct(Customer.customer_id) # Get unique customers who had duplicates

        results = await self.db.execute(stmt)
        duplicate_records = []
        for customer, offer, history in results.all():
            duplicate_records.append({
                "customer_id": str(customer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan_number": customer.pan_number,
                "duplicate_offer_id": str(offer.offer_id),
                "duplicate_offer_product_type": offer.product_type,
                "reason": history.change_reason,
                "timestamp": history.change_timestamp.isoformat()
            })

        if not duplicate_records:
            return ""

        df = pd.DataFrame(duplicate_records)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    async def generate_unique_data_file(self) -> str:
        """
        Generates a CSV file containing unique customer data. (FR41)
        This would typically be a list of all active, unique customers and their primary offer.
        """
        stmt = select(Customer, Offer).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == OFFER_STATUS_ACTIVE
        ).distinct(Customer.customer_id) # Ensure unique customers

        results = await self.db.execute(stmt)
        unique_records = []
        for customer, offer in results.all():
            unique_records.append({
                "customer_id": str(customer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan_number": customer.pan_number,
                "aadhaar_ref_number": customer.aadhaar_ref_number,
                "ucid_number": customer.ucid_number,
                "current_offer_id": str(offer.offer_id),
                "current_product_type": offer.product_type,
                "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                "customer_segments": ",".join(customer.customer_segments) if customer.customer_segments else "",
                "propensity_flag": customer.propensity_flag
            })

        if not unique_records:
            return ""

        df = pd.DataFrame(unique_records)
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()

    async def get_daily_tally_report(self, report_date: date) -> Dict[str, Any]:
        """
        Provides daily summary reports for data tally. (FR49, API: /api/v1/reports/daily_tally)
        """
        # Total customers
        total_customers_stmt = select(func.count(Customer.customer_id))
        total_customers_result = await self.db.execute(total_customers_stmt)
        total_customers = total_customers_result.scalar_one()

        # Active offers
        active_offers_stmt = select(func.count(Offer.offer_id)).where(Offer.offer_status == OFFER_STATUS_ACTIVE)
        active_offers_result = await self.db.execute(active_offers_stmt)
        active_offers = active_offers_result.scalar_one()

        # New leads today (offers created today)
        new_leads_today_stmt = select(func.count(Offer.offer_id)).where(
            func.date(Offer.created_at) == report_date
        )
        new_leads_today_result = await self.db.execute(new_leads_today_stmt)
        new_leads_today = new_leads_today_result.scalar_one()

        # Conversions today (requires campaign_events or LOS integration)
        # For now, a placeholder. Assuming 'CONVERSION' event type.
        conversions_today_stmt = select(func.count(CampaignEvent.event_id)).where(
            func.date(CampaignEvent.event_timestamp) == report_date,
            CampaignEvent.event_type == "CONVERSION"
        )
        conversions_today_result = await self.db.execute(conversions_today_stmt)
        conversions_today = conversions_today_result.scalar_one()

        return {
            "report_date": report_date.isoformat(),
            "total_customers": total_customers,
            "active_offers": active_offers,
            "new_leads_today": new_leads_today,
            "conversions_today": conversions_today
        }