import asyncio
import csv
import io
import uuid
import json
import os
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_, and_

# Assuming these modules exist in the project structure
from app.db.session import AsyncSessionLocal
from app.models.customer import Customer
from app.models.offer import Offer
from app.models.offer_history import OfferHistory
from app.schemas.customer import CustomerCreate
from app.schemas.offer import OfferCreate
from app.core.config import settings # Assuming settings are defined here

# Define expected CSV columns for customer offer uploads
# These should align with the data expected for CustomerCreate and OfferCreate schemas,
# plus any additional fields for processing logic (like dnd_status from CSV).
EXPECTED_CSV_COLUMNS = [
    "mobile_number", "pan_number", "aadhaar_ref_number", "ucid_number",
    "previous_loan_app_number", "product_type", "offer_type",
    "offer_details_json", "offer_start_date", "offer_end_date",
    "is_journey_started", "loan_application_id", "customer_attributes_json",
    "customer_segments", "propensity_flag", "dnd_status"
]

async def _get_customer_by_identifiers(db: AsyncSession,
                                       mobile_number: Optional[str] = None,
                                       pan_number: Optional[str] = None,
                                       aadhaar_ref_number: Optional[str] = None,
                                       ucid_number: Optional[str] = None,
                                       previous_loan_app_number: Optional[str] = None) -> Optional[Customer]:
    """Helper to find a customer by any of the unique identifiers."""
    conditions = []
    if mobile_number:
        conditions.append(Customer.mobile_number == mobile_number)
    if pan_number:
        conditions.append(Customer.pan_number == pan_number)
    if aadhaar_ref_number:
        conditions.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
    if ucid_number:
        conditions.append(Customer.ucid_number == ucid_number)
    if previous_loan_app_number:
        conditions.append(Customer.previous_loan_app_number == previous_loan_app_number)

    if not conditions:
        return None

    stmt = select(Customer).where(or_(*conditions))
    result = await db.execute(stmt)
    return result.scalars().first()

async def _create_or_update_customer(db: AsyncSession, customer_data: Dict) -> Customer:
    """Creates a new customer or updates an existing one based on identifiers."""
    customer = await _get_customer_by_identifiers(db,
                                                  mobile_number=customer_data.get("mobile_number"),
                                                  pan_number=customer_data.get("pan_number"),
                                                  aadhaar_ref_number=customer_data.get("aadhaar_ref_number"),
                                                  ucid_number=customer_data.get("ucid_number"),
                                                  previous_loan_app_number=customer_data.get("previous_loan_app_number"))

    if customer:
        # Update existing customer
        # Only update fields that are provided and not None
        update_data = {k: v for k, v in customer_data.items() if v is not None and hasattr(Customer, k)}
        for key, value in update_data.items():
            setattr(customer, key, value)
        customer.updated_at = datetime.now(timezone.utc)
    else:
        # Create new customer
        # Filter out None values for Pydantic model creation
        create_data = {k: v for k, v in customer_data.items() if v is not None}
        customer_create_schema = CustomerCreate(**create_data)
        customer = Customer(**customer_create_schema.dict())
        db.add(customer)
    await db.flush() # To get customer_id if new, and ensure updates are reflected for subsequent queries
    return customer

