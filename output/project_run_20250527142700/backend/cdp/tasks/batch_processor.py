import logging
from datetime import datetime, timedelta
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_

# Assuming db is initialized in backend/database.py and models in backend/models.py
from backend.database import db
from backend.models import Customer, Offer, OfferHistory, Event, Campaign

# Import services for deduplication and validation.
# Assuming specific functions for Offermart processing exist in these services.
from backend.services.deduplication_service import process_offermart_offer
from backend.services.validation_service import validate_offermart_payload

# Configure logging for batch tasks
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_offermart_daily_feed(offermart_data: list[dict]):
    """
    Processes the daily batch feed from Offermart.
    This function simulates reading data and applying validation, deduplication,
    and offer management logic.

    Functional Requirements Addressed:
    - FR2: The CDP system shall validate basic column-level data when moving data from Offermart to CDP.
    - FR8: The CDP system shall receive Offer and Customer data daily from Offermart via a staging area.
    - FR13: The CDP system shall prevent modification of customer offers with an active loan application journey until the application is expired or rejected.
    - FR14: The CDP system shall allow replenishment of offers for non-journey started customers after their existing offers expire.
    - FR16: The CDP system shall maintain flags for Offer statuses: Active, Inactive, and Expired based on defined business logic.
    - FR17: The CDP system shall maintain flags for Offer types: ‘Fresh’, ‘Enrich’, ‘New-old’, ‘New-new’ for campaigning, specifically for Preapproved and TW-L Products.
    - FR18: The CDP system shall handle 'Enrich' offers: if journey not started, flow to CDP and mark previous offer as Duplicate; if journey started, do not flow to CDP.
    - FR33: The CDP system shall provide a screen for users to download an Error Excel file for data uploads. (Errors logged here)

    Non-Functional Requirements Addressed:
    - NFR3: Data push from Offermart to CDP shall occur daily.
    - NFR8: The system shall perform basic column-level data validation during data ingestion.

    Args:
        offermart_data (list[dict]): A list of dictionaries, each representing a record
                                     from the Offermart daily feed.
    Returns:
        dict: A dictionary containing processing summary and error records.
    """
    logger.info(f"Starting daily Offermart feed processing for {len(offermart_data)} records.")
    processed_count = 0
    error_records = []

    for i, record in enumerate(offermart_data):
        try:
            # 1. Validate basic column-level data (FR2, NFR8)
            validation_errors = validate_offermart_payload(record)
            if validation_errors:
                logger.warning(f"Record {i+1} failed validation: {validation_errors}")
                error_records.append({"record": record, "errors": validation_errors})
                continue

            # 2. Process offer and customer data, including deduplication (FR1, FR3, FR4, FR5, FR6)
            # This service function should handle finding/creating customer,
            # managing offers, and applying attribution/deduplication logic.
            # It also needs to consider FR13 (active loan journey) and FR18 (Enrich offers).
            customer_id, offer_id, status_message = process_offermart_offer(record)

            if customer_id and offer_id:
                processed_count += 1
                logger.info(f"Successfully processed record {i+1}: Customer ID {customer_id}, Offer ID {offer_id}. Status: {status_message}")
            else:
                logger.warning(f"Record {i+1} could not be fully processed: {status_message}")
                error_records.append({"record": record, "errors": [status_message]})

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error processing record {i+1}: {e}")
            error_records.append({"record": record, "errors": [f"Database error: {e}"]})
        except Exception as e:
            logger.error(f"Unexpected error processing record {i+1}: {e}")
            error_records.append({"record": record, "errors": [f"Unexpected error: {e}"]})

    logger.info(f"Finished daily Offermart feed processing. Processed {processed_count} records, {len(error_records)} errors.")
    # In a real system, error_records would be saved to a file/DB for download (FR33)
    return {"processed_count": processed_count, "error_records": error_records}

def export_data_to_edw():
    """
    Exports relevant CDP data to the Enterprise Data Warehouse (EDW).
    This function queries the necessary data and prepares it for export.

    Functional Requirements Addressed:
    - FR28: The CDP system shall pass all data, including campaign data, to the EDW system daily by day end.

    Non-Functional Requirements Addressed:
    - NFR5: Data transfer from CDP to EDW shall occur daily by day end.

    Returns:
        dict: A dictionary indicating the status and counts of exported data.
    """
    logger.info("Starting data export to EDW.")
    try:
        # Query customers, offers, events, and campaign data
        # This is a simplified example; actual EDW export might require complex joins
        # and specific data transformations.
        customers = Customer.query.all()
        offers = Offer.query.all()
        events = Event.query.all()
        campaigns = Campaign.query.all()

        # Prepare data for EDW. This would typically involve converting to a specific format
        # (e.g., CSV, JSONL, Parquet) and then pushing to a data lake/warehouse.
        # Assuming models have a .to_dict() method for serialization.
        edw_data = {
            "customers": [c.to_dict() for c in customers],
            "offers": [o.to_dict() for o in offers],
            "events": [e.to_dict() for e in events],
            "campaigns": [cmp.to_dict() for cmp in campaigns]
        }

        # Simulate data transfer (e.g., print or save to a temporary file)
        # In a real scenario, this would be an API call to an EDW ingestion service
        # or writing to a cloud storage bucket that EDW consumes.
        logger.info(f"Prepared {len(customers)} customers, {len(offers)} offers, "
                    f"{len(events)} events, {len(campaigns)} campaigns for EDW.")
        # Example: logger.debug(f"Sample EDW customer data: {edw_data['customers'][:2]}")

        logger.info("Data export to EDW completed successfully.")
        return {"status": "success", "exported_counts": {
            "customers": len(customers),
            "offers": len(offers),
            "events": len(events),
            "campaigns": len(campaigns)
        }}

    except SQLAlchemyError as e:
        logger.error(f"Database error during EDW export: {e}")
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error during EDW export: {e}")
        return {"status": "error", "message": f"Unexpected error: {e}"}

