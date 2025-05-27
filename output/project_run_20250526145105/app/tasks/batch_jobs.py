import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import csv
import io

from sqlalchemy.orm import Session
from sqlalchemy import func, select, update, delete

# Assume these imports exist from other parts of the project
# For a real project, these would be defined in their respective files
from app.core.config import settings
from app.db.database import SessionLocal
from app.models.models import Customer, Offer, OfferHistory, CampaignEvent
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.schemas.offer import OfferCreate, OfferUpdate
from app.services.deduplication import DeduplicationService
from app.services.offer_precedence import OfferPrecedenceService
from app.utils.file_operations import save_csv_file, save_error_file, save_success_file

# Configure logging for batch jobs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Functions / Mocks for external dependencies ---
# In a real application, these would be proper services or utility functions.

def get_db():
    """Dependency to get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Mock data validation function (FR1, NFR3)
def validate_offermart_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Performs basic column-level validation on incoming Offermart data.
    Returns cleaned data or raises ValueError for invalid data.
    """
    required_fields = ["mobile_number", "pan_number", "product_type", "offer_start_date", "offer_end_date"]
    for field in required_fields:
        if not data.get(field):
            raise ValueError(f"Missing required field: {field}")

    # Example: Validate mobile number format
    mobile = str(data.get("mobile_number", "")).strip()
    if not (mobile.isdigit() and len(mobile) in [10, 12]): # Assuming 10 or 12 digits
        raise ValueError(f"Invalid mobile number format: {mobile}")
    data["mobile_number"] = mobile

    # Example: Validate dates
    try:
        if isinstance(data.get("offer_start_date"), str):
            data["offer_start_date"] = datetime.strptime(data["offer_start_date"], "%Y-%m-%d").date()
        if isinstance(data.get("offer_end_date"), str):
            data["offer_end_date"] = datetime.strptime(data["offer_end_date"], "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}")

    # Ensure DND status is boolean
    dnd_status = data.get("dnd_status", False)
    data["dnd_status"] = dnd_status.lower() == 'true' if isinstance(dnd_status, str) else bool(dnd_status)

    return data

# --- Batch Job Implementations ---

