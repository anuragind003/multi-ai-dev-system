import logging
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from backend.src.models import db, Customer, Offer, Event, CampaignMetric, IngestionLog
# Assuming these services exist as per system design and common Flask project structure
from backend.src.services.data_processing_service import process_offermart_data, apply_deduplication_logic 

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_with_app_context(func):
    """
    Decorator to ensure the function runs within a Flask application context.
    This is crucial for accessing `current_app` and `db` session.
    """
    def wrapper(*args, **kwargs):
        if not current_app:
            # If not already in an app context, create one.
            # This assumes `create_app` is available in `backend.src.app`.
            # In a production setup, a dedicated scheduler (e.g., Celery Beat, APScheduler)
            # would manage the app context or be initialized with the app.
            from backend.src.app import create_app 
            app = create_app()
            with app.app_context():
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper

@run_with_app_context
def daily_offermart_ingestion():
    """
    Scheduled job to ingest daily customer and offer data from Offermart.
    Handles:
    - FR9: Receive Offer and Customer data from Offermart daily via a staging area.
    - FR1: Perform basic column-level validation.
    - FR3, FR4, FR5, FR6: Trigger deduplication logic.
    """
    logger.info("Starting daily Offermart data ingestion.")
    try:
        # Simulate fetching data from a staging area or Offermart API.
        # In a real scenario, this would involve reading from a file path,
        # an S3 bucket, or making an HTTP request to Offermart's API.
        # The actual data fetching mechanism (e.g., reading a CSV, calling an API)
        # would be implemented within `data_processing_service.process_offermart_data`.
        
        # Example: A list of dictionaries representing rows from Offermart.
        # This data would typically come from a file or external system.
        mock_offermart_data = [
            {"mobile_number": "9876543210", "pan_number": "ABCDE1234F", "offer_type": "Fresh", "propensity": "High", "start_date": "2023-01-01", "end_date": "2023-12-31", "source_system": "Offermart"},
            {"mobile_number": "9988776655", "pan_number": "FGHIJ5678K", "offer_type": "Enrich", "propensity": "Medium", "start_date": "2023-02-01", "end_date": "2023-11-30", "source_system": "Offermart"},
            # Add more mock data as needed for testing
        ]
        
        # Process the data (validation, insertion/update) using the service layer.
        # This function is expected to handle FR1 (validation) and initial data loading (FR9).
        success_count, error_count = process_offermart_data(mock_offermart_data)
        
        logger.info(f"Daily Offermart ingestion completed. Successfully processed: {success_count}, Errors: {error_count}.")
        
        # After ingestion, apply deduplication logic across the entire dataset or newly ingested data.
        # This is a critical step as per FR3, FR4, FR5, FR6.
        # The `apply_deduplication_logic` function would identify and merge/flag duplicates.
        deduplicated_count = apply_deduplication_logic()
        logger.info(f"Deduplication logic applied. {deduplicated_count} potential duplicates processed/merged.")

    except Exception as e:
        logger.error(f"Error during daily Offermart ingestion: {e}", exc_info=True)
        db.session.rollback() # Ensure rollback on error

@run_with_app_context
def daily_reverse_feed_to_offermart():
    """
    Scheduled job to push daily reverse feed (offer updates) to Offermart.
    Handles:
    - FR10: Push daily reverse feed to Offermart, including Offer data updates.
    """
    logger.info("Starting daily reverse feed to Offermart.")
    try:
        # Query offers that have been updated since the last feed or are new.
        # In a real system, there would be a 'last_fed_to_offermart_at' timestamp or similar
        # to track what has already been sent. For simplicity, we'll fetch recently updated offers.
        
        # Fetch offers updated in the last 24 hours (or since the last run)
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        updated_offers = Offer.query.filter(Offer.updated_at >= twenty_four_hours_ago).all()
        
        if updated_offers:
            # Simulate pushing data to Offermart (e.g., via an API call or file generation).
            # This would involve formatting the data as required by Offermart.
            # The actual push mechanism would be in a dedicated service or utility.
            for offer in updated_offers:
                logger.debug(f"Simulating push of offer {offer.offer_id} to Offermart.")
                # Example: off_api_client.update_offer(offer.to_dict())
            logger.info(f"Successfully prepared and simulated push of {len(updated_offers)} updated offers to Offermart.")
        else:
            logger.info("No updated offers found for reverse feed to Offermart.")

    except SQLAlchemyError as e:
        logger.error(f"Database error during reverse feed to Offermart: {e}", exc_info=True)
        db.session.rollback()
    except Exception as e:
        logger.error(f"Error during daily reverse feed to Offermart: {e}", exc_info=True)

