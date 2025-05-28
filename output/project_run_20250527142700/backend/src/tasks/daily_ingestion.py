import uuid
from datetime import datetime, timedelta
from sqlalchemy import or_, func
from flask import current_app # To get app context for db operations and logger

# Assuming these are defined in backend.models and db in backend.database
# Adjust import path for db if it's initialized directly in backend/__init__.py or backend/app.py
from backend.database import db
from backend.models import Customer, Offer, OfferHistory

# Assuming services for validation and deduplication are in backend.src.services
# Adjust import paths if services are directly under backend/services
from backend.src.services.validation_service import validate_offermart_payload
from backend.src.services.deduplication_service import deduplicate_and_process_offermart_offer, update_expired_offers_for_journey_started_customers

def fetch_offermart_staging_data():
    """
    Simulates fetching daily data from the Offermart staging area.
    In a real scenario, this would involve reading from a file (CSV/Excel),
    an S3 bucket, or calling an internal API that exposes the staging data.
    The data structure should align with expected Offermart data, including
    customer identifiers and offer details.

    Returns:
        list: A list of dictionaries, each representing a record from Offermart.
    """
    # This is placeholder data. In a real system, this would come from a file or external system.
    # The structure should align with expected Offermart data.
    # Example fields based on BRD: mobile, pan, aadhaar, ucid, loan_application_number,
    # offer_type, offer_status, propensity, valid_until, source_offer_id, channel, product_type.
    return [
        {
            "source_offer_id": "OM_FRESH_001",
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhaar_number": "111122223333",
            "ucid_number": "UCID001",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "High",
            "loan_application_number": None,
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "source_system": "Offermart",
            "channel": "Digital",
            "product_type": "Consumer Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_PREAPP_002",
            "mobile_number": "9988776655",
            "pan_number": "FGHIJ5678K",
            "aadhaar_number": "444455556666",
            "ucid_number": "UCID002",
            "offer_type": "Preapproved",
            "offer_status": "Active",
            "propensity": "Medium",
            "loan_application_number": None,
            "valid_until": (datetime.now() + timedelta(days=25)).isoformat(),
            "source_system": "Offermart",
            "channel": "Branch",
            "product_type": "Consumer Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_ENRICH_003", # An 'Enrich' offer for OM_FRESH_001 (same customer)
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "aadhaar_number": "111122223333",
            "ucid_number": "UCID001",
            "offer_type": "Enrich",
            "offer_status": "Active",
            "propensity": "Very High",
            "loan_application_number": None, # No journey started yet for this customer's offers
            "valid_until": (datetime.now() + timedelta(days=45)).isoformat(),
            "source_system": "Offermart",
            "channel": "Digital",
            "product_type": "Consumer Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_TOPUP_004", # A Top-up offer
            "mobile_number": "9999999999",
            "pan_number": "KLMNO1234P",
            "aadhaar_number": "777788889999",
            "ucid_number": "UCID003",
            "offer_type": "Top-up",
            "offer_status": "Active",
            "propensity": "High",
            "loan_application_number": None,
            "valid_until": (datetime.now() + timedelta(days=60)).isoformat(),
            "source_system": "Offermart",
            "channel": "App",
            "product_type": "Top-up Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_TOPUP_005", # Another Top-up offer for the same customer as OM_TOPUP_004
            "mobile_number": "9999999999",
            "pan_number": "KLMNO1234P",
            "aadhaar_number": "777788889999",
            "ucid_number": "UCID003",
            "offer_type": "Top-up",
            "offer_status": "Active",
            "propensity": "Medium",
            "loan_application_number": None,
            "valid_until": (datetime.now() + timedelta(days=50)).isoformat(),
            "source_system": "Offermart",
            "channel": "Web",
            "product_type": "Top-up Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_JOURNEY_006", # Offer with an active journey (simulated)
            "mobile_number": "1112223333",
            "pan_number": "PQRST5678U",
            "aadhaar_number": "999988887777",
            "ucid_number": "UCID004",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "Low",
            "loan_application_number": "LAN12345", # Simulating an active journey
            "valid_until": (datetime.now() + timedelta(days=10)).isoformat(),
            "source_system": "Offermart",
            "channel": "SMS",
            "product_type": "Consumer Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_ENRICH_007", # Enrich offer for OM_JOURNEY_006 (same customer, active journey)
            "mobile_number": "1112223333",
            "pan_number": "PQRST5678U",
            "aadhaar_number": "999988887777",
            "ucid_number": "UCID004",
            "offer_type": "Enrich",
            "offer_status": "Active",
            "propensity": "High",
            "loan_application_number": "LAN12345", # Still active journey
            "valid_until": (datetime.now() + timedelta(days=20)).isoformat(),
            "source_system": "Offermart",
            "channel": "SMS",
            "product_type": "Consumer Loan",
            "is_dnd": False
        },
        {
            "source_offer_id": "OM_DND_008", # DND customer
            "mobile_number": "1234567890",
            "pan_number": "VWXYZ9876A",
            "aadhaar_number": "123456789012",
            "ucid_number": "UCID005",
            "offer_type": "Fresh",
            "offer_status": "Active",
            "propensity": "Medium",
            "loan_application_number": None,
            "valid_until": (datetime.now() + timedelta(days=30)).isoformat(),
            "source_system": "Offermart",
            "channel": "Digital",
            "product_type": "Consumer Loan",
            "is_dnd": True # This customer is DND
        }
    ]

