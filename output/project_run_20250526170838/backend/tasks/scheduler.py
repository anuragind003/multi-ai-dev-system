import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError
from backend.database import db
from backend.models import Customer, Offer, Event, IngestionLog # Assuming these models exist

# Configure logging for the scheduler
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def _get_app_context_db(app: Flask):
    """Helper to get app context and db session."""
    app_context = app.app_context()
    app_context.push()
    return app_context, db.session

def update_offer_statuses(app: Flask):
    """
    Scheduled task to update offer statuses based on expiry logic.
    FR41: Mark offers as expired based on offer end dates for non-journey started customers.
    FR43: Mark offers as expired for journey started customers whose LAN validity is over.
          (Note: For simplicity, this implementation primarily focuses on `end_date` expiry.
          Full FR43 logic involving LAN validity and journey stages would require
          more detailed checks against the `events` table and specific business rules,
          which is a complex piece of the Offer Management module.)
    FR42: Check for and replenish new offers for non-journey started customers whose previous offers have expired.
          (Note: Offer replenishment is a complex business logic involving re-eligibility,
          segmentation, and offer generation. This function only handles expiry and
          serves as a placeholder for the replenishment trigger.)
    """
    app_context, session = _get_app_context_db(app)
    try:
        logger.info("Starting offer status update job...")
        current_date = datetime.utcnow().date()

        # FR41: Mark offers as expired based on offer end dates
        # This applies to any active offer whose end_date has passed.
        offers_to_expire = session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.end_date < current_date
        ).all()

        expired_count = 0
        for offer in offers_to_expire:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            expired_count += 1
        session.commit()
        logger.info(f"Successfully expired {expired_count} offers based on end date.")

        # FR42: Placeholder for offer replenishment logic.
        # This would typically involve identifying customers whose offers just expired
        # and who are eligible for new offers, then triggering a process to generate them.
        logger.info("Offer replenishment logic (FR42) is a placeholder and not yet implemented.")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during offer status update: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during offer status update: {e}")
    finally:
        session.close()
        app_context.pop()
        logger.info("Offer status update job finished.")

def clean_old_data(app: Flask):
    """
    Scheduled task to enforce data retention policies.
    FR19, NFR8: Maintain Offer history for the past 6 months.
    FR28, NFR9: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
                (Interpreted as: transactional data like events, ingestion logs, and old offers.
                Core customer profiles in the `Customer` table are typically retained longer.)
    """
    app_context, session = _get_app_context_db(app)
    try:
        logger.info("Starting old data cleanup job...")
        current_datetime = datetime.utcnow()

        # Clean offers older than 6 months (FR19, NFR8)
        six_months_ago = current_datetime - timedelta(days=6 * 30) # Approximate 6 months
        offers_deleted = session.query(Offer).filter(Offer.created_at < six_months_ago).delete()
        logger.info(f"Deleted {offers_deleted} old offer records (older than 6 months).")

        # Clean events older than 3 months (FR28, NFR9)
        three_months_ago = current_datetime - timedelta(days=3 * 30) # Approximate 3 months
        events_deleted = session.query(Event).filter(Event.created_at < three_months_ago).delete()
        logger.info(f"Deleted {events_deleted} old event records (older than 3 months).")

        # Clean ingestion logs older than 3 months (FR28, NFR9)
        ingestion_logs_deleted = session.query(IngestionLog).filter(IngestionLog.upload_timestamp < three_months_ago).delete()
        logger.info(f"Deleted {ingestion_logs_deleted} old ingestion log records (older than 3 months).")

        session.commit()
        logger.info("Old data cleanup job finished successfully.")

    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error during data cleanup: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during data cleanup: {e}")
    finally:
        session.close()
        app_context.pop()
        logger.info("Old data cleanup job finished.")

def ingest_offermart_data_daily(app: Flask):
    """
    Scheduled task for daily data ingestion from Offermart. (FR9)
    This is a placeholder for the actual complex ingestion logic.
    It would involve reading from a staging area, validation, deduplication,
    and insertion into CDP tables.
    """
    app_context, session = _get_app_context_db(app)
    try:
        logger.info("Starting daily Offermart data ingestion job...")
        # --- Placeholder for actual ingestion logic ---
        # 1. Read data from staging area (e.g., CSV file, another DB, API endpoint)
        # 2. Perform FR1: basic column-level validation
        # 3. Perform FR3, FR4, FR5, FR6: Deduplication logic
        # 4. Insert/Update data into Customer and Offer tables
        # 5. Log success/errors (FR37, FR38)
        logger.info("Offermart data ingestion logic is a placeholder. No actual data processed.")
        # Example: Simulate some work
        # time.sleep(5)
        logger.info("Daily Offermart data ingestion job finished.")
    except Exception as e:
        logger.error(f"Error during daily Offermart data ingestion: {e}")
    finally:
        session.close()
        app_context.pop()