@run_with_app_context
def daily_data_export_to_edw():
    """
    Scheduled job to export all relevant CDP data to EDW.
    Handles:
    - FR27: Pass all data, including campaign data, from LTFS Offer CDP to EDW daily by day end.
    """
    logger.info("Starting daily data export to EDW.")
    try:
        # Fetch all relevant data for EDW export.
        # This might involve joining multiple tables or exporting them separately.
        # For simplicity, we'll just count records and log.
        
        customer_count = Customer.query.count()
        offer_count = Offer.query.count()
        event_count = Event.query.count()
        campaign_metric_count = CampaignMetric.query.count()

        # In a real scenario, this would involve:
        # 1. Fetching data in chunks to avoid memory issues.
        # 2. Formatting data (e.g., CSV, Parquet, JSONL).
        # 3. Pushing to an EDW staging area (e.g., S3, SFTP, direct DB insert).
        # This logic would typically reside in a dedicated export service.
        
        logger.info(f"Simulating export of {customer_count} customers, {offer_count} offers, "
                    f"{event_count} events, and {campaign_metric_count} campaign metrics to EDW.")
        logger.info("Daily data export to EDW completed.")

    except SQLAlchemyError as e:
        logger.error(f"Database error during data export to EDW: {e}", exc_info=True)
        db.session.rollback()
    except Exception as e:
        logger.error(f"Error during daily data export to EDW: {e}", exc_info=True)

@run_with_app_context
def update_offer_statuses():
    """
    Scheduled job to update offer statuses based on expiry logic.
    Handles:
    - FR41: Mark offers as expired based on offer end dates for non-journey started customers.
    - FR42: Check for and replenish new offers for non-journey started customers whose previous offers have expired. (Not fully implemented, requires complex business logic)
    - FR43: Mark offers as expired for journey started customers whose LAN (Loan Application Number) validity is over. (Requires more specific data model/logic)
    """
    logger.info("Starting offer status update job.")
    try:
        current_date = datetime.utcnow().date()
        
        # FR41: Mark offers as expired based on offer end dates for non-journey started customers.
        # A simplified assumption for 'non-journey started' is that the customer does not have a loan_application_number.
        # A more robust check would involve looking at specific event types or a dedicated journey status flag.
        
        expired_offers_count = 0
        offers_to_expire = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.end_date < current_date
        ).all()

        for offer in offers_to_expire:
            customer = Customer.query.get(offer.customer_id)
            
            # Check if customer has started a journey (simplified: no LAN)
            if customer and not customer.loan_application_number: 
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.utcnow()
                expired_offers_count += 1
                logger.debug(f"Marked offer {offer.offer_id} (customer {offer.customer_id}) as Expired (end date passed, no journey).")
            # FR42: "replenish new offers for non-journey started customers whose previous offers have expired."
            # This is a complex business logic that would involve generating new offers based on customer segments,
            # eligibility, etc. For MVP, this is out of scope for a simple status update job.
            # It would likely be a separate service call, e.g., `offer_service.generate_new_offers_for_expired_customers()`.
            # For now, we just mark as expired.

        # FR43: Mark offers as expired for journey started customers whose LAN (Loan Application Number) validity is over.
        # This requires knowing the LAN validity period and a field to track LAN creation/update time.
        # The current schema has `loan_application_number` on `Customer`, but no timestamp for its validity.
        # This part is left as a placeholder requiring further schema/logic definition.
        # Example placeholder logic (requires `loan_application_number_created_at` on Customer or Offer):
        # thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        # journey_started_offers_to_expire = Offer.query.join(Customer).filter(
        #     Offer.offer_status == 'Active',
        #     Customer.loan_application_number.isnot(None),
        #     Customer.loan_application_number_created_at < thirty_days_ago 
        # ).all()
        # for offer in journey_started_offers_to_expire:
        #     offer.offer_status = 'Expired'
        #     offer.updated_at = datetime.utcnow()
        #     expired_offers_count += 1 # Count these too
        #     logger.debug(f"Marked offer {offer.offer_id} (customer {offer.customer_id}) as Expired (LAN validity over).")

        db.session.commit()
        logger.info(f"Offer status update completed. {expired_offers_count} offers marked as 'Expired'.")

    except SQLAlchemyError as e:
        logger.error(f"Database error during offer status update: {e}", exc_info=True)
        db.session.rollback()
    except Exception as e:
        logger.error(f"Error during offer status update: {e}", exc_info=True)
        db.session.rollback()