async def _process_single_offer_row(db: AsyncSession, row_data: Dict) -> Tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    """
    Processes a single row of offer data from the CSV.
    Returns (unique_record, duplicate_record, error_record)
    """
    error_record = None
    unique_record = None
    duplicate_record = None

    # 1. Basic Validation (FR1, NFR3)
    # Check for mandatory fields
    if not row_data.get("mobile_number") or not row_data.get("product_type"):
        error_record = {**row_data, "error_desc": "Missing mandatory fields (mobile_number or product_type)."}
        return None, None, error_record

    try:
        # Convert date strings to date objects
        offer_start_date = datetime.strptime(row_data["offer_start_date"], "%Y-%m-%d").date() if row_data.get("offer_start_date") else None
        offer_end_date = datetime.strptime(row_data["offer_end_date"], "%Y-%m-%d").date() if row_data.get("offer_end_date") else None
        is_journey_started = row_data.get("is_journey_started", "FALSE").upper() == "TRUE"
        loan_application_id = row_data.get("loan_application_id")

        # Parse JSON fields, default to empty dict if parsing fails or field is empty
        offer_details = json.loads(row_data.get("offer_details_json") or "{}")
        customer_attributes = json.loads(row_data.get("customer_attributes_json") or "{}")
        customer_segments = [s.strip() for s in row_data.get("customer_segments", "").split(',')] if row_data.get("customer_segments") else []
        dnd_status_from_csv = row_data.get("dnd_status", "FALSE").upper() == "TRUE"

    except (ValueError, json.JSONDecodeError) as e:
        error_record = {**row_data, "error_desc": f"Data parsing error: {e}"}
        return None, None, error_record

    # Prepare customer data for creation/update
    customer_data_for_db = {
        "mobile_number": row_data.get("mobile_number") or None,
        "pan_number": row_data.get("pan_number") or None,
        "aadhaar_ref_number": row_data.get("aadhaar_ref_number") or None,
        "ucid_number": row_data.get("ucid_number") or None,
        "previous_loan_app_number": row_data.get("previous_loan_app_number") or None,
        "customer_attributes": customer_attributes,
        "customer_segments": customer_segments,
        "propensity_flag": row_data.get("propensity_flag") or None,
        "dnd_status": dnd_status_from_csv
    }

    # 2. Create/Update Customer (FR2, FR3)
    customer = await _create_or_update_customer(db, customer_data_for_db)

    # FR34: Avoid DND (Do Not Disturb) customers.
    # If customer is DND, new offers for them should not be processed.
    if customer.dnd_status:
        error_record = {**row_data, "error_desc": "Customer is marked as DND. Offer not processed."}
        return None, None, error_record

    # 3. Deduplication and Offer Precedence Logic (FR2, FR4, FR5, FR6, FR15, FR20, FR21, FR25-FR32)
    # Fetch existing active offers for this customer
    existing_offers_stmt = select(Offer).where(
        and_(
            Offer.customer_id == customer.customer_id,
            Offer.offer_status == "Active"
        )
    )
    existing_active_offers: List[Offer] = (await db.execute(existing_offers_stmt)).scalars().all()

    new_offer_product_type = row_data["product_type"]
    new_offer_type = row_data.get("offer_type", "Fresh") # Default to 'Fresh'

    # Determine if the new offer should be processed or if an existing one prevails
    should_create_new_offer = True
    for existing_offer in existing_active_offers:
        # FR15: Prevent modification of customer offers with a started loan application journey
        # FR21: If an Enrich offer's journey has started, it shall not flow into CDP.
        if existing_offer.is_journey_started:
            error_record = {**row_data, "error_desc": f"Existing offer for product '{existing_offer.product_type}' (ID: {existing_offer.offer_id}) has started journey (LAN: {existing_offer.loan_application_id}). New offer cannot be processed (FR15, FR21)."}
            should_create_new_offer = False
            break

        # FR25: If customer in pre-approved base (prospect or E-aggregator) with no journey started,
        # and same customer comes via CLEAG/Insta, CLEAG/Insta journey shall prevail, uploaded pre-approved offer will expire.
        if (new_offer_product_type.lower() in ["cleag", "insta"]) and \
           (existing_offer.product_type.lower() in ["preapproved", "e-aggregator"]):
            existing_offer.offer_status = "Expired"
            existing_offer.updated_at = datetime.now(timezone.utc)
            db.add(OfferHistory(
                offer_id=existing_offer.offer_id,
                customer_id=customer.customer_id,
                old_offer_status="Active",
                new_offer_status="Expired",
                change_reason=f"Superseded by new {new_offer_product_type} offer (FR25)",
                snapshot_offer_details=existing_offer.offer_details
            ))
            print(f"Offer {existing_offer.offer_id} expired by FR25.")
            # Continue to process the new offer, as the old one is now expired
            continue

        # FR20: If an Enrich offer's journey has not started, it shall flow to CDP,
        # and the previous offer will be moved to Duplicate.
        if new_offer_type.lower() == "enrich":
            existing_offer.offer_status = "Duplicate"
            existing_offer.updated_at = datetime.now(timezone.utc)
            db.add(OfferHistory(
                offer_id=existing_offer.offer_id,
                customer_id=customer.customer_id,
                old_offer_status="Active",
                new_offer_status="Duplicate",
                change_reason=f"Superseded by new Enrich offer (FR20)",
                snapshot_offer_details=existing_offer.offer_details
            ))
            print(f"Offer {existing_offer.offer_id} moved to Duplicate by FR20.")
            # Continue to process the new offer
            continue

        # FR29-FR32: Strict rules about what cannot be uploaded if certain offers exist.
        # This implies a hierarchy or mutual exclusivity.
        # Simplified interpretation: If a "higher priority" offer exists, the new one is rejected.
        # This requires a defined hierarchy. Let's assume a simple one for demonstration:
        # Employee Loan > TW Loyalty > Topup > Pre-approved E-aggregator > Prospect > CLEAG/Insta
        # (This is an example hierarchy, actual one needs to be confirmed from BRD ambiguities)
        offer_priority = {
            "employee loan": 5, "tw loyalty": 4, "top-up": 3,
            "preapproved": 2, "e-aggregator": 2, "prospect": 1,
            "cleag": 0, "insta": 0
        }
        existing_priority = offer_priority.get(existing_offer.product_type.lower(), -1)
        new_priority = offer_priority.get(new_offer_product_type.lower(), -1)

        if existing_priority > new_priority:
            # Existing offer has higher priority, new offer cannot be uploaded (FR29-FR32)
            duplicate_record = {**row_data, "error_desc": f"New offer ({new_offer_product_type}) cannot be uploaded as existing higher priority offer ({existing_offer.product_type}) exists (FR29-FR32)."}
            should_create_new_offer = False
            break
        elif existing_priority == new_priority and existing_offer.product_type.lower() == new_offer_product_type.lower():
            # If same product type and same priority, and not explicitly handled by FR25/FR20,
            # then the new offer might supersede the old one, or be a duplicate.
            # For simplicity, let's say the new one supersedes if not journey started.
            existing_offer.offer_status = "Expired"
            existing_offer.updated_at = datetime.now(timezone.utc)
            db.add(OfferHistory(
                offer_id=existing_offer.offer_id,
                customer_id=customer.customer_id,
                old_offer_status="Active",
                new_offer_status="Expired",
                change_reason=f"Superseded by new {new_offer_product_type} offer (same product type, no journey started)",
                snapshot_offer_details=existing_offer.offer_details
            ))
            print(f"Offer {existing_offer.offer_id} expired by same product type rule.")
            # Continue to process the new offer
            continue
        else:
            # If none of the specific rules apply and an active offer still exists,
            # the new offer is considered a duplicate.
            duplicate_record = {**row_data, "error_desc": f"New offer is duplicate; existing {existing_offer.product_type} offer prevails (general rule)."}
            should_create_new_offer = False
            break


    if not should_create_new_offer:
        return None, duplicate_record, error_record # If a rule prevented creation, return

    # 4. Create New Offer (if not prevented by precedence rules)
    offer_create_data = OfferCreate(
        customer_id=customer.customer_id,
        offer_type=new_offer_type,
        offer_status="Active", # New offer is active by default
        product_type=new_offer_product_type,
        offer_details=offer_details,
        offer_start_date=offer_start_date,
        offer_end_date=offer_end_date,
        is_journey_started=is_journey_started,
        loan_application_id=loan_application_id
    )
    new_offer = Offer(**offer_create_data.dict())
    db.add(new_offer)
    await db.flush() # To get offer_id

    # Record offer history for the new offer
    db.add(OfferHistory(
        offer_id=new_offer.offer_id,
        customer_id=customer.customer_id,
        old_offer_status=None, # New offer
        new_offer_status=new_offer.offer_status,
        change_reason="New offer uploaded",
        snapshot_offer_details=new_offer.offer_details
    ))

    # FR44: Generate leads for customers in the system upon successful upload via the Admin Portal.
    # This is implicitly handled by creating the offer. If `is_journey_started` is False, it's a lead.
    # No explicit external call here, but the record itself represents the lead.

    unique_record = {
        "customer_id": str(customer.customer_id),
        "offer_id": str(new_offer.offer_id),
        "mobile_number": customer.mobile_number,
        "product_type": new_offer.product_type,
        "offer_status": new_offer.offer_status,
        "is_journey_started": new_offer.is_journey_started,
        "loan_application_id": new_offer.loan_application_id,
        "message": "Offer processed successfully."
    }
    return unique_record, duplicate_record, error_record

