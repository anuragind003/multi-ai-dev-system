import logging
from datetime import datetime, timedelta
import csv
import os
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload

# Assuming these are defined in app/models.py and app/database.py
from app.models import Customer, Offer, OfferHistory, CampaignEvent
from app.database import get_db_session_context # Assuming a context manager for session

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration Constants (could be moved to a config file) ---
MOENGAGE_FILE_PATH = "data/moengage_files"
OFFER_HISTORY_RETENTION_MONTHS = 6
CDP_DATA_RETENTION_MONTHS = 3 # For campaign events, inactive offers etc.
LAN_EXPIRY_DAYS = 30 # Assumption for FR53: Loan Application Number validity period

# Ensure the directory for Moengage files exists
os.makedirs(MOENGAGE_FILE_PATH, exist_ok=True)

# --- Helper Functions ---
async def _get_active_offers_for_moengage(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Fetches active offers suitable for Moengage export.
    This is a simplified example; actual logic would be more complex.
    """
    # FR54: Generate Moengage format file in .csv format.
    # This implies filtering for 'Active' offers, potentially 'Fresh', 'Enrich' types
    # and customers not marked as DND (FR34).
    # Also, consider offer precedence rules (FR25-FR32) to ensure only the prevailing offer is sent.
    # For simplicity, fetching all active offers not DND.

    # Join Customer and Offer tables
    stmt = select(Customer, Offer).join(Offer, Customer.customer_id == Offer.customer_id).where(
        and_(
            Offer.offer_status == "Active",
            Customer.dnd_status == False
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    moengage_data = []
    for customer, offer in rows:
        # This is a placeholder for actual Moengage format.
        # FR54 implies a specific format, which is not detailed in BRD.
        # Assuming basic customer and offer details.
        # Ensure all fields are strings for CSV export
        moengage_data.append({
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan_number": customer.pan_number,
            "aadhaar_ref_number": customer.aadhaar_ref_number,
            "ucid_number": customer.ucid_number,
            "offer_id": str(offer.offer_id),
            "product_type": offer.product_type,
            "offer_status": offer.offer_status,
            "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else "",
            "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else "",
            "is_journey_started": str(offer.is_journey_started),
            "loan_application_id": offer.loan_application_id if offer.loan_application_id else "",
            "customer_segments": ",".join(customer.customer_segments) if customer.customer_segments else "",
            "propensity_flag": customer.propensity_flag if customer.propensity_flag else "",
            # Add other relevant offer_details fields if they are consistently structured
            # For example, if offer_details always has 'loan_amount', 'interest_rate':
            "loan_amount": offer.offer_details.get("loan_amount", "") if offer.offer_details else "",
            "interest_rate": offer.offer_details.get("interest_rate", "") if offer.offer_details else "",
            # ... more fields as per Moengage requirement
        })
    return moengage_data

# --- Scheduled Task Functions ---

async def process_offermart_data_batch():
    """
    Scheduled task to ingest and process daily data from Offermart.
    (FR9, NFR5, FR1, FR2-FR6, FR25-FR32)
    This function would typically trigger a service layer function.
    """
    logger.info("Starting daily Offermart data ingestion and processing...")
    try:
        async with get_db_session_context() as db:
            # Simulate fetching data from a staging area or external source
            # In a real scenario, this would involve reading from a file, S3, or another DB.
            # For this example, we'll just log the action.
            logger.info("Simulating data fetch from Offermart staging area.")

            # Placeholder for actual data processing logic:
            # 1. Basic column-level validation (FR1, NFR3)
            # 2. Deduplication (FR2-FR6) - against existing CDP and Customer 360 (if accessible)
            # 3. Offer precedence rules (FR25-FR32)
            # 4. Insert/Update Customers and Offers in CDP DB
            # 5. Update offer history (FR23)
            # 6. Mark old offers as 'Duplicate' if enriched (FR20)

            # Example: A simple update to demonstrate DB interaction
            # This is NOT the full logic, just a placeholder.
            # await db.execute(update(Customer).where(Customer.mobile_number == "1234567890").values(customer_segments=["C1", "C2"]))
            # await db.commit()

            logger.info("Offermart data processing completed successfully (simulated).")
    except Exception as e:
        logger.error(f"Error during Offermart data processing: {e}", exc_info=True)

async def generate_and_send_reverse_feed_to_offermart():
    """
    Scheduled task to generate and push daily reverse feed to Offermart.
    (FR10, NFR6)
    """
    logger.info("Starting daily reverse feed generation for Offermart...")
    try:
        async with get_db_session_context() as db:
            # Identify data updates (e.g., offer status changes, new journey starts)
            # This would involve querying the database for changes since last run.
            # For simplicity, we'll just log.
            logger.info("Simulating identification of updated offer data for reverse feed.")

            # Placeholder for actual data export and push logic
            # This might involve generating a file, calling an API, etc.
            logger.info("Reverse feed generated and sent to Offermart successfully (simulated).")
    except Exception as e:
        logger.error(f"Error during reverse feed generation: {e}", exc_info=True)

async def export_data_to_edw():
    """
    Scheduled task to pass data from LTFS Offer CDP to EDW.
    (FR35, FR36, NFR11)
    """
    logger.info("Starting daily data export to EDW...")
    try:
        async with get_db_session_context() as db:
            # Query relevant data (customers, offers, campaign events)
            # This would involve selecting data based on criteria (e.g., all data, or incremental changes)
            # For simplicity, we'll just log.
            logger.info("Simulating data extraction for EDW.")

            # Placeholder for actual data transformation and export logic
            # This might involve generating files, pushing to a data lake, etc.
            logger.info("Data exported to EDW successfully (simulated).")
    except Exception as e:
        logger.error(f"Error during EDW data export: {e}", exc_info=True)

async def update_offer_expiries():
    """
    Scheduled task to update offer statuses to 'Expired' based on business logic.
    (FR15, FR51, FR53)
    """
    logger.info("Starting offer expiry update process...")
    try:
        async with get_db_session_context() as db:
            current_datetime = datetime.now()
            current_date = current_datetime.date()
            
            # FR51: Mark offers as expired based on offer end dates for non-journey started customers.
            # Select offers that are active, not journey started, and whose end date is today or in the past
            stmt_select_no_journey = select(Offer).where(
                and_(
                    Offer.offer_status == "Active",
                    Offer.is_journey_started == False,
                    Offer.offer_end_date <= current_date
                )
            )
            offers_to_expire_no_journey = (await db.execute(stmt_select_no_journey)).scalars().all()

            for offer in offers_to_expire_no_journey:
                old_status = offer.offer_status
                offer.offer_status = "Expired"
                offer.updated_at = current_datetime
                db.add(offer) # Mark for update

                history_entry = OfferHistory(
                    offer_id=offer.offer_id,
                    customer_id=offer.customer_id,
                    old_offer_status=old_status,
                    new_offer_status="Expired",
                    change_reason="Offer end date passed, no journey started",
                    snapshot_offer_details=offer.offer_details # Snapshot current details
                )
                db.add(history_entry)
                logger.info(f"Offer {offer.offer_id} for customer {offer.customer_id} expired (no journey started).")

            # FR53: Mark offers as expired within the offers data if the LAN validity post loan application journey start date is over.
            # Assumption: LAN validity is tracked by `updated_at` + `LAN_EXPIRY_DAYS` if `is_journey_started` is True.
            # FR15: Prevent modification of customer offers with a started loan application journey until the application is either expired or rejected.
            # This task marks them expired, which is a status change due to expiry, not a business rule violation.
            
            lan_expiry_threshold = current_datetime - timedelta(days=LAN_EXPIRY_DAYS)

            # Select offers that are active, journey started, have a LAN, and their last update is past the LAN expiry threshold
            stmt_select_journey = select(Offer).where(
                and_(
                    Offer.offer_status == "Active",
                    Offer.is_journey_started == True,
                    Offer.loan_application_id.isnot(None), # Ensure LAN exists
                    Offer.updated_at <= lan_expiry_threshold # Assuming updated_at reflects journey start/last update
                )
            )
            offers_to_expire_journey = (await db.execute(stmt_select_journey)).scalars().all()

            for offer in offers_to_expire_journey:
                old_status = offer.offer_status
                offer.offer_status = "Expired"
                offer.updated_at = current_datetime
                db.add(offer) # Mark for update

                history_entry = OfferHistory(
                    offer_id=offer.offer_id,
                    customer_id=offer.customer_id,
                    old_offer_status=old_status,
                    new_offer_status="Expired",
                    change_reason="Loan application validity period over",
                    snapshot_offer_details=offer.offer_details # Snapshot current details
                )
                db.add(history_entry)
                logger.info(f"Offer {offer.offer_id} for customer {offer.customer_id} expired (LAN validity over).")

            await db.commit()
            logger.info("Offer expiry update process completed.")
    except Exception as e:
        logger.error(f"Error during offer expiry update: {e}", exc_info=True)

async def generate_moengage_file():
    """
    Scheduled task to generate the Moengage format CSV file.
    (FR54, FR55, NFR12)
    """
    logger.info("Starting Moengage file generation...")
    try:
        async with get_db_session_context() as db:
            moengage_data = await _get_active_offers_for_moengage(db)

            if not moengage_data:
                logger.info("No active offers found for Moengage file generation.")
                return

            # Define CSV file name with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"moengage_offers_{timestamp}.csv"
            file_path = os.path.join(MOENGAGE_FILE_PATH, file_name)

            # Get headers from the first dictionary's keys
            headers = list(moengage_data[0].keys())

            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(moengage_data)

            logger.info(f"Moengage file generated successfully at: {file_path}")
    except Exception as e:
        logger.error(f"Error during Moengage file generation: {e}", exc_info=True)

async def cleanup_old_data():
    """
    Scheduled task to clean up old data based on retention policies.
    (FR23, FR37, NFR9, NFR10)
    """
    logger.info("Starting old data cleanup process...")
    try:
        async with get_db_session_context() as db:
            current_datetime = datetime.now()

            # Cleanup Offer History (FR23, NFR9: 6 months)
            history_retention_threshold = current_datetime - timedelta(days=OFFER_HISTORY_RETENTION_MONTHS * 30) # Approx months
            
            delete_history_stmt = delete(OfferHistory).where(
                OfferHistory.change_timestamp < history_retention_threshold
            )
            deleted_history_count = (await db.execute(delete_history_stmt)).rowcount
            logger.info(f"Deleted {deleted_history_count} old offer history records.")

            # Cleanup Campaign Events (FR37, NFR10: 3 months)
            campaign_event_retention_threshold = current_datetime - timedelta(days=CDP_DATA_RETENTION_MONTHS * 30)
            
            delete_campaign_events_stmt = delete(CampaignEvent).where(
                CampaignEvent.event_timestamp < campaign_event_retention_threshold
            )
            deleted_campaign_events_count = (await db.execute(delete_campaign_events_stmt)).rowcount
            logger.info(f"Deleted {deleted_campaign_events_count} old campaign event records.")

            # Cleanup old offers (e.g., 'Expired', 'Inactive', 'Duplicate' offers older than 3 months)
            # This needs careful consideration not to delete offers linked to active customers or recent history.
            # For simplicity, only deleting offers that are 'Expired' or 'Duplicate' and older than 3 months.
            # Active offers should generally not be deleted by this cleanup.
            offer_retention_threshold = current_datetime - timedelta(days=CDP_DATA_RETENTION_MONTHS * 30)
            
            delete_old_offers_stmt = delete(Offer).where(
                and_(
                    Offer.offer_status.in_(["Expired", "Inactive", "Duplicate"]),
                    Offer.updated_at < offer_retention_threshold
                )
            )
            deleted_offers_count = (await db.execute(delete_old_offers_stmt)).rowcount
            logger.info(f"Deleted {deleted_offers_count} old inactive/expired/duplicate offers.")

            await db.commit()
            logger.info("Old data cleanup process completed.")
    except Exception as e:
        logger.error(f"Error during data cleanup: {e}", exc_info=True)

# Main function to run all scheduled tasks (for testing/manual trigger)
async def run_all_scheduled_tasks():
    logger.info("Running all scheduled tasks...")
    await process_offermart_data_batch()
    await generate_and_send_reverse_feed_to_offermart()
    await export_data_to_edw()
    await update_offer_expiries()
    await generate_moengage_file()
    await cleanup_old_data()
    logger.info("All scheduled tasks completed.")