@run_with_app_context
def enforce_data_retention_policy():
    """
    Scheduled job to enforce data retention policies.
    Handles:
    - FR19: Maintain Offer history for the past 6 months.
    - FR28: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
    - NFR8: Retain offer history for 6 months for reference purposes.
    - NFR9: Retain all data in CDP for 3 months before deletion.
    """
    logger.info("Starting data retention policy enforcement.")
    try:
        three_months_ago = datetime.utcnow() - timedelta(days=90)
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        deleted_count = 0

        # Delete old events (3 months retention)
        # Using `delete()` with `synchronize_session='fetch'` for efficiency
        events_deleted = Event.query.filter(Event.created_at < three_months_ago).delete(synchronize_session='fetch')
        deleted_count += events_deleted
        logger.info(f"Deleted {events_deleted} old events (older than 3 months).")

        # Delete old campaign metrics (3 months retention)
        campaign_metrics_deleted = CampaignMetric.query.filter(CampaignMetric.created_at < three_months_ago).delete(synchronize_session='fetch')
        deleted_count += campaign_metrics_deleted
        logger.info(f"Deleted {campaign_metrics_deleted} old campaign metrics (older than 3 months).")

        # Delete old ingestion logs (3 months retention)
        ingestion_logs_deleted = IngestionLog.query.filter(IngestionLog.upload_timestamp < three_months_ago).delete(synchronize_session='fetch')
        deleted_count += ingestion_logs_deleted
        logger.info(f"Deleted {ingestion_logs_deleted} old ingestion logs (older than 3 months).")

        # Offers: Retain for 6 months, but only delete if not 'Active'
        # We delete offers that are 'Expired' or 'Inactive' AND older than 6 months.
        offers_deleted = Offer.query.filter(
            Offer.created_at < six_months_ago,
            Offer.offer_status.in_(['Expired', 'Inactive']) 
        ).delete(synchronize_session='fetch')
        deleted_count += offers_deleted
        logger.info(f"Deleted {offers_deleted} old inactive/expired offers (older than 6 months).")

        # Customers: This is a complex decision. Deleting customers would cascade delete offers/events.
        # Given "single profile view of the customer" (FR2) and potential for long-term customer relationships,
        # hard deleting customer records based on age alone is generally not recommended unless explicitly stated
        # and carefully designed (e.g., anonymization, soft deletion).
        # The BRD has conflicting retention periods (3 months for "all data" vs. 6 months for "offer history").
        # For MVP, and to avoid data integrity issues, customer records are NOT hard deleted based on age alone.
        # This requires further clarification from business stakeholders.
        logger.warning("Customer data deletion based on age is not implemented due to potential conflicts with 'single profile view' and foreign key constraints. This requires further clarification.")

        db.session.commit()
        logger.info(f"Data retention policy enforcement completed. Total records deleted: {deleted_count}.")

    except SQLAlchemyError as e:
        logger.error(f"Database error during data retention enforcement: {e}", exc_info=True)
        db.session.rollback()
    except Exception as e:
        logger.error(f"Error during data retention enforcement: {e}", exc_info=True)
        db.session.rollback()