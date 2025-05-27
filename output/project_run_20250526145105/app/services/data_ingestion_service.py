import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import io
import pandas as pd

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.schemas.customer import CustomerCreate, CustomerInDB
from app.schemas.offer import OfferCreate, OfferInDB
from app.schemas.data_ingestion import LeadCreate # Assuming LeadCreate is defined here or similar

# Placeholder for a more sophisticated deduplication service
# In a real scenario, this might be a separate class/module
class DeduplicationService:
    def find_existing_customer(self, db: Session, data: Dict) -> Optional[Customer]:
        """
        FR3: Deduplicate customers based on Mobile number, Pan number, Aadhaar reference number, UCID number, or previous loan application number.
        FR5: Deduplication against the live book (from Customer 360) based on mobile number, pan number, Aadhaar reference number, or UCID number.
        For MVP, we'll query our own DB. Integration with Customer 360 would be an external API call.
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
            return None # No identifiable information to deduplicate

        return db.query(Customer).filter(or_(*query_conditions)).first()

class DataIngestionService:
    def __init__(self):
        self.deduplication_service = DeduplicationService()

    def _validate_data(self, data: Dict, required_fields: List[str]) -> Optional[str]:
        """
        FR1: The system shall perform basic column-level validation during data transfer from Offermart to CDP.
        NFR3: The system shall perform basic column level validation when moving data from Offermart to CDP.
        Basic validation: check for presence of required fields.
        More complex validation (data types, formats, business rules) would be added here.
        """
        for field in required_fields:
            if not data.get(field):
                return f"Missing required field: {field}"
        return None

    def _log_offer_history(self, db: Session, offer: Offer, old_status: str, new_status: str, reason: str):
        """
        Logs changes to an offer's status.
        """
        history_entry = OfferHistory(
            offer_id=offer.offer_id,
            customer_id=offer.customer_id,
            old_offer_status=old_status,
            new_offer_status=new_status,
            change_reason=reason,
            snapshot_offer_details=offer.offer_details # Store a snapshot
        )
        db.add(history_entry)
        db.flush() # Use flush to ensure ID is generated before commit

    def _apply_offer_precedence_logic(self, db: Session, existing_customer: Customer, new_offer_data: Dict) -> Tuple[str, Optional[Offer]]:
        """
        FR15, FR16, FR20, FR21, FR25-FR32: Complex offer precedence rules.
        This is a simplified implementation. Real logic would be much more detailed.
        Returns a tuple: (action_taken, prevailing_offer_if_any)
        Action_taken can be "NEW_OFFER_PREVAILS", "EXISTING_OFFER_PREVAILS", "NEW_OFFER_DUPLICATE", "NEW_OFFER_EXPIRED", "NEW_OFFER_REJECTED".
        """
        new_product_type = new_offer_data.get("product_type")
        if not new_product_type:
            return "ERROR_MISSING_PRODUCT_TYPE", None

        # Find existing active offers for this customer
        existing_offers = db.query(Offer).filter(
            Offer.customer_id == existing_customer.customer_id,
            Offer.offer_status == "Active"
        ).all()

        for existing_offer in existing_offers:
            # FR15: Prevent modification of customer offers with a started loan application journey.
            # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
            # FR26: If pre-approved (prospect/E-aggregator) with journey started, and same customer comes via CLEAG/Insta, pre-approved prevails.
            if existing_offer.is_journey_started:
                # If any active offer has a journey started, new offers for the same product type are rejected.
                # For different product types, FR29-FR32 apply, which generally state new offers cannot be uploaded.
                # This implies a strict "first journey started" rule for existing active offers.
                return "NEW_OFFER_REJECTED_EXISTING_JOURNEY_STARTED", existing_offer

            # If existing offer's journey has NOT started
            # FR20: If an Enrich offer's journey has not started, it shall flow to CDP, and the previous offer will be moved to Duplicate.
            # FR25: If pre-approved (prospect/E-aggregator) with no journey started, and same customer comes via CLEAG/Insta, CLEAG/Insta prevails.
            if not existing_offer.is_journey_started:
                # Rule: If new offer is for the same product type, and existing is not started, new one replaces.
                if existing_offer.product_type == new_product_type:
                    old_status = existing_offer.offer_status
                    existing_offer.offer_status = "Duplicate" # Mark old offer as 'Duplicate'
                    existing_offer.updated_at = datetime.now(settings.TIMEZONE)
                    db.add(existing_offer)
                    self._log_offer_history(db, existing_offer, old_status, "Duplicate", f"Replaced by new offer for {new_product_type}")
                    return "NEW_OFFER_PREVAILS_REPLACED_OLD", None # New offer will be created

                # Specific precedence rules for different product types (FR25, FR29-FR32)
                # Example: If existing is 'Preapproved' (no journey) and new is 'Insta'/'E-aggregator', Insta/E-aggregator prevails.
                # Assuming 'Insta' and 'E-aggregator' are higher priority than 'Preapproved'/'Prospect' if no journey started.
                if existing_offer.product_type in ["Preapproved", "Prospect"] and \
                   new_product_type in ["Insta", "E-aggregator"]: # Assuming CLEAG/Insta maps to these
                    old_status = existing_offer.offer_status
                    existing_offer.offer_status = "Expired" # FR25 says "will expire"
                    existing_offer.updated_at = datetime.now(settings.TIMEZONE)
                    db.add(existing_offer)
                    self._log_offer_history(db, existing_offer, old_status, "Expired", f"Replaced by higher priority offer ({new_product_type})")
                    return "NEW_OFFER_PREVAILS_REPLACED_OLD", None

                # FR29-FR32: If a customer has an offer of type X, new offers of type Y cannot be uploaded.
                # This implies a hierarchy or mutual exclusivity.
                # For simplicity, if an active offer exists (journey not started), and the new offer is of a type that cannot be uploaded
                # according to FR29-FR32, then the new offer is rejected.
                # This requires a mapping of product types and their precedence/exclusivity.
                # Example: If existing is 'Employee Loan' and new is 'TW Loyalty', new cannot be uploaded (FR30).
                # This logic would be more complex and data-driven in a full implementation.
                # For now, if an active offer exists and no specific replacement rule applies, new offer is rejected.
                return "NEW_OFFER_REJECTED_BY_EXISTING_OFFER", existing_offer

        # If no conflicting active offers found, or if existing offers were marked for replacement, the new offer can be created.
        return "NEW_OFFER_CAN_BE_CREATED", None

    def _process_customer_and_offer(self, db: Session, raw_data: Dict) -> Tuple[Optional[Customer], Optional[Offer], Optional[str]]:
        """
        Helper to process a single customer/offer record.
        Returns (customer, offer, error_message)
        """
        error_message = self._validate_data(raw_data, ["mobile_number", "product_type", "offer_details"])
        if error_message:
            return None, None, error_message

        # FR34: Avoid DND (Do Not Disturb) customers.
        if raw_data.get("dnd_status", False):
             return None, None, "Customer is marked as Do Not Disturb (DND)."

        existing_customer = self.deduplication_service.find_existing_customer(db, raw_data)
        customer_id = None
        customer_obj = None
        is_new_customer = False

        if existing_customer:
            customer_id = existing_customer.customer_id
            customer_obj = existing_customer
            # Update existing customer attributes if new data is richer
            if raw_data.get("customer_attributes"):
                if existing_customer.customer_attributes:
                    existing_customer.customer_attributes.update(raw_data["customer_attributes"])
                else:
                    existing_customer.customer_attributes = raw_data["customer_attributes"]
            # Update other identifiable fields if provided and currently null
            for key in ["pan_number", "aadhaar_ref_number", "ucid_number", "previous_loan_app_number"]:
                if raw_data.get(key) and getattr(existing_customer, key) is None:
                    setattr(existing_customer, key, raw_data[key])
            if raw_data.get("dnd_status") is not None: # Allow updating DND status
                existing_customer.dnd_status = raw_data["dnd_status"]

            existing_customer.updated_at = datetime.now(settings.TIMEZONE)
            db.add(existing_customer)
            db.flush() # Flush to ensure updates are visible for offer processing
        else:
            # Create new customer
            is_new_customer = True
            customer_id = uuid.uuid4()
            customer_create_data = CustomerCreate(
                customer_id=customer_id,
                mobile_number=raw_data.get("mobile_number"),
                pan_number=raw_data.get("pan_number"),
                aadhaar_ref_number=raw_data.get("aadhaar_ref_number"),
                ucid_number=raw_data.get("ucid_number"),
                previous_loan_app_number=raw_data.get("previous_loan_app_number"),
                customer_attributes=raw_data.get("customer_attributes", {}),
                customer_segments=raw_data.get("customer_segments", []),
                propensity_flag=raw_data.get("propensity_flag"),
                dnd_status=raw_data.get("dnd_status", False)
            )
            customer_obj = Customer(**customer_create_data.dict())
            db.add(customer_obj)
            db.flush() # Flush to get customer_id for offer

        # Process Offer
        offer_obj = None
        action, prevailing_offer = self._apply_offer_precedence_logic(db, customer_obj, raw_data)

        if action == "NEW_OFFER_CAN_BE_CREATED" or action == "NEW_OFFER_PREVAILS_REPLACED_OLD":
            offer_id = uuid.uuid4()
            offer_create_data = OfferCreate(
                offer_id=offer_id,
                customer_id=customer_id,
                offer_type=raw_data.get("offer_type", "Fresh"), # FR19: 'Fresh', 'Enrich', 'New-old', 'New-new'
                offer_status=raw_data.get("offer_status", "Active"), # FR18: 'Active', 'Inactive', 'Expired'
                product_type=raw_data.get("product_type"),
                offer_details=raw_data.get("offer_details", {}),
                offer_start_date=raw_data.get("offer_start_date"),
                offer_end_date=raw_data.get("offer_end_date"),
                is_journey_started=raw_data.get("is_journey_started", False),
                loan_application_id=raw_data.get("loan_application_id")
            )
            offer_obj = Offer(**offer_create_data.dict())
            db.add(offer_obj)
            self._log_offer_history(db, offer_obj, "N/A", offer_obj.offer_status, "New offer created")
        elif action == "NEW_OFFER_REJECTED_EXISTING_JOURNEY_STARTED":
            return customer_obj, None, f"New offer rejected as an existing offer (ID: {prevailing_offer.offer_id}) has journey started for this customer."
        elif action == "NEW_OFFER_REJECTED_BY_EXISTING_OFFER":
            return customer_obj, None, f"New offer rejected due to existing active offer (ID: {prevailing_offer.offer_id}) and precedence rules."
        elif action == "ERROR_MISSING_PRODUCT_TYPE":
            return customer_obj, None, "Offer could not be processed: Missing product_type."
        else:
            # This covers other rejection scenarios or unexpected outcomes from precedence logic
            return customer_obj, None, f"New offer not processed due to precedence rules: {action}"

        db.commit()
        db.refresh(customer_obj)
        if offer_obj:
            db.refresh(offer_obj)
        return customer_obj, offer_obj, None

    def ingest_offermart_batch_data(self, db: Session, data: List[Dict]) -> Dict:
        """
        FR9: The system shall receive Offer data and Customer data from Offermart System on a daily basis via a staging area.
        Processes a batch of data from Offermart.
        """
        results = {
            "total_records": len(data),
            "processed_successfully": 0,
            "failed_records": [],
            "new_customers": 0,
            "updated_customers": 0,
            "new_offers": 0,
            "rejected_offers": 0,
            "duplicate_offers_marked": 0 # Offers that were marked duplicate due to new incoming offers
        }

        for i, record in enumerate(data):
            try:
                customer, offer, error_message = self._process_customer_and_offer(db, record)
                if error_message:
                    results["failed_records"].append({"row_index": i, "data": record, "error": error_message})
                    if "rejected" in error_message:
                        results["rejected_offers"] += 1
                    elif "DND" in error_message:
                        results["rejected_offers"] += 1
                    # Note: "duplicate_offers_marked" is counted within _apply_offer_precedence_logic
                else:
                    results["processed_successfully"] += 1
                    # Simple check for new vs. updated customer based on creation/update timestamps
                    if customer and customer.created_at == customer.updated_at:
                        results["new_customers"] += 1
                    else:
                        results["updated_customers"] += 1
                    if offer:
                        results["new_offers"] += 1
            except Exception as e:
                db.rollback() # Rollback current transaction for this record
                results["failed_records"].append({"row_index": i, "data": record, "error": str(e)})
                # Re-raise if it's a critical error that should stop the batch, otherwise log and continue.
                # For batch processing, usually continue and report all errors.

        return results

    def ingest_realtime_lead(self, db: Session, lead_data: LeadCreate) -> Tuple[CustomerInDB, OfferInDB]:
        """
        FR11: The system shall receive real-time data from Insta or E-aggregators into the CDP via Open APIs.
        FR12: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database.
        Processes a single real-time lead.
        """
        # Convert Pydantic model to dict for internal processing
        raw_data = lead_data.dict(exclude_unset=True)
        # Ensure offer_details is a dict, even if empty
        if 'offer_details' not in raw_data or raw_data['offer_details'] is None:
            raw_data['offer_details'] = {}

        customer, offer, error_message = self._process_customer_and_offer(db, raw_data)

        if error_message:
            # Raise an exception for API to catch and return appropriate error response
            raise ValueError(f"Lead ingestion failed: {error_message}")

        if not customer or not offer:
            # This case should ideally be caught by error_message, but as a fallback
            raise RuntimeError("Lead ingestion failed unexpectedly: No customer or offer created.")

        return CustomerInDB.from_orm(customer), OfferInDB.from_orm(offer)

    def process_admin_upload(self, db: Session, file_content: bytes, file_type: str) -> Tuple[bytes, bytes]:
        """
        FR43: The system shall allow uploading customer details on the Admin Portal for Prospect, TW Loyalty, Topup, and Employee loans.
        FR45: The system shall generate a success file upon successful data upload on the Admin Portal.
        FR46: The system shall generate an error file with an 'Error Desc' column for failed data uploads on the Admin Portal.
        Processes an uploaded CSV/Excel file.
        Returns (success_file_bytes, error_file_bytes)
        """
        if file_type not in ["csv", "xlsx"]:
            raise ValueError("Unsupported file type. Only CSV and XLSX are supported.")

        input_io = io.BytesIO(file_content)
        if file_type == "csv":
            df = pd.read_csv(input_io)
        else: # xlsx
            df = pd.read_excel(input_io)

        success_records = []
        error_records = []

        # Convert DataFrame rows to dictionaries for processing
        for index, row in df.iterrows():
            record_data = row.to_dict()
            # Convert keys to lowercase for consistency with internal processing
            record_data = {k.lower(): v for k, v in record_data.items()}

            # Convert pandas NaN to None for database compatibility
            for key, value in record_data.items():
                if pd.isna(value):
                    record_data[key] = None
            
            # Handle boolean fields from string/int if necessary (e.g., 'TRUE', '1', '0')
            if 'dnd_status' in record_data and record_data['dnd_status'] is not None:
                record_data['dnd_status'] = str(record_data['dnd_status']).lower() in ['true', '1', 'yes']
            if 'is_journey_started' in record_data and record_data['is_journey_started'] is not None:
                record_data['is_journey_started'] = str(record_data['is_journey_started']).lower() in ['true', '1', 'yes']

            try:
                # Use a new session for each row to ensure atomicity per row for admin uploads.
                # For very large files, consider batching commits for performance, but this simplifies error handling.
                with SessionLocal() as row_db:
                    customer, offer, error_message = self._process_customer_and_offer(row_db, record_data)
                    if error_message:
                        error_records.append({**record_data, "error_desc": error_message})
                    else:
                        success_records.append({**record_data, "customer_id": str(customer.customer_id), "offer_id": str(offer.offer_id) if offer else "N/A"})
            except Exception as e:
                # Catch any unexpected exceptions during processing of a row
                error_records.append({**record_data, "error_desc": str(e)})

        # Generate success file
        success_df = pd.DataFrame(success_records)
        success_output = io.BytesIO()
        if file_type == "csv":
            success_df.to_csv(success_output, index=False)
        else:
            success_df.to_excel(success_output, index=False)
        success_output.seek(0)

        # Generate error file
        error_df = pd.DataFrame(error_records)
        error_output = io.BytesIO()
        if file_type == "csv":
            error_df.to_csv(error_output, index=False)
        else:
            error_df.to_excel(error_output, index=False)
        error_output.seek(0)

        return success_output.getvalue(), error_output.getvalue()

# Instantiate the service for use in API routes or scheduled tasks
data_ingestion_service = DataIngestionService()