def process_offermart_data_ingestion():
    """
    FR9, NFR5: Ingests daily offer and customer data from Offermart staging area into CDP.
    This function simulates reading from a data source (e.g., a CSV file or direct DB connection
    to a staging table) and processing each record.
    """
    logger.info("Starting daily Offermart data ingestion.")
    db: Session = next(get_db())
    deduplication_service = DeduplicationService(db)
    offer_precedence_service = OfferPrecedenceService(db)

    # Simulate reading data from a staging area.
    # In a real scenario, this might involve:
    # 1. Reading from a specific file path (e.g., SFTP drop).
    # 2. Querying a staging table in the same or a linked database.
    # For this example, we'll use a mock list of dictionaries.
    mock_offermart_data = [
        {
            "mobile_number": "9876543210", "pan_number": "ABCDE1234F", "aadhaar_ref_number": "123456789012",
            "product_type": "Preapproved", "offer_details": {"loan_amount": 50000, "interest_rate": 10.5},
            "offer_start_date": "2023-01-01", "offer_end_date": "2023-03-31", "dnd_status": "False",
            "customer_segments": ["C1", "HighValue"], "propensity_flag": "High"
        },
        {
            "mobile_number": "9988776655", "pan_number": "FGHIJ5678K", "aadhaar_ref_number": "234567890123",
            "product_type": "Loyalty", "offer_details": {"loan_amount": 75000, "tenure": 24},
            "offer_start_date": "2023-02-01", "offer_end_date": "2023-04-30", "dnd_status": "True",
            "customer_segments": ["C2"], "propensity_flag": "Medium"
        },
        {
            "mobile_number": "9876543210", "pan_number": "ABCDE1234F", # Same customer, new offer
            "product_type": "Enrich", "offer_details": {"loan_amount": 60000, "interest_rate": 9.8},
            "offer_start_date": "2023-03-01", "offer_end_date": "2023-05-31", "dnd_status": "False",
            "customer_segments": ["C1", "HighValue"], "propensity_flag": "High"
        },
        {
            "mobile_number": "9123456789", "pan_number": "LMNOP9012Q",
            "product_type": "Prospect", "offer_details": {"loan_amount": 25000, "tenure": 12},
            "offer_start_date": "2023-03-15", "offer_end_date": "2023-06-15", "dnd_status": "False",
            "customer_segments": ["C3"], "propensity_flag": "Low"
        }
    ]

    processed_count = 0
    error_count = 0
    error_records = []

    for i, raw_data in enumerate(mock_offermart_data):
        try:
            validated_data = validate_offermart_data(raw_data)

            # FR34: Check DND status early if it's a hard block for processing
            if validated_data.get("dnd_status"):
                logger.info(f"Skipping record {i+1} due to DND status for mobile: {validated_data.get('mobile_number')}")
                continue

            # Deduplication (FR2, FR3, FR4, FR5, FR6)
            customer_data = CustomerCreate(
                mobile_number=validated_data.get("mobile_number"),
                pan_number=validated_data.get("pan_number"),
                aadhaar_ref_number=validated_data.get("aadhaar_ref_number"),
                ucid_number=validated_data.get("ucid_number"),
                previous_loan_app_number=validated_data.get("previous_loan_app_number"),
                customer_attributes=validated_data.get("customer_attributes", {}),
                customer_segments=validated_data.get("customer_segments", []),
                propensity_flag=validated_data.get("propensity_flag"),
                dnd_status=validated_data.get("dnd_status", False)
            )
            customer, is_new_customer = deduplication_service.deduplicate_customer(customer_data)

            # Offer processing
            offer_data = OfferCreate(
                customer_id=customer.customer_id,
                offer_type=validated_data.get("offer_type", "Fresh"), # Default to 'Fresh' if not specified
                offer_status="Active", # Initial status
                product_type=validated_data["product_type"],
                offer_details=validated_data.get("offer_details", {}),
                offer_start_date=validated_data["offer_start_date"],
                offer_end_date=validated_data["offer_end_date"],
                is_journey_started=False
            )

            # Determine prevailing offer and handle new/existing offers (FR15, FR16, FR20, FR21, FR25-FR32)
            # This service will handle updates to existing offers or creation of new ones,
            # and mark old offers as 'Duplicate' or 'Expired' as per rules.
            offer_precedence_service.process_new_offer(customer, offer_data)

            db.commit()
            processed_count += 1
            logger.info(f"Successfully processed record {i+1} for customer {customer.customer_id}")

        except ValueError as ve:
            logger.error(f"Validation error for record {i+1}: {ve}")
            error_records.append({"record": raw_data, "error_desc": str(ve)})
            error_count += 1
            db.rollback()
        except Exception as e:
            logger.error(f"Error processing record {i+1}: {e}", exc_info=True)
            error_records.append({"record": raw_data, "error_desc": str(e)})
            error_count += 1
            db.rollback()

    if error_records:
        error_file_path = save_error_file(error_records, "offermart_ingestion_errors")
        logger.warning(f"Offermart ingestion completed with {error_count} errors. Error file: {error_file_path}")
    else:
        logger.info("Offermart ingestion completed successfully with no errors.")

    logger.info(f"Total records processed: {processed_count + error_count}, Successful: {processed_count}, Failed: {error_count}")
    db.close()


