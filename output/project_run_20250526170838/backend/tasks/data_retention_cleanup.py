import datetime
import logging
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError

# Configure logging for the cleanup task
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_data_retention_cleanup(app: Flask):
    """
    Performs data retention cleanup based on defined policies.

    - Offers with `created_at` timestamp older than 6 months are deleted.
    - Events with `created_at` timestamp older than 3 months are deleted.
    - Campaign Metrics with `created_at` timestamp older than 3 months are deleted.
    - Ingestion Logs with `upload_timestamp` older than 3 months are deleted.

    This function must be run within a Flask application context.
    """
    with app.app_context():
        from backend.extensions import db
        from backend.models import Offer, Event, CampaignMetric, IngestionLog

        logger.info("Starting data retention cleanup task...")

        current_datetime = datetime.datetime.now()

        # Define retention periods in months
        OFFER_RETENTION_MONTHS = 6
        GENERAL_RETENTION_MONTHS = 3

        # Calculate cutoff datetimes
        # Using an approximation of 30 days per month for simplicity.
        # For more precise monthly calculations, dateutil.relativedelta could be used.
        offer_cutoff_datetime = current_datetime - datetime.timedelta(days=OFFER_RETENTION_MONTHS * 30)
        general_cutoff_datetime = current_datetime - datetime.timedelta(days=GENERAL_RETENTION_MONTHS * 30)

        try:
            # Cleanup Offers (FR19, NFR8: 6 months retention)
            offers_to_delete_count = db.session.query(Offer).filter(Offer.created_at < offer_cutoff_datetime).count()
            if offers_to_delete_count > 0:
                db.session.query(Offer).filter(Offer.created_at < offer_cutoff_datetime).delete(synchronize_session=False)
                logger.info(f"Deleted {offers_to_delete_count} offers older than "
                            f"{OFFER_RETENTION_MONTHS} months (before {offer_cutoff_datetime.isoformat()}).")
            else:
                logger.info(f"No offers found older than {OFFER_RETENTION_MONTHS} months to delete.")

            # Cleanup Events (FR28, NFR9: 3 months retention for general data)
            events_to_delete_count = db.session.query(Event).filter(Event.created_at < general_cutoff_datetime).count()
            if events_to_delete_count > 0:
                db.session.query(Event).filter(Event.created_at < general_cutoff_datetime).delete(synchronize_session=False)
                logger.info(f"Deleted {events_to_delete_count} events older than "
                            f"{GENERAL_RETENTION_MONTHS} months (before {general_cutoff_datetime.isoformat()}).")
            else:
                logger.info(f"No events found older than {GENERAL_RETENTION_MONTHS} months to delete.")

            # Cleanup Campaign Metrics (FR28, NFR9: 3 months retention for general data)
            campaign_metrics_to_delete_count = db.session.query(CampaignMetric).filter(
                CampaignMetric.created_at < general_cutoff_datetime).count()
            if campaign_metrics_to_delete_count > 0:
                db.session.query(CampaignMetric).filter(
                    CampaignMetric.created_at < general_cutoff_datetime).delete(synchronize_session=False)
                logger.info(f"Deleted {campaign_metrics_to_delete_count} campaign metrics older than "
                            f"{GENERAL_RETENTION_MONTHS} months (before {general_cutoff_datetime.isoformat()}).")
            else:
                logger.info(f"No campaign metrics found older than {GENERAL_RETENTION_MONTHS} months to delete.")

            # Cleanup Ingestion Logs (FR28, NFR9: 3 months retention for general data)
            ingestion_logs_to_delete_count = db.session.query(IngestionLog).filter(
                IngestionLog.upload_timestamp < general_cutoff_datetime).count()
            if ingestion_logs_to_delete_count > 0:
                db.session.query(IngestionLog).filter(
                    IngestionLog.upload_timestamp < general_cutoff_datetime).delete(synchronize_session=False)
                logger.info(f"Deleted {ingestion_logs_to_delete_count} ingestion logs older than "
                            f"{GENERAL_RETENTION_MONTHS} months (before {general_cutoff_datetime.isoformat()}).")
            else:
                logger.info(f"No ingestion logs found older than {GENERAL_RETENTION_MONTHS} months to delete.")

            db.session.commit()
            logger.info("Data retention cleanup completed successfully.")

        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error during data retention cleanup: {e}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"An unexpected error occurred during data retention cleanup: {e}")
        finally:
            db.session.close()

if __name__ == "__main__":
    # This block demonstrates how the cleanup task would be run.
    # In a real Flask application, you would typically import your app factory
    # or the initialized app instance. This task would then be scheduled
    # using a tool like Flask-APScheduler, Celery Beat, or a cron job
    # that executes this script.
    try:
        from backend.app import create_app
        app = create_app()
        run_data_retention_cleanup(app)
    except ImportError:
        logger.error("Could not import 'create_app' from 'backend.app'. "
                     "Ensure your Flask application is correctly structured and initialized.")
        logger.error("This script is intended to be run within a Flask application context.")
    except Exception as e:
        logger.critical(f"Failed to initialize Flask app or run cleanup task: {e}")