import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta

from backend.extensions import db
from backend.models import Customer, Offer, Event, CampaignMetric

# Configure logging for the cleanup tasks
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def cleanup_old_offers():
    """
    Deletes offers older than 6 months as per FR19 and NFR8.
    Offers are identified by their 'created_at' timestamp.
    """
    # Calculate the cutoff date: 6 months ago from now (UTC)
    cutoff_date = datetime.utcnow() - relativedelta(months=6)
    logger.info(f"Starting cleanup of offers created before "
                f"{cutoff_date.isoformat()} UTC.")

    try:
        # Perform bulk deletion of offers
        # synchronize_session=False is used for efficiency in bulk operations
        # as it avoids loading objects into the session before deletion.
        # The session must be committed afterwards.
        deleted_count = db.session.query(Offer).filter(
            Offer.created_at < cutoff_date
        ).delete(synchronize_session=False)
        db.session.commit()

        if deleted_count > 0:
            logger.info(f"Successfully deleted {deleted_count} offers "
                        f"older than 6 months.")
        else:
            logger.info("No offers found older than 6 months to delete.")

    except Exception as e:
        db.session.rollback()  # Rollback changes on error
        logger.error(f"Error during offer cleanup: {e}", exc_info=True)
        # Re-raise the exception to allow calling context to handle task failure
        raise


def cleanup_old_customer_data():
    """
    Deletes customer, event, and campaign metric data older than 3 months
    as per FR28 and NFR9.
    This function handles foreign key dependencies by deleting child records
    (events, offers) before parent records (customers).
    """
    # Calculate the cutoff date: 3 months ago from now (UTC)
    cutoff_date = datetime.utcnow() - relativedelta(months=3)
    logger.info(f"Starting cleanup of customer-related data created before "
                f"{cutoff_date.isoformat()} UTC.")

    try:
        # 1. Clean up old events
        logger.info("Cleaning up old events...")
        deleted_events_count = db.session.query(Event).filter(
            Event.created_at < cutoff_date
        ).delete(synchronize_session=False)
        db.session.commit()
        logger.info(f"Successfully deleted {deleted_events_count} events "
                    f"older than 3 months.")

        # 2. Clean up old campaign metrics
        logger.info("Cleaning up old campaign metrics...")
        deleted_campaign_metrics_count = db.session.query(CampaignMetric).filter(
            CampaignMetric.created_at < cutoff_date
        ).delete(synchronize_session=False)
        db.session.commit()
        logger.info(f"Successfully deleted {deleted_campaign_metrics_count} "
                    f"campaign metrics older than 3 months.")

        # 3. Identify customers whose 'created_at' is older than 3 months
        # and then delete their associated offers and the customers themselves.
        # This ensures no dangling foreign keys for customers.
        customers_to_delete_ids = [
            c.customer_id for c in Customer.query.filter(
                Customer.created_at < cutoff_date
            ).all()
        ]
        num_customers_to_delete = len(customers_to_delete_ids)

        if num_customers_to_delete > 0:
            logger.info(f"Identified {num_customers_to_delete} customers "
                        f"for deletion (created before "
                        f"{cutoff_date.isoformat()}).")

            # Delete offers associated with these customers first
            deleted_offers_by_customer_count = db.session.query(Offer).filter(
                Offer.customer_id.in_(customers_to_delete_ids)
            ).delete(synchronize_session=False)
            db.session.commit()
            logger.info(f"Successfully deleted "
                        f"{deleted_offers_by_customer_count} offers linked "
                        f"to customers older than 3 months.")

            # Delete the customers themselves
            deleted_customers_count = db.session.query(Customer).filter(
                Customer.customer_id.in_(customers_to_delete_ids)
            ).delete(synchronize_session=False)
            db.session.commit()
            logger.info(f"Successfully deleted {deleted_customers_count} "
                        f"customers older than 3 months.")
        else:
            logger.info("No customer data found older than 3 months to delete.")

    except Exception as e:
        db.session.rollback()  # Rollback changes on error
        logger.error(f"Error during general data cleanup: {e}", exc_info=True)
        # Re-raise the exception to allow calling context to handle task failure
        raise