def generate_moengage_file() -> Optional[str]:
    """
    FR54, FR55, NFR12: Generates the Moengage-formatted CSV file.
    Returns the CSV content as a string.
    """
    logger.info("Starting Moengage file generation.")
    db: Session = next(get_db())
    try:
        # Query for active offers and their associated customer details
        # Exclude DND customers (FR34)
        stmt = select(
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_ref_number,
            Customer.customer_segments,
            Customer.propensity_flag,
            Offer.offer_id,
            Offer.product_type,
            Offer.offer_details,
            Offer.offer_start_date,
            Offer.offer_end_date
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.offer_status == "Active",
            Offer.is_journey_started == False, # Only offers where journey has not started
            Customer.dnd_status == False
        )
        results = db.execute(stmt).fetchall()

        if not results:
            logger.info("No active offers found for Moengage file generation.")
            return None

        # Define Moengage specific headers (example, actual headers would come from BRD Q10)
        headers = [
            "customer_mobile", "customer_pan", "customer_aadhaar", "customer_segments",
            "propensity_flag", "offer_id", "product_type", "loan_amount", "interest_rate",
            "offer_start_date", "offer_end_date"
        ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)

        for row in results:
            customer_mobile = row.mobile_number
            customer_pan = row.pan_number
            customer_aadhaar = row.aadhaar_ref_number
            customer_segments = ",".join(row.customer_segments) if row.customer_segments else ""
            propensity_flag = row.propensity_flag
            offer_id = row.offer_id
            product_type = row.product_type
            offer_details = row.offer_details or {} # Ensure it's a dict
            loan_amount = offer_details.get("loan_amount")
            interest_rate = offer_details.get("interest_rate")
            offer_start_date = row.offer_start_date.strftime("%Y-%m-%d") if row.offer_start_date else ""
            offer_end_date = row.offer_end_date.strftime("%Y-%m-%d") if row.offer_end_date else ""

            writer.writerow([
                customer_mobile, customer_pan, customer_aadhaar, customer_segments,
                propensity_flag, offer_id, product_type, loan_amount, interest_rate,
                offer_start_date, offer_end_date
            ])

        csv_content = output.getvalue()
        file_path = save_csv_file(csv_content, "moengage_campaign_file")
        logger.info(f"Moengage file generated successfully at: {file_path}")
        return csv_content

    except Exception as e:
        logger.error(f"Error generating Moengage file: {e}", exc_info=True)
        return None
    finally:
        db.close()