async def process_customer_offer_upload(file_content: bytes, job_id: uuid.UUID):
    """
    Background task to process uploaded customer offer CSV file.
    Args:
        file_content: The content of the uploaded CSV file as bytes.
        job_id: A unique ID for this processing job.
    """
    print(f"Starting background processing for job_id: {job_id}")

    unique_records: List[Dict] = []
    duplicate_records: List[Dict] = []
    error_records: List[Dict] = []

    # Decode bytes to string and wrap in StringIO for csv.reader
    csv_file = io.StringIO(file_content.decode('utf-8'))
    reader = csv.DictReader(csv_file)

    # Validate CSV headers
    if not all(col in reader.fieldnames for col in EXPECTED_CSV_COLUMNS):
        missing_cols = [col for col in EXPECTED_CSV_COLUMNS if col not in reader.fieldnames]
        error_records.append({"job_id": str(job_id), "error_desc": f"CSV header mismatch. Missing columns: {', '.join(missing_cols)}. Expected columns: {', '.join(EXPECTED_CSV_COLUMNS)}"})
        print(f"CSV header mismatch for job {job_id}. Missing: {missing_cols}")
        # If headers are critically wrong, we might want to stop here.
        # For now, we'll proceed, but rows might fail due to missing keys.

    async with AsyncSessionLocal() as db:
        for i, row in enumerate(reader):
            # Ensure all expected columns are present in row_data, defaulting to empty string
            row_data = {col: row.get(col, "") for col in EXPECTED_CSV_COLUMNS}
            unique, duplicate, error = await _process_single_offer_row(db, row_data)
            if unique:
                unique_records.append(unique)
            if duplicate:
                duplicate_records.append(duplicate)
            if error:
                error_records.append(error)
            # Commit periodically to prevent large transactions and memory issues
            if (i + 1) % settings.DB_COMMIT_BATCH_SIZE == 0: # Assuming DB_COMMIT_BATCH_SIZE in settings
                await db.commit()
                print(f"Job {job_id}: Processed {i+1} rows, committed.")
        await db.commit() # Final commit for any remaining rows

    # Generate output files (FR39, FR40, FR41, FR42, FR45, FR46)
    # These files would typically be stored in a persistent storage (S3, shared volume)
    # and their paths/URLs stored in a job status table for download.
    # For this exercise, we'll simulate saving them locally.

    output_dir = settings.UPLOAD_FILE_STORAGE_PATH
    os.makedirs(output_dir, exist_ok=True)

    # Helper to write CSV files
    def write_csv_file(file_path: str, records: List[Dict], default_fieldnames: List[str]):
        if records:
            # Collect all possible keys from all records to ensure all columns are present
            all_keys = set()
            for record in records:
                all_keys.update(record.keys())
            fieldnames = sorted(list(all_keys)) if all_keys else default_fieldnames
            if not fieldnames: # Fallback if no records and no default fieldnames
                fieldnames = ["message"] # At least one column for empty files
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(records)
            print(f"File generated: {file_path}")
        else:
            print(f"No records for {file_path}. File not generated.")

    # Success File (FR45) / Unique Data File (FR41)
    success_file_path = os.path.join(output_dir, f"job_{job_id}_success.csv")
    write_csv_file(success_file_path, unique_records, ["customer_id", "offer_id", "mobile_number", "product_type", "offer_status", "message"])

    # Error File (FR46)
    error_file_path = os.path.join(output_dir, f"job_{job_id}_error.csv")
    write_csv_file(error_file_path, error_records, EXPECTED_CSV_COLUMNS + ["error_desc"])

    # Duplicate Data File (FR40)
    duplicate_file_path = os.path.join(output_dir, f"job_{job_id}_duplicate.csv")
    write_csv_file(duplicate_file_path, duplicate_records, EXPECTED_CSV_COLUMNS + ["error_desc"])

    print(f"Finished background processing for job_id: {job_id}")

