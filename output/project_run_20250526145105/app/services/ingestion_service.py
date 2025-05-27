import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import UploadFile, HTTPException, status

# Assuming models and schemas are defined in app.models and app.schemas
from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.schemas.ingestion import (
    LeadIngestionRequest,
    BulkUploadResult,
    LeadIngestionResponse,
    OfferDetailsSchema,
)
from app.core.config import settings # For DND list or external API settings

# For file processing (if needed for bulk upload)
import pandas as pd
import io

logger = logging.getLogger(__name__)

class IngestionService:
    def __init__(self, db: Session):
        self.db = db

    async def _check_dnd_status(self, mobile_number: str) -> bool:
        """
        FR34: Check if the customer is on the Do Not Disturb (DND) list.
        For MVP, this could be a simple check against a static list or a placeholder.
        In a real system, it would query a DND database or an external service.
        """
        # Placeholder: In a real scenario, query a DND list/service
        # For now, let's assume a hardcoded DND list for demonstration
        # settings.DND_MOBILE_NUMBERS should be configured in app/core/config.py
        dnd_numbers = getattr(settings, "DND_MOBILE_NUMBERS", [])
        if mobile_number and mobile_number in dnd_numbers:
            logger.warning(f"Customer with mobile {mobile_number} is on DND list. Skipping offer processing.")
            return True
        return False

    async def _find_or_create_customer(
        self,
        mobile_number: Optional[str],
        pan_number: Optional[str],
        aadhaar_ref_number: Optional[str],
        ucid_number: Optional[str] = None,
        previous_loan_app_number: Optional[str] = None,
        customer_attributes: Optional[Dict[str, Any]] = None
    ) -> Customer:
        """
        FR2, FR3, FR4, FR5: Deduplicate customers based on multiple identifiers.
        Prioritize existing customer if any identifier matches.
        If multiple identifiers match different customers, this indicates a data integrity issue.
        For simplicity, we'll assume if any identifier matches, it's the same customer.
        If multiple identifiers match *different* existing customers, this needs a merge strategy,
        which is complex and out of scope for a single service method.
        For MVP, we'll pick the first found customer or raise an error if conflicting customer IDs are found.
        """
        query_conditions = []
        if mobile_number:
            query_conditions.append(Customer.mobile_number == mobile_number)
        if pan_number:
            query_conditions.append(Customer.pan_number == pan_number)
        if aadhaar_ref_number:
            query_conditions.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
        if ucid_number:
            query_conditions.append(Customer.ucid_number == ucid_number)
        if previous_loan_app_number:
            query_conditions.append(Customer.previous_loan_app_number == previous_loan_app_number)

        existing_customer = None
        if query_conditions:
            # Use OR to find if any identifier matches an existing customer
            existing_customer = self.db.query(Customer).filter(or_(*query_conditions)).first()

        if existing_customer:
            logger.info(f"Found existing customer with ID: {existing_customer.customer_id}")
            # Update existing customer attributes if provided and different
            updated = False
            if customer_attributes:
                # Ensure customer_attributes is a mutable dictionary
                if not isinstance(existing_customer.customer_attributes, dict):
                    existing_customer.customer_attributes = {}
                for key, value in customer_attributes.items():
                    if key in existing_customer.customer_attributes and existing_customer.customer_attributes[key] != value:
                        existing_customer.customer_attributes[key] = value
                        updated = True
                    elif key not in existing_customer.customer_attributes:
                        existing_customer.customer_attributes[key] = value
                        updated = True
            if updated:
                existing_customer.updated_at = datetime.now(timezone.utc)
                self.db.add(existing_customer)
                self.db.commit()
                self.db.refresh(existing_customer)
            return existing_customer
        else:
            # Create new customer
            new_customer = Customer(
                customer_id=uuid4(),
                mobile_number=mobile_number,
                pan_number=pan_number,
                aadhaar_ref_number=aadhaar_ref_number,
                ucid_number=ucid_number,
                previous_loan_app_number=previous_loan_app_number,
                customer_attributes=customer_attributes if customer_attributes else {},
                dnd_status=False # Default to False, can be updated later
            )
            self.db.add(new_customer)
            self.db.commit()
            self.db.refresh(new_customer)
            logger.info(f"Created new customer with ID: {new_customer.customer_id}")
            return new_customer

    async def _apply_offer_precedence_rules(
        self,
        customer: Customer,
        new_offer_data: OfferDetailsSchema,
        existing_offers: List[Offer]
    ) -> Dict[str, Any]:
        """
        FR15, FR16, FR20, FR21, FR25-FR32: Apply complex offer precedence rules.
        This function determines the outcome of a new offer based on existing offers and business rules.
        Returns a dictionary indicating the action:
        {'action': 'create_new', 'status': 'Active'}
        {'action': 'update_existing', 'offer_to_update': Offer, 'status': 'Active'}
        {'action': 'expire_existing', 'offers_to_expire': List[Offer], 'status': 'Active'}
        {'action': 'reject_new', 'reason': 'string'}
        """
        new_offer_product_type = new_offer_data.product_type
        new_offer_is_enrich = new_offer_data.offer_type == 'Enrich'

        # Rule FR15, FR21: Prevent modification if journey started for existing offer
        for existing_offer in existing_offers:
            if existing_offer.is_journey_started:
                if new_offer_is_enrich:
                    logger.info(f"FR21: Enrich offer for customer {customer.customer_id} rejected as existing offer {existing_offer.offer_id} has journey started.")
                    return {'action': 'reject_new', 'reason': 'Existing offer journey started, cannot enrich.'}
                # FR15: If any existing offer has a started journey, prevent new offer if it conflicts
                # This rule is broad, needs specific interpretation. Assuming it means no new offers of same product type.
                # For now, if a journey is started, we generally don't allow new offers of the same type to override.
                if existing_offer.product_type == new_offer_product_type:
                    logger.info(f"FR15: New offer for customer {customer.customer_id} rejected as existing offer {existing_offer.offer_id} of same product type has journey started.")
                    return {'action': 'reject_new', 'reason': f'Existing offer of type {new_offer_product_type} has journey started.'}

        # Rule FR20: Enrich offer, journey not started -> previous offer to Duplicate
        if new_offer_is_enrich:
            for existing_offer in existing_offers:
                if not existing_offer.is_journey_started:
                    logger.info(f"FR20: Existing offer {existing_offer.offer_id} for customer {customer.customer_id} marked as Duplicate due to new Enrich offer.")
                    return {'action': 'expire_existing', 'offers_to_expire': [existing_offer], 'status': 'Active'} # New offer will be created as Active

        # Rule FR25: Pre-approved (no journey) + CLEAG/Insta -> CLEAG/Insta prevails, pre-approved expires.
        if new_offer_product_type in ['Insta', 'E-aggregator']:
            for existing_offer in existing_offers:
                if existing_offer.product_type in ['Preapproved', 'Prospect'] and not existing_offer.is_journey_started:
                    logger.info(f"FR25: Existing {existing_offer.product_type} offer {existing_offer.offer_id} for customer {customer.customer_id} expired due to new {new_offer_product_type} offer.")
                    return {'action': 'expire_existing', 'offers_to_expire': [existing_offer], 'status': 'Active'}

        # Rule FR26, FR27, FR28: Journey started -> direct to existing offer, attribution remains.
        # This implies the new offer is rejected or ignored, and the customer is directed to the existing one.
        # This logic might be handled at the API gateway/frontend level, but for ingestion, it means we don't create a new offer.
        for existing_offer in existing_offers:
            if existing_offer.is_journey_started:
                if (new_offer_product_type in ['Insta', 'E-aggregator'] and existing_offer.product_type in ['Preapproved', 'Prospect']) or \
                   (new_offer_product_type in ['Insta', 'E-aggregator'] and existing_offer.product_type in ['Insta', 'E-aggregator']) or \
                   (new_offer_product_type in ['Insta', 'E-aggregator'] and existing_offer.product_type in ['TWL', 'Top-up', 'EL']):
                    logger.info(f"FR26/27/28: New offer for customer {customer.customer_id} rejected as existing offer {existing_offer.offer_id} has journey started. Customer directed to existing.")
                    return {'action': 'reject_new', 'reason': 'Existing offer journey started, customer directed to existing offer.'}

        # Rule FR29, FR30, FR31, FR32: Specific product type precedence (new offer cannot be uploaded)
        # These rules imply a hierarchy or exclusivity.
        # Let's define product type groups for these rules.
        pre_approved_base_types = ['Preapproved', 'Prospect', 'E-aggregator']
        loan_product_types = ['TW Loyalty', 'Top-up', 'Employee Loan']

        for existing_offer in existing_offers:
            # FR29: If customer is in a pre-approved base and then receives an offer for TW Loyalty, Topup, Employee loan, Pre-approved E-aggregator, or Prospect, the new offer cannot be uploaded.
            if existing_offer.product_type in pre_approved_base_types and \
               new_offer_product_type in (loan_product_types + pre_approved_base_types):
                logger.info(f"FR29: New offer of type {new_offer_product_type} for customer {customer.customer_id} rejected due to existing {existing_offer.product_type} offer.")
                return {'action': 'reject_new', 'reason': 'New offer cannot be uploaded due to existing pre-approved base offer.'}

            # FR30: If customer receives an Employee loan offer first and then receives an offer for TW loyalty, Topup, Pre-approved E-aggregator, or Prospect, the new offer cannot be uploaded.
            if existing_offer.product_type == 'Employee Loan' and \
               new_offer_product_type in (['TW Loyalty', 'Top-up'] + pre_approved_base_types):
                logger.info(f"FR30: New offer of type {new_offer_product_type} for customer {customer.customer_id} rejected due to existing Employee Loan offer.")
                return {'action': 'reject_new', 'reason': 'New offer cannot be uploaded due to existing Employee Loan offer.'}

            # FR31: If customer receives a TW Loyalty offer first and then receives an offer for Topup, Employee loan, Pre-approved E-aggregator, or Prospect, the new offer cannot be uploaded.
            if existing_offer.product_type == 'TW Loyalty' and \
               new_offer_product_type in (['Top-up', 'Employee Loan'] + pre_approved_base_types):
                logger.info(f"FR31: New offer of type {new_offer_product_type} for customer {customer.customer_id} rejected due to existing TW Loyalty offer.")
                return {'action': 'reject_new', 'reason': 'New offer cannot be uploaded due to existing TW Loyalty offer.'}

            # FR32: If customer receives a Prospect offer first and then receives an offer for TW Loyalty, Topup, Employee loan, or Pre-approved E-aggregator, the new offer cannot be uploaded.
            # This rule is partially covered by FR29 if 'Prospect' is in 'pre_approved_base_types'.
            # Assuming 'Prospect' here is specifically about a new offer of these types being blocked.
            if existing_offer.product_type == 'Prospect' and \
               new_offer_product_type in (loan_product_types + ['Preapproved', 'E-aggregator']):
                logger.info(f"FR32: New offer of type {new_offer_product_type} for customer {customer.customer_id} rejected due to existing Prospect offer.")
                return {'action': 'reject_new', 'reason': 'New offer cannot be uploaded due to existing Prospect offer.'}

        # FR6: Deduplicate Top-up loan offers only against other Top-up offers, removing matches found.
        # This implies if a new offer is Top-up, and an existing Top-up offer exists, the existing one is removed/duplicated.
        if new_offer_product_type == 'Top-up':
            for existing_offer in existing_offers:
                if existing_offer.product_type == 'Top-up' and not existing_offer.is_journey_started:
                    logger.info(f"FR6: Existing Top-up offer {existing_offer.offer_id} for customer {customer.customer_id} marked as Duplicate due to new Top-up offer.")
                    return {'action': 'expire_existing', 'offers_to_expire': [existing_offer], 'status': 'Active'}

        # Default: If no specific rule applies, and there are no active offers of the same product type, create a new one.
        # If there's an existing active offer of the same product type, and it's not an enrich, reject.
        for existing_offer in existing_offers:
            if existing_offer.product_type == new_offer_product_type and existing_offer.offer_status == 'Active':
                logger.info(f"New offer of type {new_offer_product_type} for customer {customer.customer_id} rejected as an active offer of the same type already exists.")
                return {'action': 'reject_new', 'reason': 'Active offer of same product type already exists.'}

        # If no rejection or specific update rule, create a new offer
        return {'action': 'create_new', 'status': 'Active'}

    async def _record_offer_history(
        self,
        offer: Offer,
        old_status: Optional[str],
        new_status: str,
        reason: str,
        snapshot_details: Dict[str, Any]
    ):
        """FR23: Maintain offer history."""
        history_entry = OfferHistory(
            history_id=uuid4(),
            offer_id=offer.offer_id,
            customer_id=offer.customer_id,
            old_offer_status=old_status,
            new_offer_status=new_status,
            change_reason=reason,
            snapshot_offer_details=snapshot_details
        )
        self.db.add(history_entry)
        self.db.commit()
        self.db.refresh(history_entry)
        logger.info(f"Recorded offer history for offer {offer.offer_id}: {old_status} -> {new_status} ({reason})")

    async def _push_to_offermart(self, offer_data: Dict[str, Any]):
        """
        FR7, FR8, NFR8: Simulate pushing real-time offers/updates to Analytics Offermart.
        In a real system, this would be an HTTP POST request to the Offermart API
        or pushing to a message queue for async processing.
        """
        logger.info(f"Simulating push to Analytics Offermart for offer: {offer_data.get('offer_id')}")
        # Example:
        # import requests
        # try:
        #     response = requests.post(settings.OFFERMART_API_URL, json=offer_data)
        #     response.raise_for_status()
        #     logger.info(f"Successfully pushed offer {offer_data.get('offer_id')} to Offermart.")
        # except requests.exceptions.RequestException as e:
        #     logger.error(f"Failed to push offer {offer_data.get('offer_id')} to Offermart: {e}")
        pass

    async def process_realtime_lead_ingestion(self, lead_data: LeadIngestionRequest) -> LeadIngestionResponse:
        """
        Handles real-time lead generation data from external aggregators/Insta.
        FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR11, FR12, FR15, FR16, FR18, FR19, FR20, FR21, FR25-FR32, FR34, NFR3, NFR7, NFR8
        """
        logger.info(f"Processing real-time lead: Mobile: {lead_data.mobile_number}, PAN: {lead_data.pan_number}")

        if lead_data.mobile_number and await self._check_dnd_status(lead_data.mobile_number):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Customer is on DND list and cannot receive offers."
            )

        # 1. Find or Create Customer (Deduplication)
        customer = await self._find_or_create_customer(
            mobile_number=lead_data.mobile_number,
            pan_number=lead_data.pan_number,
            aadhaar_ref_number=lead_data.aadhaar_ref_number,
            ucid_number=lead_data.ucid_number,
            previous_loan_app_number=lead_data.previous_loan_app_number,
            customer_attributes=lead_data.customer_attributes
        )

        # 2. Get existing active offers for the customer
        existing_offers = self.db.query(Offer).filter(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == 'Active'
        ).all()

        # 3. Apply Offer Precedence Rules
        precedence_result = await self._apply_offer_precedence_rules(
            customer, lead_data.offer_details, existing_offers
        )

        action = precedence_result['action']
        offer_id = None
        message = "Lead processed successfully."

        try:
            if action == 'create_new':
                new_offer = Offer(
                    offer_id=uuid4(),
                    customer_id=customer.customer_id,
                    offer_type=lead_data.offer_details.offer_type,
                    offer_status=precedence_result['status'],
                    product_type=lead_data.offer_details.product_type,
                    offer_details=lead_data.offer_details.offer_details,
                    offer_start_date=lead_data.offer_details.offer_start_date,
                    offer_end_date=lead_data.offer_details.offer_end_date,
                    is_journey_started=False
                )
                self.db.add(new_offer)
                self.db.commit()
                self.db.refresh(new_offer)
                offer_id = new_offer.offer_id
                await self._record_offer_history(
                    new_offer, None, new_offer.offer_status, "New offer created", new_offer.offer_details
                )
                logger.info(f"New offer {new_offer.offer_id} created for customer {customer.customer_id}.")
                await self._push_to_offermart(new_offer.to_dict()) # Push new offer to Offermart

            elif action == 'expire_existing':
                offers_to_expire = precedence_result['offers_to_expire']
                for offer_to_expire in offers_to_expire:
                    old_status = offer_to_expire.offer_status
                    offer_to_expire.offer_status = 'Expired' if offer_to_expire.product_type != 'Top-up' else 'Duplicate' # FR6
                    offer_to_expire.updated_at = datetime.now(timezone.utc)
                    self.db.add(offer_to_expire)
                    self.db.commit()
                    self.db.refresh(offer_to_expire)
                    await self._record_offer_history(
                        offer_to_expire, old_status, offer_to_expire.offer_status,
                        f"Expired/Duplicated due to new offer precedence rule: {precedence_result.get('reason', 'N/A')}",
                        offer_to_expire.offer_details
                    )
                    logger.info(f"Offer {offer_to_expire.offer_id} for customer {customer.customer_id} marked as {offer_to_expire.offer_status}.")
                    await self._push_to_offermart(offer_to_expire.to_dict()) # Push update to Offermart

                # After expiring existing, create the new offer if the status is 'Active'
                if precedence_result['status'] == 'Active':
                    new_offer = Offer(
                        offer_id=uuid4(),
                        customer_id=customer.customer_id,
                        offer_type=lead_data.offer_details.offer_type,
                        offer_status='Active', # The new offer is active
                        product_type=lead_data.offer_details.product_type,
                        offer_details=lead_data.offer_details.offer_details,
                        offer_start_date=lead_data.offer_details.offer_start_date,
                        offer_end_date=lead_data.offer_details.offer_end_date,
                        is_journey_started=False
                    )
                    self.db.add(new_offer)
                    self.db.commit()
                    self.db.refresh(new_offer)
                    offer_id = new_offer.offer_id
                    await self._record_offer_history(
                        new_offer, None, new_offer.offer_status, "New offer created after expiring existing", new_offer.offer_details
                    )
                    logger.info(f"New offer {new_offer.offer_id} created for customer {customer.customer_id} after expiring previous.")
                    await self._push_to_offermart(new_offer.to_dict()) # Push new offer to Offermart

            elif action == 'reject_new':
                message = f"New offer rejected: {precedence_result['reason']}"
                logger.warning(f"New offer for customer {customer.customer_id} rejected: {precedence_result['reason']}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=message
                )
            else:
                message = "No action taken for the new offer."
                logger.info(f"No specific action taken for new offer for customer {customer.customer_id}.")

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error processing lead for customer {customer.customer_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process lead: {e}"
            )

        return LeadIngestionResponse(
            status="success",
            message=message,
            customer_id=customer.customer_id,
            offer_id=offer_id
        )

    async def process_bulk_customer_offers_upload(self, file: UploadFile) -> BulkUploadResult:
        """
        FR43, FR44, FR45, FR46: Allows administrators to upload a file (e.g., CSV)
        containing customer offer details for bulk processing and lead generation.
        """
        logger.info(f"Received bulk upload file: {file.filename}, content type: {file.content_type}")

        if not file.filename.endswith(('.csv', '.xlsx')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Only CSV and Excel files are supported."
            )

        contents = await file.read()
        df = None
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(io.BytesIO(contents))
        except Exception as e:
            logger.error(f"Error reading uploaded file: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to read file content: {e}"
            )

        # Basic column-level validation (FR1, NFR3)
        # These are the minimum required columns for a lead ingestion request
        required_columns = [
            "mobile_number", "pan_number", "aadhaar_ref_number", "product_type",
            "offer_type", "offer_start_date", "offer_end_date"
        ]
        # Check if at least one identifier column is present, and all offer details columns
        identifier_columns = ["mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number", "previous_loan_app_number"]
        if not any(col in df.columns for col in identifier_columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must contain at least one customer identifier column (mobile_number, pan_number, aadhaar_ref_number, ucid_number, or previous_loan_app_number)."
            )

        missing_offer_cols = [col for col in required_columns[3:] if col not in df.columns]
        if missing_offer_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required offer detail columns in the uploaded file: {', '.join(missing_offer_cols)}"
            )

        success_count = 0
        failed_records = []
        total_records = len(df)

        for index, row in df.iterrows():
            try:
                # Ensure identifiers are treated as strings, handle NaN/None
                mobile_number = str(int(row['mobile_number'])) if pd.notna(row.get('mobile_number')) else None
                pan_number = str(row['pan_number']) if pd.notna(row.get('pan_number')) else None
                aadhaar_ref_number = str(int(row['aadhaar_ref_number'])) if pd.notna(row.get('aadhaar_ref_number')) else None
                ucid_number = str(row['ucid_number']) if pd.notna(row.get('ucid_number')) else None
                previous_loan_app_number = str(row['previous_loan_app_number']) if pd.notna(row.get('previous_loan_app_number')) else None

                # At least one identifier must be present for a valid record
                if not any([mobile_number, pan_number, aadhaar_ref_number, ucid_number, previous_loan_app_number]):
                    raise ValueError("At least one of mobile_number, pan_number, aadhaar_ref_number, ucid_number, or previous_loan_app_number must be provided for the record.")

                # Convert dates from pandas format to date objects
                offer_start_date = pd.to_datetime(row['offer_start_date']).date() if pd.notna(row['offer_start_date']) else None
                offer_end_date = pd.to_datetime(row['offer_end_date']).date() if pd.notna(row['offer_end_date']) else None

                # Handle customer_attributes and offer_details which might be JSON strings in CSV/Excel
                customer_attributes = {}
                if 'customer_attributes' in row and pd.notna(row['customer_attributes']):
                    try:
                        customer_attributes = json.loads(row['customer_attributes'])
                    except json.JSONDecodeError:
                        logger.warning(f"Row {index}: Invalid JSON for customer_attributes. Skipping.")
                        customer_attributes = {}

                offer_details_json = {}
                if 'offer_details' in row and pd.notna(row['offer_details']):
                    try:
                        offer_details_json = json.loads(row['offer_details'])
                    except json.JSONDecodeError:
                        logger.warning(f"Row {index}: Invalid JSON for offer_details. Skipping.")
                        offer_details_json = {}

                lead_ingestion_request = LeadIngestionRequest(
                    mobile_number=mobile_number,
                    pan_number=pan_number,
                    aadhaar_ref_number=aadhaar_ref_number,
                    ucid_number=ucid_number,
                    previous_loan_app_number=previous_loan_app_number,
                    customer_attributes=customer_attributes,
                    offer_details=OfferDetailsSchema(
                        product_type=str(row['product_type']),
                        offer_type=str(row['offer_type']),
                        offer_details=offer_details_json,
                        offer_start_date=offer_start_date,
                        offer_end_date=offer_end_date
                    )
                )
                # Call the real-time ingestion logic for each row
                await self.process_realtime_lead_ingestion(lead_ingestion_request)
                success_count += 1
            except HTTPException as e:
                failed_records.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": e.detail
                })
                logger.warning(f"Row {index} failed: {e.detail}")
            except Exception as e:
                failed_records.append({
                    "row_index": index,
                    "data": row.to_dict(),
                    "error_desc": str(e)
                })
                logger.error(f"Unexpected error processing row {index}: {e}", exc_info=True)

        # FR45, FR46: Generate success/error files.
        # For this service, we return a summary. The actual file generation
        # would be handled by a separate export utility or a background task
        # that can be triggered by the job_id.
        # For now, we'll just return the summary.
        # The `job_id` can be used to retrieve the detailed success/error files later.
        job_id = uuid4()
        logger.info(f"Bulk upload job {job_id} completed. Success: {success_count}, Failed: {len(failed_records)}")

        return BulkUploadResult(
            status="success" if not failed_records else "partial_success",
            message=f"Processed {total_records} records. {success_count} successful, {len(failed_records)} failed.",
            job_id=job_id,
            total_records=total_records,
            successful_records=success_count,
            failed_records=failed_records # For immediate feedback, or store this in DB for later download
        )