def update_offer_expiries():
    """
    FR51, FR53: Marks offers as expired based on business logic.
    - Offers with offer_end_date in the past and no journey started (FR51).
    - Offers where LAN validity is over (FR53 - placeholder logic as per BRD Q9).
    """
    logger.info("Starting offer expiry update job.")
    db: Session = next(get_db())
    current_date = datetime.now().date()
    updated_count = 0

    try:
        # Logic for FR51: Offers expired by offer_end_date if journey not started
        offers_to_expire_by_date = db.execute(
            select(Offer).where(
                Offer.offer_end_date < current_date,
                Offer.is_journey_started == False,
                Offer.offer_status == "Active"
            )
        ).scalars().all()

        for offer in offers_to_expire_by_date:
            old_status = offer.offer_status
            offer.offer_status = "Expired"
            offer.updated_at = datetime.now()
            db.add(OfferHistory(
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Expired",
                change_reason="Offer expired by end date, no journey started",
                snapshot_offer_details=offer.offer_details
            ))
            updated_count += 1
            logger.info(f"Offer {offer.offer_id} expired by end date.")

        # Logic for FR53: Offers expired if LAN validity is over
        # This requires clarification (BRD Q9). For now, a placeholder:
        # Assume LAN validity is 30 days from journey start if not explicitly defined.
        offers_to_expire_by_lan = db.execute(
            select(Offer).where(
                Offer.is_journey_started == True,
                Offer.loan_application_id.isnot(None),
                Offer.offer_status == "Active",
                # Placeholder: if journey started more than 30 days ago and not converted
                # In a real system, this would check against LOS status or a specific LAN expiry date field
                Offer.updated_at < datetime.now() - timedelta(days=30) # Assuming updated_at reflects journey start
            )
        ).scalars().all()

        for offer in offers_to_expire_by_lan:
            # Further check if the loan application is actually rejected/expired in LOS
            # For now, we assume if it's old and journey started, it might be expired.
            # This needs integration with LOS status.
            old_status = offer.offer_status
            offer.offer_status = "Expired"
            offer.updated_at = datetime.now()
            db.add(OfferHistory(
                offer_id=offer.offer_id,
                customer_id=offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Expired",
                change_reason="Loan application validity expired (placeholder logic)",
                snapshot_offer_details=offer.offer_details
            ))
            updated_count += 1
            logger.info(f"Offer {offer.offer_id} expired due to LAN validity (placeholder).")

        db.commit()
        logger.info(f"Offer expiry update completed. Total {updated_count} offers marked as expired.")

    except Exception as e:
        logger.error(f"Error during offer expiry update: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def perform_data_retention_cleanup():
    """
    FR37, NFR10: Deletes old data based on retention policies.
    - Offer history older than 6 months (FR23, NFR9).
    - CDP data (customers, offers, campaign events) older than 3 months (FR37, NFR10).
      (Careful with customer/offer deletion: only if no active offers/journeys)
    """
    logger.info("Starting data retention cleanup job.")
    db: Session = next(get_db())
    try:
        # 1. Clean up Offer History (6 months retention)
        six_months_ago = datetime.now() - timedelta(days=6 * 30) # Approx 6 months
        deleted_history_count = db.execute(
            delete(OfferHistory).where(OfferHistory.change_timestamp < six_months_ago)
        ).rowcount
        logger.info(f"Deleted {deleted_history_count} offer history records older than 6 months.")

        # 2. Clean up Campaign Events (3 months retention)
        three_months_ago = datetime.now() - timedelta(days=3 * 30) # Approx 3 months
        deleted_campaign_events_count = db.execute(
            delete(CampaignEvent).where(CampaignEvent.event_timestamp < three_months_ago)
        ).rowcount
        logger.info(f"Deleted {deleted_campaign_events_count} campaign event records older than 3 months.")

        # 3. Clean up Customers and Offers (3 months retention)
        # This is more complex. We should only delete customers/offers if they are truly inactive
        # and have no active offers or ongoing journeys.
        # For simplicity in this example, we'll delete offers that are 'Expired' or 'Duplicate'
        # and older than 3 months, and then customers who have no remaining offers.

        # Delete expired/duplicate offers older than 3 months
        deleted_offers_count = db.execute(
            delete(Offer).where(
                (Offer.offer_status.in_(["Expired", "Duplicate"])),
                Offer.updated_at < three_months_ago
            )
        ).rowcount
        logger.info(f"Deleted {deleted_offers_count} expired/duplicate offers older than 3 months.")

        # Delete customers who have no associated offers or campaign events
        # This requires careful consideration of foreign key constraints and business rules.
        # A safer approach might be soft deletes or archiving.
        # For this example, we'll identify customers with no active offers and no recent activity.
        # This is a simplified logic and might need adjustment based on specific business rules.
        customers_to_delete_stmt = select(Customer.customer_id).outerjoin(
            Offer, Customer.customer_id == Offer.customer_id
        ).group_by(Customer.customer_id).having(
            func.count(Offer.offer_id) == 0, # No offers at all
            Customer.updated_at < three_months_ago # No recent updates
        )
        customer_ids_to_delete = [row[0] for row in db.execute(customers_to_delete_stmt).fetchall()]

        if customer_ids_to_delete:
            deleted_customers_count = db.execute(
                delete(Customer).where(Customer.customer_id.in_(customer_ids_to_delete))
            ).rowcount
            logger.info(f"Deleted {deleted_customers_count} customers with no associated offers and older than 3 months.")
        else:
            logger.info("No customers found for deletion based on current criteria.")

        db.commit()
        logger.info("Data retention cleanup completed.")

    except Exception as e:
        logger.error(f"Error during data retention cleanup: {e}", exc_info=True)
        db.rollback()
    finally:
        db.close()


def process_admin_upload_file(file_path: str, job_id: uuid.UUID):
    """
    FR43, FR44, FR45, FR46: Processes an uploaded customer details file from the Admin Portal.
    This function would typically be called by a background task queue (e.g., Celery)
    after a file is uploaded via the API endpoint.
    """
    logger.info(f"Starting processing for admin upload job_id: {job_id} from file: {file_path}")
    db: Session = next(get_db())
    deduplication_service = DeduplicationService(db)
    offer_precedence_service = OfferPrecedenceService(db)

    success_records = []
    error_records = []
    processed_count = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                try:
                    # Basic validation and type conversion for CSV row
                    validated_data = {k: v.strip() for k, v in row.items() if v is not None}
                    validated_data = validate_offermart_data(validated_data) # Re-use validation logic

                    # FR34: Check DND status
                    if validated_data.get("dnd_status"):
                        error_records.append({"record": row, "error_desc": "Customer is DND"})
                        continue

                    customer_data = CustomerCreate(
                        mobile_number=validated_data.get("mobile_number"),
                        pan_number=validated_data.get("pan_number"),
                        aadhaar_ref_number=validated_data.get("aadhaar_ref_number"),
                        ucid_number=validated_data.get("ucid_number"),
                        previous_loan_app_number=validated_data.get("previous_loan_app_number"),
                        customer_attributes=validated_data.get("customer_attributes", {}),
                        customer_segments=validated_data.get("customer_segments", []),
                        propensity_flag=validated_data.get("propensity_flag"),
                        dnd_status=validated_data.get("dnd_status", False)
                    )
                    customer, is_new_customer = deduplication_service.deduplicate_customer(customer_data)

                    offer_data = OfferCreate(
                        customer_id=customer.customer_id,
                        offer_type=validated_data.get("offer_type", "Fresh"),
                        offer_status="Active",
                        product_type=validated_data["product_type"],
                        offer_details=validated_data.get("offer_details", {}),
                        offer_start_date=validated_data["offer_start_date"],
                        offer_end_date=validated_data["offer_end_date"],
                        is_journey_started=False
                    )

                    # Determine prevailing offer and handle new/existing offers
                    offer_precedence_service.process_new_offer(customer, offer_data)

                    db.commit()
                    success_records.append({"record": row, "customer_id": str(customer.customer_id)})
                    processed_count += 1
                    logger.info(f"Admin upload: Successfully processed row {i+1} for customer {customer.customer_id}")

                except ValueError as ve:
                    logger.error(f"Admin upload: Validation error for row {i+1}: {ve}")
                    error_records.append({"record": row, "error_desc": str(ve)})
                    db.rollback()
                except Exception as e:
                    logger.error(f"Admin upload: Error processing row {i+1}: {e}", exc_info=True)
                    error_records.append({"record": row, "error_desc": str(e)})
                    db.rollback()

        # Generate success and error files (FR45, FR46)
        if success_records:
            save_success_file(success_records, f"admin_upload_success_{job_id}")
        if error_records:
            save_error_file(error_records, f"admin_upload_error_{job_id}")

        logger.info(f"Admin upload job {job_id} completed. Processed: {processed_count}, Errors: {len(error_records)}")

    except FileNotFoundError:
        logger.error(f"Admin upload: File not found at {file_path} for job {job_id}")
    except Exception as e:
        logger.error(f"Admin upload: Critical error during file processing for job {job_id}: {e}", exc_info=True)
    finally:
        db.close()


def push_data_to_offermart():
    """
    FR10, NFR6: Pushes daily reverse feed (offer updates) from CDP to Offermart.
    This function simulates sending data to an external system.
    """
    logger.info("Starting daily reverse feed to Offermart.")
    db: Session = next(get_db())
    try:
        # Query for offers that have been updated since the last push
        # (e.g., status changes, new offers created in CDP, etc.)
        # For simplicity, let's get all active offers and their customer details.
        # In a real system, you'd track a 'last_pushed_to_offermart' timestamp.
        stmt = select(
            Customer.mobile_number,
            Customer.pan_number,
            Offer.offer_id,
            Offer.product_type,
            Offer.offer_status,
            Offer.offer_details,
            Offer.updated_at
        ).join(Offer, Customer.customer_id == Offer.customer_id).where(
            Offer.updated_at >= datetime.now() - timedelta(days=1) # Offers updated in last 24 hours
        )
        updated_offers = db.execute(stmt).fetchall()

        if not updated_offers:
            logger.info("No new or updated offers to push to Offermart.")
            return

        # Simulate sending data to Offermart (e.g., via API, SFTP, or direct DB insert)
        # This would involve formatting data as required by Offermart.
        offermart_feed_data = []
        for offer_row in updated_offers:
            offermart_feed_data.append({
                "customer_mobile": offer_row.mobile_number,
                "customer_pan": offer_row.pan_number,
                "offer_id": str(offer_row.offer_id),
                "product_type": offer_row.product_type,
                "offer_status": offer_row.offer_status,
                "offer_details": offer_row.offer_details,
                "last_updated_cdp": offer_row.updated_at.isoformat()
            })

        # Example: Print to console or save to a mock file
        # In production, this would be an API call or SFTP transfer.
        mock_output_file = f"{settings.DATA_EXPORT_DIR}/offermart_reverse_feed_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        with open(mock_output_file, 'w') as f:
            import json
            json.dump(offermart_feed_data, f, indent=2)
        logger.info(f"Successfully generated {len(offermart_feed_data)} records for Offermart reverse feed. Saved to {mock_output_file}")

    except Exception as e:
        logger.error(f"Error pushing data to Offermart: {e}", exc_info=True)
    finally:
        db.close()


def push_data_to_edw():
    """
    FR35, FR36, NFR11: Passes all relevant data from LTFS Offer CDP to EDW daily.
    This function simulates sending data to an Enterprise Data Warehouse.
    """
    logger.info("Starting daily data push to EDW.")
    db: Session = next(get_db())
    try:
        # Query all relevant data: customers, offers, campaign events
        # This might involve complex joins or separate queries for different EDW tables.
        # For simplicity, we'll fetch a combined view.

        # Fetch Customers
        customers_data = db.execute(select(Customer)).scalars().all()
        # Fetch Offers
        offers_data = db.execute(select(Offer)).scalars().all()
        # Fetch Campaign Events
        campaign_events_data = db.execute(select(CampaignEvent)).scalars().all()

        if not (customers_data or offers_data or campaign_events_data):
            logger.info("No data found to push to EDW.")
            return

        # Format data for EDW (BRD Q5: Raj to share data template)
        # This is a placeholder for the actual EDW schema.
        edw_formatted_data = {
            "customers": [c.to_dict() for c in customers_data], # Assuming a .to_dict() method on models
            "offers": [o.to_dict() for o in offers_data],
            "campaign_events": [ce.to_dict() for ce in campaign_events_data]
        }

        # Simulate sending data to EDW (e.g., via SFTP, Kafka, or direct DB link)
        mock_output_file = f"{settings.DATA_EXPORT_DIR}/edw_full_dump_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
        with open(mock_output_file, 'w') as f:
            import json
            json.dump(edw_formatted_data, f, indent=2, default=str) # default=str for UUID, datetime objects
        logger.info(f"Successfully generated data for EDW. Saved to {mock_output_file}")

    except Exception as e:
        logger.error(f"Error pushing data to EDW: {e}", exc_info=True)
    finally:
        db.close()

# Example of how these tasks might be called (e.g., by a scheduler)
if __name__ == "__main__":
    # This block is for testing purposes only.
    # In a real application, these functions would be invoked by a scheduler like Celery Beat, APScheduler, or cron.

    logger.info("--- Running all batch jobs for testing ---")

    # Ensure settings are loaded for local testing
    # In a real FastAPI app, settings would be loaded via Pydantic BaseSettings
    class MockSettings:
        DATABASE_URL: str = "postgresql://user:password@host:port/dbname" # Replace with actual test DB
        MOENGAGE_FILE_PATH: str = "./data_exports/moengage_files"
        UPLOAD_SUCCESS_DIR: str = "./data_exports/admin_uploads/success"
        UPLOAD_ERROR_DIR: str = "./data_exports/admin_uploads/errors"
        DATA_EXPORT_DIR: str = "./data_exports"

    settings = MockSettings()

    # Create necessary directories for mock file operations
    import os
    os.makedirs(settings.MOENGAGE_FILE_PATH, exist_ok=True)
    os.makedirs(settings.UPLOAD_SUCCESS_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_ERROR_DIR, exist_ok=True)
    os.makedirs(settings.DATA_EXPORT_DIR, exist_ok=True)

    # Mock database setup for testing
    # In a real scenario, you'd have a test database or a proper ORM setup.
    # For this example, we'll just log that we're "connecting"
    logger.info(f"Attempting to connect to mock DB: {settings.DATABASE_URL}")
    # You would typically run migrations here if this was a standalone script
    # from app.db.base import Base
    # from app.db.database import engine
    # Base.metadata.create_all(bind=engine)

    # Run the batch jobs
    # process_offermart_data_ingestion()
    # update_offer_expiries()
    # generate_moengage_file()
    # push_data_to_offermart()
    # push_data_to_edw()
    # perform_data_retention_cleanup()

    # Example of calling admin upload processing (requires a mock file)
    # mock_upload_file_path = "./data_exports/mock_admin_upload.csv"
    # with open(mock_upload_file_path, 'w', newline='') as f:
    #     writer = csv.writer(f)
    #     writer.writerow(["mobile_number", "pan_number", "product_type", "offer_start_date", "offer_end_date", "dnd_status"])
    #     writer.writerow(["9999900001", "TESTP1234A", "Prospect", "2023-04-01", "2023-06-30", "False"])
    #     writer.writerow(["9999900002", "TESTP1234B", "Loyalty", "2023-04-01", "2023-06-30", "True"]) # DND
    #     writer.writerow(["9999900003", "TESTP1234C", "Top-up", "2023-04-01", "2023-06-30", "False"])
    #
    # process_admin_upload_file(mock_upload_file_path, uuid.uuid4())

    logger.info("--- All batch jobs testing completed ---")