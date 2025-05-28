import os
import csv
import logging
from datetime import datetime

# Import db and models from the main application context
# Assuming db is initialized in backend.src.app and models are in backend.src.models
try:
    from backend.src.app import db, app
    from backend.src.models import Customer, Offer, Event, Campaign
except ImportError as e:
    # This block provides a fallback for isolated testing or if the full Flask app
    # context is not yet available. In a deployed application, the 'try' block
    # should succeed.
    # For the purpose of generating runnable code, we'll assume these imports
    # will be resolvable in the target environment.
    logging.error(f"Failed to import db or models from backend.src: {e}")
    logging.error("This script expects to be run within a Flask application context "
                  "or have access to its models and db instance.")
    # Re-raise the error if critical imports fail, as the script cannot function without them.
    raise


# --- Configuration ---
# Output directory for exported CSV files
# This directory should be accessible by the script and potentially mounted for EDW ingestion.
EXPORT_DIR = os.getenv('EDW_EXPORT_DIR', '/app/exports/edw')

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def ensure_export_directory_exists():
    """Ensures the EDW export directory exists."""
    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)
        logger.info(f"Created EDW export directory: {EXPORT_DIR}")

def export_customers_to_csv(session, export_path):
    """Exports customer data to a CSV file."""
    customers = session.query(Customer).all()
    if not customers:
        logger.info("No customer data found for export.")
        return 0

    headers = [
        "customer_id", "mobile_number", "pan_number", "aadhaar_number",
        "ucid_number", "customer_360_id", "is_dnd", "segment", "attributes",
        "created_at", "updated_at"
    ]
    count = 0
    try:
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for customer in customers:
                writer.writerow([
                    str(customer.customer_id),
                    customer.mobile_number,
                    customer.pan_number,
                    customer.aadhaar_number,
                    customer.ucid_number,
                    customer.customer_360_id,
                    customer.is_dnd,
                    customer.segment,
                    str(customer.attributes), # JSONB might need specific handling
                    customer.created_at.isoformat() if customer.created_at else '',
                    customer.updated_at.isoformat() if customer.updated_at else ''
                ])
                count += 1
        logger.info(f"Exported {count} customer records to {export_path}")
    except IOError as e:
        logger.error(f"Failed to write customer data to {export_path}: {e}")
        count = -1 # Indicate error
    return count

def export_offers_to_csv(session, export_path):
    """Exports offer data to a CSV file."""
    offers = session.query(Offer).all()
    if not offers:
        logger.info("No offer data found for export.")
        return 0

    headers = [
        "offer_id", "customer_id", "source_offer_id", "offer_type",
        "offer_status", "propensity", "loan_application_number", "valid_until",
        "source_system", "channel", "is_duplicate", "original_offer_id",
        "created_at", "updated_at"
    ]
    count = 0
    try:
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for offer in offers:
                writer.writerow([
                    str(offer.offer_id),
                    str(offer.customer_id),
                    offer.source_offer_id,
                    offer.offer_type,
                    offer.offer_status,
                    offer.propensity,
                    offer.loan_application_number,
                    offer.valid_until.isoformat() if offer.valid_until else '',
                    offer.source_system,
                    offer.channel,
                    offer.is_duplicate,
                    str(offer.original_offer_id) if offer.original_offer_id else '',
                    offer.created_at.isoformat() if offer.created_at else '',
                    offer.updated_at.isoformat() if offer.updated_at else ''
                ])
                count += 1
        logger.info(f"Exported {count} offer records to {export_path}")
    except IOError as e:
        logger.error(f"Failed to write offer data to {export_path}: {e}")
        count = -1
    return count

def export_events_to_csv(session, export_path):
    """Exports event data to a CSV file."""
    events = session.query(Event).all()
    if not events:
        logger.info("No event data found for export.")
        return 0

    headers = [
        "event_id", "customer_id", "offer_id", "event_type",
        "event_timestamp", "source_system", "event_details"
    ]
    count = 0
    try:
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for event in events:
                writer.writerow([
                    str(event.event_id),
                    str(event.customer_id) if event.customer_id else '',
                    str(event.offer_id) if event.offer_id else '',
                    event.event_type,
                    event.event_timestamp.isoformat() if event.event_timestamp else '',
                    event.source_system,
                    str(event.event_details) # JSONB might need specific handling
                ])
                count += 1
        logger.info(f"Exported {count} event records to {export_path}")
    except IOError as e:
        logger.error(f"Failed to write event data to {export_path}: {e}")
        count = -1
    return count

