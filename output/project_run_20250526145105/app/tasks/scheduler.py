import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.customer_service import CustomerService
from app.services.offer_service import OfferService
from app.services.data_ingestion_service import DataIngestionService
from app.services.data_export_service import DataExportService
from app.services.moengage_service import MoengageService
from app.services.data_cleanup_service import DataCleanupService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

async def _get_db_session() -> AsyncSession:
    """Helper to get an async database session for scheduled jobs."""
    async for session in get_db():
        return session # Return the session, as we only need one for the job

async def ingest_offermart_data_daily():
    """
    Scheduled task to ingest daily data from Offermart to CDP.
    Handles FR1, FR9, NFR3, NFR5.
    This process should also trigger deduplication and offer precedence logic.
    """
    logger.info("Starting daily Offermart data ingestion...")
    session: AsyncSession = await _get_db_session()
    try:
        data_ingestion_service = DataIngestionService(session)
        await data_ingestion_service.ingest_offermart_data()
        logger.info("Daily Offermart data ingestion completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily Offermart data ingestion: {e}", exc_info=True)
    finally:
        await session.close()

async def push_reverse_feed_to_offermart_daily():
    """
    Scheduled task to push daily reverse feed from CDP to Offermart.
    Handles FR10, NFR6.
    """
    logger.info("Starting daily reverse feed push to Offermart...")
    session: AsyncSession = await _get_db_session()
    try:
        data_export_service = DataExportService(session)
        await data_export_service.push_reverse_feed_to_offermart()
        logger.info("Daily reverse feed push to Offermart completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily reverse feed push to Offermart: {e}", exc_info=True)
    finally:
        await session.close()

async def push_realtime_offers_to_offermart_hourly():
    """
    Scheduled task to push real-time offers from CDP to Analytics Offermart.
    Handles FR7, NFR8.
    This might be for offers generated via APIs that need to be synced back.
    """
    logger.info("Starting hourly real-time offers push to Offermart...")
    session: AsyncSession = await _get_db_session()
    try:
        data_export_service = DataExportService(session)
        await data_export_service.push_realtime_offers_to_offermart()
        logger.info("Hourly real-time offers push to Offermart completed successfully.")
    except Exception as e:
        logger.error(f"Error during hourly real-time offers push to Offermart: {e}", exc_info=True)
    finally:
        await session.close()

async def export_data_to_edw_daily():
    """
    Scheduled task to push daily data from LTFS Offer CDP to EDW.
    Handles FR35, FR36, NFR11.
    """
    logger.info("Starting daily data export to EDW...")
    session: AsyncSession = await _get_db_session()
    try:
        data_export_service = DataExportService(session)
        await data_export_service.export_data_to_edw()
        logger.info("Daily data export to EDW completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily data export to EDW: {e}", exc_info=True)
    finally:
        await session.close()

async def update_offer_statuses_daily():
    """
    Scheduled task to update offer statuses (e.g., 'Expired') based on business logic.
    Handles FR15, FR16, FR18, FR51, FR52, FR53.
    """
    logger.info("Starting daily offer status update...")
    session: AsyncSession = await _get_db_session()
    try:
        offer_service = OfferService(session)
        await offer_service.update_expired_offers()
        logger.info("Daily offer status update completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily offer status update: {e}", exc_info=True)
    finally:
        await session.close()

async def cleanup_old_data_monthly():
    """
    Scheduled task to clean up old data based on retention policies.
    Handles FR23 (offer history 6 months), FR37 (CDP data 3 months), NFR9, NFR10.
    """
    logger.info("Starting monthly old data cleanup...")
    session: AsyncSession = await _get_db_session()
    try:
        data_cleanup_service = DataCleanupService(session)
        await data_cleanup_service.cleanup_old_customer_data(retention_months=settings.CDP_DATA_RETENTION_MONTHS)
        await data_cleanup_service.cleanup_old_offer_history(retention_months=settings.OFFER_HISTORY_RETENTION_MONTHS)
        logger.info("Monthly old data cleanup completed successfully.")
    except Exception as e:
        logger.error(f"Error during monthly old data cleanup: {e}", exc_info=True)
    finally:
        await session.close()

async def generate_moengage_file_daily():
    """
    Scheduled task to generate the Moengage format file daily.
    Handles FR54. This file will then be available for download via API.
    """
    logger.info("Starting daily Moengage file generation...")
    session: AsyncSession = await _get_db_session()
    try:
        moengage_service = MoengageService(session)
        await moengage_service.generate_campaign_file()
        logger.info("Daily Moengage file generation completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily Moengage file generation: {e}", exc_info=True)
    finally:
        await session.close()

def start_scheduler():
    """
    Adds all scheduled jobs and starts the scheduler.
    """
    logger.info("Initializing scheduler jobs...")

    # Daily tasks
    # Ingest Offermart data daily (e.g., early morning at 3 AM)
    scheduler.add_job(ingest_offermart_data_daily, CronTrigger(hour=3, minute=0), name="Daily Offermart Ingestion")

    # Push reverse feed to Offermart daily (e.g., late evening at 10 PM)
    scheduler.add_job(push_reverse_feed_to_offermart_daily, CronTrigger(hour=22, minute=0), name="Daily Reverse Feed to Offermart")

    # Export data to EDW daily (by day end, e.g., 11 PM)
    scheduler.add_job(export_data_to_edw_daily, CronTrigger(hour=23, minute=0), name="Daily Data Export to EDW")

    # Update offer statuses daily (e.g., after ingestion and before exports, at 4 AM)
    scheduler.add_job(update_offer_statuses_daily, CronTrigger(hour=4, minute=0), name="Daily Offer Status Update")

    # Generate Moengage file daily (e.g., after all data processing, at 5 AM)
    scheduler.add_job(generate_moengage_file_daily, CronTrigger(hour=5, minute=0), name="Daily Moengage File Generation")

    # Hourly tasks
    # Push real-time offers to Offermart hourly (at the top of every hour)
    scheduler.add_job(push_realtime_offers_to_offermart_hourly, CronTrigger(minute='0'), name="Hourly Real-time Offers to Offermart")

    # Monthly tasks (e.g., 1st day of the month at 2 AM)
    # Cleanup old data
    scheduler.add_job(cleanup_old_data_monthly, CronTrigger(day='1', hour=2, minute=0), name="Monthly Data Cleanup")

    scheduler.start()
    logger.info("Scheduler started with configured jobs.")

def shutdown_scheduler():
    """
    Shuts down the scheduler gracefully.
    """
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")