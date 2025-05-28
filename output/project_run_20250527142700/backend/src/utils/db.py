import logging
from datetime import datetime, timedelta

# Assuming db and models are accessible from a central point like backend.cdp
# In a Flask app, db is typically initialized in backend/cdp/__init__.py
# and models are defined in backend/cdp/models.py
try:
    from backend.cdp import db
    from backend.cdp.models import Customer, Offer, OfferHistory, Event, Campaign
except ImportError as e:
    # This error indicates a critical setup issue if the application is running.
    # It means the Flask app context or module structure is not as expected.
    logging.error(f"Failed to import db or models from backend.cdp: {e}. "
                  "Ensure backend.cdp and backend.cdp.models are correctly defined and accessible.")
    # In a production environment, this would likely lead to an application crash
    # if these imports are essential for the application's core functionality.
    raise # Re-raise the exception to indicate a fatal setup error.

logger = logging.getLogger(__name__)

def init_db():
    """
    Initializes the database by creating all tables defined in the models.
    This function is typically called once during application startup or
    for development/testing purposes.
    It requires an active Flask application context.
    """
    try:
        with db.app.app_context():
            db.create_all()
            logger.info("Database tables created successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}", exc_info=True)
        raise # Re-raise to indicate failure

def clean_old_data():
    """
    Implements the data retention policies as per NFR10 and FR29:
    - Offer history maintained for 6 months (FR20).
    - All other data in CDP maintained for 3 months before deletion (FR29).
    This function should be run as a scheduled job.
    It requires an active Flask application context.
    """
    with db.app.app_context():
        try:
            # Calculate cutoff dates
            # Using 30 days per month for approximation. For exact, use date arithmetic.
            offer_history_cutoff = datetime.now() - timedelta(days=6 * 30)
            cdp_data_cutoff = datetime.now() - timedelta(days=3 * 30)

            # 1. Clean old OfferHistory (6 months retention)
            deleted_offer_history_count = OfferHistory.query.filter(
                OfferHistory.status_change_date < offer_history_cutoff
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_offer_history_count} old offer history records.")

            # 2. Clean old Events (3 months retention)
            deleted_event_count = Event.query.filter(
                Event.event_timestamp < cdp_data_cutoff
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_event_count} old event records.")

            # 3. Clean old Campaigns (3 months retention)
            # Assuming `campaign_date` is the relevant field for retention.
            deleted_campaign_count = Campaign.query.filter(
                Campaign.campaign_date < cdp_data_cutoff
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_campaign_count} old campaign records.")

            # 4. Clean old Offers (3 months retention for inactive/expired)
            # Only delete offers that are explicitly 'Expired' or 'Inactive'
            # AND whose `updated_at` timestamp is older than the 3-month cutoff.
            deleted_inactive_expired_offers = Offer.query.filter(
                Offer.offer_status.in_(['Expired', 'Inactive']),
                Offer.updated_at < cdp_data_cutoff
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_inactive_expired_offers} inactive/expired offer records older than 3 months.")

            # 5. Clean old Customers (3 months retention for those with no associated offers)
            # Identify customer IDs that still have associated offers (active or otherwise).
            # This ensures we don't delete customers who are still linked to offers.
            # The `customer_ids_with_offers` subquery gets all customer_ids present in the offers table.
            customer_ids_with_offers = db.session.query(Offer.customer_id).distinct().subquery()

            # Delete customers whose `updated_at` is older than 3 months
            # AND whose `customer_id` is NOT in the list of customers with offers.
            deleted_customer_count = Customer.query.filter(
                Customer.updated_at < cdp_data_cutoff,
                ~Customer.customer_id.in_(customer_ids_with_offers)
            ).delete(synchronize_session=False)
            logger.info(f"Deleted {deleted_customer_count} old customer records with no associated offers.")

            db.session.commit()
            logger.info("Old data cleanup completed successfully.")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during old data cleanup: {e}", exc_info=True)
            raise # Re-raise to indicate failure if this is part of a scheduled job.