from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import or_, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import JSONB

# Assuming db and models are defined in app.extensions and app.models respectively
# This is a common Flask project structure.
from app.extensions import db
from app.models import Offer, CustomerEvent

def mark_offers_expired():
    """
    Task to implement offer expiry logic based on defined business rules (FR13, FR15, FR37, FR38).
    This task should be scheduled to run periodically (e.g., daily).

    Logic:
    1. Offers for non-journey started customers (FR37):
       Mark as 'Expired' if 'Active', 'loan_application_number' is NULL,
       and 'offer_end_date' is today or in the past.
    2. Offers with started loan application journeys (FR38):
       Mark as 'Expired' if 'Active', 'loan_application_number' is NOT NULL,
       and the associated loan application has reached a terminal status ('REJECTED' or 'EXPIRED')
       as indicated by a 'LOS' customer event.
    """
    logger = current_app.logger
    logger.info("Starting offer expiry task...")
    
    # Use UTC for consistency with database timestamps
    current_utc_date = datetime.utcnow().date() 

    try:
        # --- Rule 1: Offers for non-journey started customers (FR37) ---
        # Mark offers as 'Expired' if they are 'Active', have no loan_application_number,
        # and their offer_end_date is today or in the past.
        
        offers_to_expire_by_date = db.session.query(Offer).filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.is_(None), # No journey started
            Offer.offer_end_date <= current_utc_date
        ).all()

        count_expired_by_date = 0
        for offer in offers_to_expire_by_date:
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            count_expired_by_date += 1
        
        if count_expired_by_date > 0:
            logger.info(f"Expired {count_expired_by_date} offers based on offer_end_date for non-journey customers.")
        else:
            logger.info("No offers expired based on offer_end_date for non-journey customers.")

        # --- Rule 2: Offers with started loan application journeys (FR38) ---
        # Mark offers as 'Expired' if they are 'Active', have a loan_application_number,
        # and the associated loan application journey has reached a terminal status (e.g., 'REJECTED', 'EXPIRED').
        # Assumption: CustomerEvent.event_details contains {"loan_application_number": "...", "application_status": "REJECTED/EXPIRED"}
        # and event_source is 'LOS'.
        
        # Find distinct loan_application_numbers that have a terminal event
        terminal_lan_events = db.session.query(CustomerEvent.event_details['loan_application_number'].astext).filter(
            CustomerEvent.event_source == 'LOS', # Assuming LOS provides final application status
            CustomerEvent.event_details.has_key('loan_application_number'),
            CustomerEvent.event_details['application_status'].astext.in_(['REJECTED', 'EXPIRED'])
        ).distinct().all()

        # Extract LANs from the query result, filtering out any potential None or empty strings
        terminal_lans = [lan[0] for lan in terminal_lan_events if lan[0]] 

        count_expired_by_lan_status = 0
        if terminal_lans:
            offers_to_expire_by_lan_status = db.session.query(Offer).filter(
                Offer.offer_status == 'Active',
                Offer.loan_application_number.isnot(None), # Journey started
                Offer.loan_application_number.in_(terminal_lans)
            ).all()

            for offer in offers_to_expire_by_lan_status:
                offer.offer_status = 'Expired'
                offer.updated_at = datetime.utcnow()
                count_expired_by_lan_status += 1
            
            logger.info(f"Expired {count_expired_by_lan_status} offers based on loan application status (REJECTED/EXPIRED).")
        else:
            logger.info("No offers expired based on loan application status.")

        db.session.commit()
        logger.info("Offer expiry task completed successfully.")

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error during offer expiry task: {e}")
        # Re-raise the exception to allow scheduler/caller to handle it
        raise
    except Exception as e:
        db.session.rollback() # Ensure rollback on other unexpected errors too
        logger.error(f"An unexpected error occurred during offer expiry task: {e}")
        # Re-raise the exception
        raise