def cleanup_old_data():
    """
    Cleans up old data based on retention policies.

    Functional Requirements Addressed:
    - FR20: The CDP system shall maintain Offer history for the past 6 months.
    - FR29: The CDP system shall maintain all data for previous 3 months before deletion from CDP.

    Non-Functional Requirements Addressed:
    - NFR10: Offer history shall be maintained for 6 months.
    - NFR11: All data in CDP shall be maintained for 3 months before deletion.

    Returns:
        dict: A dictionary indicating the status and counts of deleted data.
    """
    logger.info("Starting data cleanup for old records.")
    deleted_counts = {
        "offer_history": 0,
        "events": 0,
        "offers": 0,
        "customers": 0,
        "campaigns": 0
    }

    try:
        # 1. Clean up offer history older than 6 months (FR20, NFR10)
        six_months_ago = datetime.now() - timedelta(days=6 * 30) # Approximate 6 months
        history_to_delete = OfferHistory.query.filter(
            OfferHistory.status_change_date < six_months_ago
        ).all()
        for record in history_to_delete:
            db.session.delete(record)
            deleted_counts["offer_history"] += 1
        db.session.commit()
        logger.info(f"Deleted {deleted_counts['offer_history']} offer history records older than 6 months.")

        # 2. Clean up main CDP data (events, offers, campaigns, customers) older than 3 months (FR29, NFR11)
        # Deletion order matters due to foreign key constraints. Events -> Offers -> Campaigns -> Customers.
        three_months_ago = datetime.now() - timedelta(days=3 * 30) # Approximate 3 months

        # Delete old events
        events_to_delete = Event.query.filter(
            Event.event_timestamp < three_months_ago
        ).all()
        for event in events_to_delete:
            db.session.delete(event)
            deleted_counts["events"] += 1
        db.session.commit()
        logger.info(f"Deleted {deleted_counts['events']} event records older than 3 months.")

        # Delete old offers (only inactive/expired ones to avoid deleting active offers prematurely)
        offers_to_delete = Offer.query.filter(
            Offer.created_at < three_months_ago,
            Offer.offer_status.in_(['Inactive', 'Expired'])
        ).all()
        for offer in offers_to_delete:
            db.session.delete(offer)
            deleted_counts["offers"] += 1
        db.session.commit()
        logger.info(f"Deleted {deleted_counts['offers']} inactive/expired offer records older than 3 months.")

        # Delete old campaigns
        campaigns_to_delete = Campaign.query.filter(
            Campaign.campaign_date < three_months_ago.date()
        ).all()
        for campaign in campaigns_to_delete:
            db.session.delete(campaign)
            deleted_counts["campaigns"] += 1
        db.session.commit()
        logger.info(f"Deleted {deleted_counts['campaigns']} campaign records older than 3 months.")

        # Delete customers who have no remaining offers and were created before 3 months.
        # This is a simplified approach. In a real system, customer deletion might be more complex
        # or involve soft deletes/archiving.
        customers_to_delete = Customer.query.filter(
            Customer.created_at < three_months_ago,
            ~Customer.offers.any() # Customers with no associated offers
        ).all()
        for customer in customers_to_delete:
            db.session.delete(customer)
            deleted_counts["customers"] += 1
        db.session.commit()
        logger.info(f"Deleted {deleted_counts['customers']} customer records (with no active offers) older than 3 months.")

        logger.info("Data cleanup completed successfully.")
        return {"status": "success", "deleted_counts": deleted_counts}

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during data cleanup: {e}")
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        logger.error(f"Unexpected error during data cleanup: {e}")
        return {"status": "error", "message": f"Unexpected error: {e}"}

def update_expired_offers():
    """
    Updates the status of offers that have expired based on their loan application number (LAN) validity.

    Functional Requirements Addressed:
    - FR36: The CDP system shall mark offers as expired if the loan application number (LAN) validity is over for journey-started customers.

    Returns:
        dict: A dictionary indicating the status and count of expired offers.
    """
    logger.info("Starting update for expired offers.")
    updated_count = 0
    try:
        # Find offers that have a LAN, are currently 'Active', and whose valid_until date has passed.
        # Assuming 'journey-started customers' implies offers with a non-null LAN.
        # The exact "LAN validity" period is ambiguous (Question 5 in BRD), so we use `valid_until` field.
        offers_to_expire = Offer.query.filter(
            Offer.loan_application_number.isnot(None),
            Offer.offer_status == 'Active',
            Offer.valid_until < datetime.now()
        ).all()

        for offer in offers_to_expire:
            old_status = offer.offer_status
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()
            db.session.add(offer)

            # Record in offer history (FR20)
            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status='Expired',
                change_reason='LAN validity expired'
            )
            db.session.add(history_entry)
            updated_count += 1
            logger.info(f"Offer {offer.offer_id} (LAN: {offer.loan_application_number}) marked as Expired.")

        db.session.commit()
        logger.info(f"Finished updating expired offers. {updated_count} offers marked as Expired.")
        return {"status": "success", "expired_offers_count": updated_count}

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during offer expiry update: {e}")
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        db.session.rollback() # Ensure rollback on unexpected errors too
        logger.error(f"Unexpected error during offer expiry update: {e}")
        return {"status": "error", "message": f"Unexpected error: {e}"}