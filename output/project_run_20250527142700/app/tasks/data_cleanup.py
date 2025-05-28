from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import not_
from sqlalchemy.exc import SQLAlchemyError

# Assuming db and models are defined in app.extensions and app.models respectively
# This is a common Flask project structure.
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog

def cleanup_old_data():
    """
    Task to enforce data retention policies as per BRD:
    - Retain offer history for 6 months (FR18, NFR3).
    - Retain all other data in CDP for 3 months before deletion (FR24, NFR4).
    - Customer records are deleted only if they have no associated offers within 6 months
      and no associated events within 3 months, and the customer record itself is older than 3 months.
    """
    logger = current_app.logger
    logger.info("Starting data cleanup task...")

    try:
        now = datetime.utcnow()
        # Using 30 days per month for approximation. For exact calendar month calculations,
        # consider using dateutil.relativedelta if precision is critical.
        three_months_ago = now - timedelta(days=3 * 30)
        six_months_ago = now - timedelta(days=6 * 30)

        # 1. Clean up DataIngestionLog records older than 3 months
        deleted_logs_count = db.session.query(DataIngestionLog).filter(
            DataIngestionLog.upload_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_logs_count} old DataIngestionLog records.")

        # 2. Clean up Campaign records older than 3 months
        deleted_campaigns_count = db.session.query(Campaign).filter(
            Campaign.created_at < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_campaigns_count} old Campaign records.")

        # 3. Clean up CustomerEvent records older than 3 months
        deleted_events_count = db.session.query(CustomerEvent).filter(
            CustomerEvent.event_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_events_count} old CustomerEvent records.")

        # 4. Clean up Offer records older than 6 months (Offer History)
        deleted_offers_count = db.session.query(Offer).filter(
            Offer.created_at < six_months_ago
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_offers_count} old Offer records.")

        # 5. Clean up Customer records
        # Delete customers whose record is older than 3 months AND
        # who have no associated offers created in the last 6 months AND
        # who have no associated events created in the last 3 months.

        # Subquery to find customer_ids with recent offers (within last 6 months)
        recent_offers_customer_ids = db.session.query(Offer.customer_id).filter(
            Offer.created_at >= six_months_ago
        ).distinct()

        # Subquery to find customer_ids with recent events (within last 3 months)
        recent_events_customer_ids = db.session.query(CustomerEvent.customer_id).filter(
            CustomerEvent.event_timestamp >= three_months_ago
        ).distinct()

        # Main query to delete customers based on the specified criteria
        deleted_customers_count = db.session.query(Customer).filter(
            Customer.created_at < three_months_ago,
            # Ensure no associated offers created in the last 6 months
            not_(Customer.customer_id.in_(recent_offers_customer_ids)),
            # Ensure no associated events created in the last 3 months
            not_(Customer.customer_id.in_(recent_events_customer_ids))
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_customers_count} old Customer records.")

        db.session.commit()
        logger.info("Data cleanup task completed successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during data cleanup: {e}")
        # Re-raise the exception to allow external task runners (e.g., Celery) to catch it
        raise
    except Exception as e:
        # Ensure rollback even for non-SQLAlchemy errors if session was modified
        db.session.rollback()
        logger.error(f"An unexpected error occurred during data cleanup: {e}")
        # Re-raise the exception
        raise