async def generate_moengage_file() -> Optional[str]:
    """
    Generates the Moengage format CSV file (FR54, FR55).
    This would typically be a scheduled task or triggered by an API endpoint.
    Returns the path to the generated file, or None if no file was generated.
    """
    print("Starting Moengage file generation...")
    moengage_records: List[Dict] = []
    async with AsyncSessionLocal() as db:
        # Query for active offers that are ready for campaigning
        # FR54: Generate a Moengage format file in .csv format.
        # Criteria: Active offers, not journey started, customer not DND.
        stmt = select(Customer, Offer).join(Offer).where(
            and_(
                Offer.offer_status == "Active",
                Offer.is_journey_started == False,
                Customer.dnd_status == False
            )
        )
        result = await db.execute(stmt)
        for customer, offer in result.all():
            # The exact Moengage format is not specified.
            # We'll create a comprehensive record including customer and offer details.
            # Moengage typically uses `customer_id` or `mobile_number` as primary key.
            record = {
                "customer_id": str(customer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan_number": customer.pan_number,
                "aadhaar_ref_number": customer.aadhaar_ref_number,
                "ucid_number": customer.ucid_number,
                "offer_id": str(offer.offer_id),
                "product_type": offer.product_type,
                "offer_type": offer.offer_type,
                "offer_status": offer.offer_status,
                "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else "",
                "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else "",
                "is_journey_started": str(offer.is_journey_started).upper(),
                "loan_application_id": offer.loan_application_id,
                "customer_segments": ",".join(customer.customer_segments) if customer.customer_segments else "",
                "propensity_flag": customer.propensity_flag,
                "dnd_status": str(customer.dnd_status).upper(),
                # Flatten offer_details JSONB into top-level keys if possible/needed by Moengage
                **offer.offer_details # This will add keys from offer_details dict
            }
            moengage_records.append(record)

    output_dir = settings.MOENGAGE_FILE_STORAGE_PATH
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    moengage_file_name = f"moengage_campaign_data_{timestamp}.csv"
    moengage_file_path = os.path.join(output_dir, moengage_file_name)

    if moengage_records:
        # Collect all possible keys from all records to ensure all columns are present
        all_keys = set()
        for record in moengage_records:
            all_keys.update(record.keys())
        fieldnames = sorted(list(all_keys)) # Sort for consistent column order

        with open(moengage_file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(moengage_records)
        print(f"Moengage file generated: {moengage_file_path}")
        return moengage_file_path
    else:
        print("No records found for Moengage file generation.")
        return None

async def update_offer_statuses():
    """
    Scheduled task to update offer statuses (FR51, FR52, FR53).
    """
    print("Starting offer status update task...")
    async with AsyncSessionLocal() as db:
        current_date = date.today()
        current_datetime_utc = datetime.now(timezone.utc)

        # FR51: Mark offers as expired based on offer end dates for non-journey started customers.
        stmt_expire_by_date = select(Offer).where(
            and_(
                Offer.offer_status == "Active",
                Offer.is_journey_started == False,
                Offer.offer_end_date < current_date
            )
        )
        offers_to_expire = (await db.execute(stmt_expire_by_date)).scalars().all()
        for offer in offers_to_expire:
            old_status = offer.offer_status
            offer.offer_status = "Expired"
            offer.updated_at = current_datetime_utc
            db.add(OfferHistory(
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Expired",
                change_reason="Offer expired based on end date (FR51)",
                snapshot_offer_details=offer.offer_details # Snapshot current details
            ))
            print(f"Offer {offer.offer_id} expired by date.")

        # FR53: Mark offers as expired within the offers data if the LAN validity post loan application journey start date is over.
        # Question 9: "Clarification is required to understand the period after which the LAN to be marked as Expired for that Offer."
        # Assuming a default LAN validity period (e.g., 90 days) for MVP. This should be configurable.
        LAN_VALIDITY_DAYS = settings.LAN_VALIDITY_DAYS # e.g., 90 days from config

        # This requires knowing the exact journey start date. If `updated_at` is updated when journey starts,
        # we can use that. Otherwise, a dedicated `journey_start_timestamp` column would be ideal.
        # For now, assuming `updated_at` is a proxy for the last significant update, which could be journey start.
        stmt_expire_by_lan = select(Offer).where(
            and_(
                Offer.offer_status == "Active",
                Offer.is_journey_started == True,
                Offer.loan_application_id.isnot(None),
                Offer.updated_at < current_datetime_utc - timedelta(days=LAN_VALIDITY_DAYS)
            )
        )
        offers_to_expire_lan = (await db.execute(stmt_expire_by_lan)).scalars().all()
        for offer in offers_to_expire_lan:
            old_status = offer.offer_status
            offer.offer_status = "Expired"
            offer.updated_at = current_datetime_utc
            db.add(OfferHistory(
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Expired",
                change_reason=f"Offer expired based on LAN validity ({LAN_VALIDITY_DAYS} days) (FR53)",
                snapshot_offer_details=offer.offer_details
            ))
            print(f"Offer {offer.offer_id} expired by LAN validity.")

        # FR16, FR52: Check for new replenishment offers for loan applications that have expired or been rejected.
        # This is a complex business logic that would likely involve:
        # 1. Identifying customers with expired/rejected offers.
        # 2. Re-evaluating their eligibility for new offers (potentially calling analytics/offermart).
        # 3. Creating new offers if eligible.
        # This task only marks existing offers. The generation of *new* replenishment offers is outside this scope.
        print("Checking for replenishment offers (logic for generation is external to this task)...")

        await db.commit()
    print("Finished offer status update task.")

async def cleanup_old_data():
    """
    Scheduled task to clean up old data (FR23, FR37, NFR9, NFR10).
    """
    print("Starting data cleanup task...")
    async with AsyncSessionLocal() as db:
        current_datetime_utc = datetime.now(timezone.utc)

        # FR37, NFR10: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
        # This implies deleting customer and offer data.
        # For safety, we will only delete offers that are NOT 'Active' and are older than 3 months.
        # Deleting customers is more complex as it might affect other data.
        # A more robust solution might involve soft deletes or archiving to a data warehouse.
        three_months_ago = current_datetime_utc - timedelta(days=settings.CDP_DATA_RETENTION_DAYS) # e.g., 90 days

        # Delete offers that are not active and are older than the retention period
        stmt_delete_old_inactive_offers = select(Offer).where(
            and_(
                Offer.offer_status != "Active",
                Offer.created_at < three_months_ago
            )
        )
        offers_to_delete = (await db.execute(stmt_delete_old_inactive_offers)).scalars().all()
        for offer in offers_to_delete:
            await db.delete(offer)
            print(f"Deleted old inactive offer: {offer.offer_id}")

        # FR23, NFR9: Maintain offer history for the past 6 months.
        six_months_ago = current_datetime_utc - timedelta(days=settings.OFFER_HISTORY_RETENTION_DAYS) # e.g., 180 days

        stmt_delete_old_history = select(OfferHistory).where(
            OfferHistory.change_timestamp < six_months_ago
        )
        history_to_delete = (await db.execute(stmt_delete_old_history)).scalars().all()
        for history_record in history_to_delete:
            await db.delete(history_record)
            print(f"Deleted old offer history: {history_record.history_id}")

        await db.commit()
    print("Finished data cleanup task.")