def export_to_edw_daily(app: Flask):
    """
    Scheduled task for daily data export to EDW. (FR27)
    This is a placeholder for the actual export logic.
    It would involve querying CDP data, transforming it, and pushing it to EDW.
    """
    app_context, session = _get_app_context_db(app)
    try:
        logger.info("Starting daily EDW data export job...")
        # --- Placeholder for actual export logic ---
        # 1. Query relevant data from Customer, Offer, Event, CampaignMetric tables
        # 2. Transform data to EDW format (as per Question 10 in BRD ambiguities)
        # 3. Push data to EDW (e.g., via file transfer, direct DB insert, API)
        logger.info("EDW data export logic is a placeholder. No actual data exported.")
        logger.info("Daily EDW data export job finished.")
    except Exception as e:
        logger.error(f"Error during daily EDW data export: {e}")
    finally:
        session.close()
        app_context.pop()

def reverse_feed_to_offermart_daily(app: Flask):
    """
    Scheduled task for daily reverse feed to Offermart. (FR10)
    This is a placeholder for the actual reverse feed logic.
    It would involve querying updated offer data from CDP and pushing it back to Offermart.
    """
    app_context, session = _get_app_context_db(app)
    try:
        logger.info("Starting daily reverse feed to Offermart job...")
        # --- Placeholder for actual reverse feed logic ---
        # 1. Query updated offer data (e.g., offers updated by E-aggregators via APIs)
        # 2. Transform data to Offermart format
        # 3. Push data to Offermart staging area or API
        logger.info("Reverse feed to Offermart logic is a placeholder. No actual data processed.")
        logger.info("Daily reverse feed to Offermart job finished.")
    except Exception as e:
        logger.error(f"Error during daily reverse feed to Offermart: {e}")
    finally:
        session.close()
        app_context.pop()

def start_scheduler(app: Flask):
    """
    Initializes and starts the APScheduler.
    Schedules various background tasks.
    """
    logger.info("Initializing APScheduler...")

    # Schedule offer status updates daily at a specific time (e.g., 2 AM UTC)
    scheduler.add_job(
        func=update_offer_statuses,
        trigger=CronTrigger(hour=2, minute=0),
        args=[app],
        id='update_offer_statuses_job',
        name='Update Offer Statuses',
        replace_existing=True
    )
    logger.info("Scheduled 'Update Offer Statuses' job daily at 02:00 AM UTC.")

    # Schedule data cleanup daily at a specific time (e.g., 3 AM UTC)
    scheduler.add_job(
        func=clean_old_data,
        trigger=CronTrigger(hour=3, minute=0),
        args=[app],
        id='clean_old_data_job',
        name='Clean Old Data',
        replace_existing=True
    )
    logger.info("Scheduled 'Clean Old Data' job daily at 03:00 AM UTC.")

    # Schedule daily Offermart data ingestion (e.g., 4 AM UTC)
    scheduler.add_job(
        func=ingest_offermart_data_daily,
        trigger=CronTrigger(hour=4, minute=0),
        args=[app],
        id='ingest_offermart_data_job',
        name='Ingest Offermart Data',
        replace_existing=True
    )
    logger.info("Scheduled 'Ingest Offermart Data' job daily at 04:00 AM UTC.")

    # Schedule daily EDW export (e.g., 23:00 / 11 PM UTC - "by day end" FR27)
    scheduler.add_job(
        func=export_to_edw_daily,
        trigger=CronTrigger(hour=23, minute=0),
        args=[app],
        id='export_to_edw_job',
        name='Export to EDW',
        replace_existing=True
    )
    logger.info("Scheduled 'Export to EDW' job daily at 23:00 PM UTC.")

    # Schedule daily reverse feed to Offermart (e.g., 22:00 / 10 PM UTC - "hourly/daily" FR10, choosing daily for now)
    scheduler.add_job(
        func=reverse_feed_to_offermart_daily,
        trigger=CronTrigger(hour=22, minute=0),
        args=[app],
        id='reverse_feed_offermart_job',
        name='Reverse Feed to Offermart',
        replace_existing=True
    )
    logger.info("Scheduled 'Reverse Feed to Offermart' job daily at 22:00 PM UTC.")

    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started.")
    else:
        logger.info("APScheduler is already running.")

def shutdown_scheduler():
    """Shuts down the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler shut down.")