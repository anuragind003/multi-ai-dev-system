from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

# Assuming db and models are defined in app.extensions and app.models respectively
from app.extensions import db
from app.models import Customer, Offer

def generate_and_push_reverse_feed():
    """
    Task to generate and push a daily/hourly reverse feed to Offermart.
    This includes Offer data updates from E-aggregators and other relevant updates.
    (FR8: Push daily reverse feed to Offermart, including Offer data updates from E-aggregators)
    (NFR6: Handle hourly/daily reverse feeds from CDP to Offermart)
    """
    logger = current_app.logger
    logger.info("Starting reverse feed generation and push task...")

    # Define the time window for identifying updated offers.
    # For a daily feed, we look back 24 hours. For an hourly feed, it would be 1 hour.
    # This can be made configurable or dynamic based on the last successful run timestamp
    # in a more robust production setup.
    time_window_start = datetime.utcnow() - timedelta(hours=24)

    try:
        # Query for offers that have been updated within the defined time window.
        # Join with the Customer table to retrieve relevant customer identifiers
        # that Offermart might need to match and update its records.
        updated_offers_data = db.session.query(
            Offer.offer_id,
            Offer.customer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.propensity_flag,
            Offer.offer_start_date,
            Offer.offer_end_date,
            Offer.loan_application_number,
            Offer.attribution_channel,
            Offer.updated_at,
            Customer.mobile_number,
            Customer.pan,
            Customer.aadhaar_ref_number,
            Customer.ucid
        ).join(Customer, Offer.customer_id == Customer.customer_id)\
        .filter(Offer.updated_at >= time_window_start)\
        .all()

        if not updated_offers_data:
            logger.info("No updated offer data found for reverse feed in the last 24 hours.")
            return

        # Prepare data for the feed.
        # In a real-world scenario, this list of dictionaries would then be
        # converted into a specific format (e.g., CSV, JSON) and sent
        # to Offermart via an agreed-upon method (e.g., SFTP, API call, message queue).
        feed_records = []
        for offer, customer in updated_offers_data:
            feed_records.append({
                "offer_id": str(offer.offer_id),
                "customer_id": str(offer.customer_id),
                "mobile_number": customer.mobile_number,
                "pan": customer.pan,
                "aadhaar_ref_number": customer.aadhaar_ref_number,
                "ucid": customer.ucid,
                "offer_type": offer.offer_type,
                "offer_status": offer.offer_status,
                "propensity_flag": offer.propensity_flag,
                "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                "loan_application_number": offer.loan_application_number,
                "attribution_channel": offer.attribution_channel,
                "cdp_updated_at": offer.updated_at.isoformat()
            })

        logger.info(f"Found {len(feed_records)} updated offers for reverse feed.")
        # Log a sample of the data for debugging purposes, avoid logging all data in production
        if feed_records:
            logger.debug(f"Sample reverse feed data (first 5 entries): {feed_records[:5]}")

        # --- Simulate pushing data to Offermart ---
        # This section would contain the actual integration logic.
        # For example:
        # 1. Generate a CSV file from `feed_records` using pandas or csv module.
        # 2. Write the file to a designated SFTP server or shared network drive.
        # 3. Make an HTTP POST request to an Offermart API endpoint with the data.
        # 4. Publish the data to a Kafka topic or other message queue.

        # For this implementation, we will simply log the action.
        logger.info("Simulating push of reverse feed data to Offermart...")
        # Example of how you might generate a CSV (requires pandas):
        # import pandas as pd
        # import io
        # df = pd.DataFrame(feed_records)
        # output_buffer = io.StringIO()
        # df.to_csv(output_buffer, index=False)
        # csv_content = output_buffer.getvalue()
        # logger.debug(f"Generated CSV content (first 500 chars): {csv_content[:500]}...")
        # # Then, `csv_content` would be sent to Offermart.

        logger.info("Reverse feed generation and push task completed successfully.")

    except SQLAlchemyError as e:
        # Rollback in case of database errors, though this is a read-only task
        # it's good practice if any writes were implicitly part of a larger transaction.
        db.session.rollback()
        logger.error(f"Database error during reverse feed generation: {e}")
        # Depending on requirements, you might want to re-raise the exception
        # or send an alert to a monitoring system.
    except Exception as e:
        logger.error(f"An unexpected error occurred during reverse feed generation: {e}")
        # Re-raise or alert as appropriate for unhandled exceptions.