def export_campaigns_to_csv(session, export_path):
    """Exports campaign data to a CSV file."""
    campaigns = session.query(Campaign).all()
    if not campaigns:
        logger.info("No campaign data found for export.")
        return 0

    headers = [
        "campaign_id", "campaign_name", "campaign_date",
        "campaign_unique_identifier", "attempted_count", "sent_count",
        "failed_count", "success_rate", "conversion_rate", "created_at",
        "updated_at"
    ]
    count = 0
    try:
        with open(export_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for campaign in campaigns:
                writer.writerow([
                    str(campaign.campaign_id),
                    campaign.campaign_name,
                    campaign.campaign_date.isoformat() if campaign.campaign_date else '',
                    campaign.campaign_unique_identifier,
                    campaign.attempted_count,
                    campaign.sent_count,
                    campaign.failed_count,
                    campaign.success_rate,
                    campaign.conversion_rate,
                    campaign.created_at.isoformat() if campaign.created_at else '',
                    campaign.updated_at.isoformat() if campaign.updated_at else ''
                ])
                count += 1
        logger.info(f"Exported {count} campaign records to {export_path}")
    except IOError as e:
        logger.error(f"Failed to write campaign data to {export_path}: {e}")
        count = -1
    return count

def export_data_to_edw():
    """
    Main function to export CDP data to EDW.
    This function is intended to be run as a daily scheduled task.
    It exports data from Customer, Offer, Event, and Campaign tables
    into separate CSV files in the specified EDW export directory.

    Non-Functional Requirements Addressed:
        - NFR5: Data transfer from CDP to EDW shall occur daily by day end.

    Returns:
        dict: A dictionary indicating the status and counts of exported data.
    """
    logger.info("Starting data export to EDW.")
    ensure_export_directory_exists()

    export_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = {
        "status": "success",
        "customers_exported": 0,
        "offers_exported": 0,
        "events_exported": 0,
        "campaigns_exported": 0,
        "timestamp": export_timestamp
    }

    try:
        # Use db.session for Flask-SQLAlchemy
        # no_autoflush is good for read-only operations to prevent unnecessary flushes
        with db.session.no_autoflush:
            # Export Customers
            customer_export_path = os.path.join(
                EXPORT_DIR, f"cdp_customers_{export_timestamp}.csv"
            )
            results["customers_exported"] = export_customers_to_csv(
                db.session, customer_export_path
            )
            if results["customers_exported"] == -1: # Check for file write errors
                raise IOError("Failed to export customer data.")

            # Export Offers
            offer_export_path = os.path.join(
                EXPORT_DIR, f"cdp_offers_{export_timestamp}.csv"
            )
            results["offers_exported"] = export_offers_to_csv(
                db.session, offer_export_path
            )
            if results["offers_exported"] == -1:
                raise IOError("Failed to export offer data.")

            # Export Events
            event_export_path = os.path.join(
                EXPORT_DIR, f"cdp_events_{export_timestamp}.csv"
            )
            results["events_exported"] = export_events_to_csv(
                db.session, event_export_path
            )
            if results["events_exported"] == -1:
                raise IOError("Failed to export event data.")

            # Export Campaigns
            campaign_export_path = os.path.join(
                EXPORT_DIR, f"cdp_campaigns_{export_timestamp}.csv"
            )
            results["campaigns_exported"] = export_campaigns_to_csv(
                db.session, campaign_export_path
            )
            if results["campaigns_exported"] == -1:
                raise IOError("Failed to export campaign data.")

        logger.info("Data export to EDW completed successfully.")

    except Exception as e:
        # Rollback in case of error, though not strictly necessary for reads
        db.session.rollback()
        logger.error(f"Error during data export to EDW: {e}", exc_info=True)
        results["status"] = "failed"
        results["error"] = str(e)

    return results

if __name__ == '__main__':
    # This block allows the script to be run directly for testing purposes.
    # In a real Flask application, this task might be invoked via a Flask CLI command
    # or a scheduler (e.g., Celery beat, cron job) that sets up the app context.
    # To run this directly, you need to ensure the Flask app context is pushed
    # and db/models are correctly initialized.
    # The 'app' object imported from backend.src.app is used to push the context.
    with app.app_context():
        export_results = export_data_to_edw()
        logger.info(f"EDW Export Final Results: {export_results}")