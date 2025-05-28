from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_, and_

# Assuming db and models are defined in app.extensions and app.models respectively
# This is a common Flask project structure.
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog

def cleanup_old_data():
    """
    Task to enforce data retention policies:
    - Retain offer history for 6 months (FR18, NFR3).
    - Retain all other data in CDP for 3 months before deletion (FR24, NFR4).
    """
    current_app.logger.info("Starting data cleanup task...")
    try:
        # Calculate cutoff dates (approximate for months)
        three_months_ago = datetime.utcnow() - timedelta(days=3 * 30)
        six_months_ago = datetime.utcnow() - timedelta(days=6 * 30)

        # 1. Clean up Offer history older than 6 months
        # NFR3: "retain offer history data for 06 months."
        # NFR4: "retain all data within LTFS Offer CDP for a period of 3 months before deletion."
        # Interpreting this as: offers older than 6 months can be deleted.
        offers_to_delete = Offer.query.filter(Offer.created_at < six_months_ago).all()
        deleted_offers_count = 0
        for offer in offers_to_delete:
            db.session.delete(offer)
            deleted_offers_count += 1
        db.session.commit()
        current_app.logger.info(f"Deleted {deleted_offers_count} old offers (older than 6 months).")

        # 2. Clean up Customer Events older than 3 months
        events_to_delete = CustomerEvent.query.filter(CustomerEvent.created_at < three_months_ago).all()
        deleted_events_count = 0
        for event in events_to_delete:
            db.session.delete(event)
            deleted_events_count += 1
        db.session.commit()
        current_app.logger.info(f"Deleted {deleted_events_count} old customer events (older than 3 months).")

        # 3. Clean up Data Ingestion Logs older than 3 months
        logs_to_delete = DataIngestionLog.query.filter(DataIngestionLog.upload_timestamp < three_months_ago).all()
        deleted_logs_count = 0
        for log in logs_to_delete:
            db.session.delete(log)
            deleted_logs_count += 1
        db.session.commit()
        current_app.logger.info(f"Deleted {deleted_logs_count} old data ingestion logs (older than 3 months).")

        # 4. Clean up Campaigns older than 3 months
        campaigns_to_delete = Campaign.query.filter(Campaign.created_at < three_months_ago).all()
        deleted_campaigns_count = 0
        for campaign in campaigns_to_delete:
            db.session.delete(campaign)
            deleted_campaigns_count += 1
        db.session.commit()
        current_app.logger.info(f"Deleted {deleted_campaigns_count} old campaigns (older than 3 months).")

        # Customer records are generally retained as long as there are associated offers or events,
        # or indefinitely as they represent the core profile. Not deleting customers based on age here.

        current_app.logger.info("Data cleanup task completed successfully.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during data cleanup task: {e}", exc_info=True)

def update_offer_statuses():
    """
    Task to update offer statuses based on expiry logic (FR13, FR15, FR37, FR38).
    - Mark offers as 'Expired' if offer_end_date is in the past and no loan application journey started.
    - Mark offers as 'Expired' if loan_application_number exists and its validity post journey start date is over.
      (The exact business logic for LAN validity needs clarification per BRD Question 3).
    """
    current_app.logger.info("Starting offer status update task...")
    try:
        current_date = datetime.utcnow().date()
        updated_count = 0

        # Rule 1: Offers for non-journey started customers expire based on offer end dates (FR37)
        offers_to_expire_by_date = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.offer_end_date < current_date,
            Offer.loan_application_number.is_(None) # No journey started
        ).all()

        for offer in offers_to_expire_by_date:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            updated_count += 1
            current_app.logger.debug(f"Offer {offer.offer_id} expired by end date.")

        # Rule 2: Offers with started loan application journeys (LAN) expire if LAN validity is over (FR38)
        # This requires knowing the validity period or status of a LAN.
        # As per BRD Question 3, this needs clarification.
        # For now, a simplified placeholder: mark as expired if LAN exists and the offer was created > 30 days ago
        # and it's still active (assuming no conversion/rejection event has occurred).
        # A robust solution would query an external LOS system or a dedicated LAN status table/events.
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        offers_to_expire_by_lan = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.isnot(None), # Journey started
            Offer.created_at < thirty_days_ago # Simplistic: LAN is old
            # Add more complex conditions here based on actual LAN status from LOS/events
            # e.g., checking for 'CONVERSION' or 'REJECTED' events associated with this LAN
        ).all()

        for offer in offers_to_expire_by_lan:
            # In a real scenario, this would involve a lookup to the LOS or event data
            # to confirm the LAN's actual status (e.g., expired, rejected, converted).
            # For this placeholder, we proceed with the simplified age-based expiry.
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            updated_count += 1
            current_app.logger.debug(f"Offer {offer.offer_id} expired by LAN age (simplified).")

        db.session.commit()
        current_app.logger.info(f"Offer status update task completed. {updated_count} offers updated.")

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error during offer status update task: {e}", exc_info=True)