def daily_offermart_ingestion_task():
    """
    Main function to perform daily data ingestion from Offermart.
    This function should be called within a Flask application context
    to ensure database operations and logging work correctly.
    """
    current_app.logger.info("Starting daily Offermart data ingestion task...")
    ingested_new_offers_count = 0
    updated_offers_count = 0
    marked_as_duplicate_count = 0
    skipped_due_to_journey_count = 0
    error_records = []

    offermart_data = fetch_offermart_staging_data()

    for i, record in enumerate(offermart_data):
        try:
            # 1. Basic Column-level Data Validation (FR2, NFR8)
            validation_errors = validate_offermart_payload(record)
            if validation_errors:
                error_records.append({
                    "record_index": i,
                    "data": record,
                    "errors": validation_errors,
                    "stage": "Validation"
                })
                current_app.logger.warning(f"Validation failed for record {i}: {validation_errors}")
                continue

            # 2. Process record, including deduplication and offer updates
            # This function handles FR1, FR3, FR4, FR5, FR6, FR7, FR16, FR17, FR18, FR13 (partially)
            process_result = deduplicate_and_process_offermart_offer(record)

            if process_result['status'] == 'new_offer_created':
                ingested_new_offers_count += 1
                current_app.logger.info(f"Successfully created new offer: {process_result['offer_id']} for customer: {process_result['customer_id']}")
            elif process_result['status'] == 'offer_updated':
                updated_offers_count += 1
                current_app.logger.info(f"Successfully updated existing offer: {process_result['offer_id']}")
            elif process_result['status'] == 'offer_marked_as_duplicate':
                marked_as_duplicate_count += 1
                current_app.logger.info(f"Offer marked as duplicate: {process_result['offer_id']}")
            elif process_result['status'] == 'skipped_due_to_active_journey':
                skipped_due_to_journey_count += 1
                current_app.logger.info(f"Skipped offer due to active loan application journey for customer: {process_result.get('customer_id')}")
            else:
                current_app.logger.warning(f"Unexpected process result status: {process_result['status']} for record {i}")

        except Exception as e:
            db.session.rollback() # Rollback any partial changes for this record
            error_records.append({
                "record_index": i,
                "data": record,
                "errors": str(e),
                "stage": "Processing"
            })
            current_app.logger.error(f"Error processing record {i}: {e}", exc_info=True)

    # 3. Handle offer expiry for journey-started customers (FR13, FR36)
    # This is a separate cleanup/update step, typically run after all new data is ingested.
    current_app.logger.info("Checking for expired offers for journey-started customers...")
    expired_offers_count = update_expired_offers_for_journey_started_customers()
    current_app.logger.info(f"Marked {expired_offers_count} offers as expired due to LAN validity.")

    # 4. Generate Error Report (FR33) - The actual file generation is handled by an export route.
    # Here, we just log the summary and return the errors for potential immediate feedback.
    if error_records:
        current_app.logger.warning(f"Daily ingestion completed with {len(error_records)} errors. "
                                   "A detailed error report can be generated via the /exports/data-errors endpoint.")
    else:
        current_app.logger.info("Daily ingestion completed with no errors.")

    current_app.logger.info(f"Summary: New Offers Ingested: {ingested_new_offers_count}, "
                            f"Offers Updated: {updated_offers_count}, "
                            f"Offers Marked as Duplicate: {marked_as_duplicate_count}, "
                            f"Offers Skipped (Active Journey): {skipped_due_to_journey_count}, "
                            f"Offers Expired (LAN Validity): {expired_offers_count}.")
    current_app.logger.info("Daily Offermart data ingestion task finished.")

    return {
        "status": "completed",
        "new_offers_ingested": ingested_new_offers_count,
        "offers_updated": updated_offers_count,
        "offers_marked_as_duplicate": marked_as_duplicate_count,
        "offers_skipped_active_journey": skipped_due_to_journey_count,
        "offers_expired_lan_validity": expired_offers_count,
        "error_count": len(error_records),
        "errors": error_records # For immediate feedback/debugging
    }

# This block allows the task to be run directly as a Python script,
# ensuring it operates within a Flask application context.
if __name__ == '__main__':
    # Import create_app from your main Flask application file
    # This assumes backend/app.py contains the create_app function.
    from backend.app import create_app

    app = create_app()
    with app.app_context():
        daily_offermart_ingestion_task()