def daily_offermart_to_cdp_ingestion():
    """
    Placeholder for daily data ingestion from Offermart to CDP (FR7, NFR5).
    This task would typically:
    1. Connect to Offermart DB (or read files from a designated location).
    2. Extract customer and offer data.
    3. Perform basic column-level validation (FR1, NFR2).
    4. Load data into CDP staging tables or directly into Customer/Offer tables.
    5. Trigger deduplication (FR3, FR4, FR5) and attribution logic (FR20) as subsequent steps.
    """
    current_app.logger.info("Starting daily Offermart to CDP data ingestion task...")
    try:
        # --- Placeholder for actual ingestion logic ---
        # Example:
        # data_from_offermart = get_data_from_offermart_source()
        # validated_data = validate_offermart_data(data_from_offermart)
        # insert_into_cdp_staging(validated_data)
        # trigger_deduplication_and_attribution()
        # --- End Placeholder ---

        current_app.logger.info("Daily Offermart to CDP data ingestion task completed. (Placeholder)")
    except Exception as e:
        current_app.logger.error(f"Error during daily Offermart to CDP ingestion: {e}", exc_info=True)

def hourly_cdp_to_offermart_feed():
    """
    Placeholder for hourly/daily reverse feed from CDP to Offermart (FR8, NFR6).
    This task would typically:
    1. Query updated offer data from CDP (e.g., offers updated by E-aggregators).
    2. Format data according to Offermart's requirements.
    3. Push data to Offermart (e.g., via API, file transfer, or direct DB insert).
    """
    current_app.logger.info("Starting hourly/daily CDP to Offermart reverse feed task...")
    try:
        # --- Placeholder for actual reverse feed logic ---
        # Example:
        # updated_offers = Offer.query.filter(Offer.updated_at > (datetime.utcnow() - timedelta(hours=1))).all()
        # formatted_data = format_for_offermart(updated_offers)
        # push_to_offermart(formatted_data)
        # --- End Placeholder ---

        current_app.logger.info("Hourly/daily CDP to Offermart reverse feed task completed. (Placeholder)")
    except Exception as e:
        current_app.logger.error(f"Error during CDP to Offermart reverse feed: {e}", exc_info=True)

def daily_cdp_to_edw_push():
    """
    Placeholder for daily data transfer from LTFS Offer CDP to EDW (FR23, NFR8).
    This task would typically:
    1. Extract all relevant CDP data (customers, offers, events, campaigns).
    2. Transform data into an EDW-compatible format.
    3. Load data into EDW (e.g., via ETL tool, file transfer, or direct DB connection).
    """
    current_app.logger.info("Starting daily CDP to EDW data push task...")
    try:
        # --- Placeholder for actual EDW push logic ---
        # Example:
        # all_customers = Customer.query.all()
        # all_offers = Offer.query.all()
        # all_events = CustomerEvent.query.all()
        # all_campaigns = Campaign.query.all()
        #
        # transformed_data = transform_for_edw(all_customers, all_offers, all_events, all_campaigns)
        # load_to_edw(transformed_data)
        # --- End Placeholder ---

        current_app.logger.info("Daily CDP to EDW data push task completed. (Placeholder)")
    except Exception as e:
        current_app.logger.error(f"Error during daily CDP to EDW push: {e}", exc_info=True)