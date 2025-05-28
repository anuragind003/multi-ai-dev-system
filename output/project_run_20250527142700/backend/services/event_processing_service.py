import uuid
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from backend.database import db
from backend.models import Customer, Offer, Event, Campaign

logger = logging.getLogger(__name__)

def process_moengage_event(event_data: dict) -> dict:
    """
    Processes an event received from Moengage.
    Records the event and updates relevant campaign metrics.

    Args:
        event_data (dict): Dictionary containing Moengage event details.
                           Expected keys: 'customer_mobile', 'event_type',
                           'timestamp', 'campaign_id', 'details'.

    Returns:
        dict: A dictionary indicating success or failure.
    """
    customer_mobile = event_data.get('customer_mobile')
    event_type = event_data.get('event_type')
    timestamp_str = event_data.get('timestamp')
    campaign_unique_identifier = event_data.get('campaign_id') # Maps to campaign_unique_identifier in DB
    details = event_data.get('details', {})

    if not all([customer_mobile, event_type, timestamp_str, campaign_unique_identifier]):
        logger.error(f"Missing required Moengage event data: {event_data}")
        return {"status": "error", "message": "Missing required event data"}

    try:
        # Ensure timestamp is timezone-aware. Moengage often sends ISO 8601 with 'Z' for UTC.
        event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)

        customer = Customer.query.filter_by(mobile_number=customer_mobile).first()
        if not customer:
            logger.warning(f"Customer with mobile number {customer_mobile} not found for Moengage event. Skipping event recording.")
            return {"status": "error", "message": f"Customer not found for mobile: {customer_mobile}"}

        campaign = Campaign.query.filter_by(campaign_unique_identifier=campaign_unique_identifier).first()
        if not campaign:
            logger.warning(f"Campaign with ID '{campaign_unique_identifier}' not found for Moengage event. Skipping campaign metric update.")
            # Depending on business logic, a new campaign might be created here.
            # For MVP, assume campaigns are pre-loaded or created by other processes.

        # Record the event
        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer.customer_id,
            # offer_id is optional for Moengage events unless explicitly provided in details
            # and can be linked to a specific offer. For now, link to customer.
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='Moengage',
            event_details=details
        )
        db.session.add(new_event)

        # Update campaign metrics (FR35)
        if campaign:
            # Note: 'attempted_count' is a total count of messages attempted (sent or failed).
            # 'sent_count' is successfully sent. 'failed_count' is failed.
            # 'success_rate' is (sent_count / attempted_count) * 100.
            if event_type == 'SMS_SENT':
                campaign.sent_count += 1
                campaign.attempted_count += 1
            elif event_type == 'SMS_FAILED':
                campaign.failed_count += 1
                campaign.attempted_count += 1
            # Other event types like 'SMS_DELIVERED', 'SMS_CLICKED' might not directly affect these counts
            # but could be used for conversion rates or other metrics if needed.

            # Recalculate success rate
            if campaign.attempted_count > 0:
                campaign.success_rate = (campaign.sent_count / campaign.attempted_count) * 100
            else:
                campaign.success_rate = 0.0
            
            db.session.add(campaign) # Mark for update

        db.session.commit()
        logger.info(f"Moengage event '{event_type}' for customer {customer_mobile} (Campaign: {campaign_unique_identifier}) processed successfully.")
        return {"status": "success", "message": "Moengage event recorded"}

    except ValueError as e:
        db.session.rollback()
        logger.error(f"Timestamp parsing error for Moengage event: {e} - Data: {event_data}")
        return {"status": "error", "message": f"Invalid timestamp format: {e}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error processing Moengage event: {e} - Data: {event_data}", exc_info=True)
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error processing Moengage event: {e} - Data: {event_data}", exc_info=True)
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}


def process_los_event(event_data: dict) -> dict:
    """
    Processes an event received from LOS (Loan Origination System).
    Records the event and updates relevant offer/customer statuses.

    Args:
        event_data (dict): Dictionary containing LOS event details.
                           Expected keys: 'loan_application_number', 'event_type',
                           'timestamp', 'customer_id' (optional), 'details'.

    Returns:
        dict: A dictionary indicating success or failure.
    """
    loan_application_number = event_data.get('loan_application_number')
    event_type = event_data.get('event_type')
    timestamp_str = event_data.get('timestamp')
    # customer_id_from_payload = event_data.get('customer_id') # Optional, can derive from offer
    details = event_data.get('details', {})

    if not all([loan_application_number, event_type, timestamp_str]):
        logger.error(f"Missing required LOS event data: {event_data}")
        return {"status": "error", "message": "Missing required event data"}

    try:
        # Ensure timestamp is timezone-aware.
        event_timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        if event_timestamp.tzinfo is None:
            event_timestamp = event_timestamp.replace(tzinfo=timezone.utc)

        offer = Offer.query.filter_by(loan_application_number=loan_application_number).first()
        if not offer:
            logger.warning(f"Offer with LAN '{loan_application_number}' not found for LOS event. Skipping event recording.")
            return {"status": "error", "message": f"Offer not found for LAN: {loan_application_number}"}

        customer = Customer.query.get(offer.customer_id)
        if not customer:
            logger.error(f"Customer with ID '{offer.customer_id}' linked to offer LAN '{loan_application_number}' not found. Data inconsistency.")
            return {"status": "error", "message": "Associated customer not found."}

        # Record the event
        new_event = Event(
            event_id=uuid.uuid4(),
            customer_id=customer.customer_id,
            offer_id=offer.offer_id,
            event_type=event_type,
            event_timestamp=event_timestamp,
            source_system='LOS',
            event_details=details
        )
        db.session.add(new_event)

        # Update offer status based on LOS event (FR26, FR27)
        # Define mapping for journey stages and conversion/rejection events
        # These event types should align with what LOS sends.
        journey_start_events = ['LOGIN', 'BUREAU_CHECK', 'OFFER_DETAILS', 'EKYC',
                                'BANK_DETAILS', 'OTHER_DETAILS', 'E_SIGN']
        conversion_events = ['EKYC_ACHIEVED', 'DISBURSEMENT']
        rejection_events = ['APPLICATION_REJECTED', 'APPLICATION_CANCELLED'] # Assuming these exist from LOS

        if event_type in conversion_events:
            offer.offer_status = 'Converted'
            logger.info(f"Offer {offer.offer_id} (LAN: {loan_application_number}) status updated to 'Converted' due to LOS event: {event_type}.")
            # FR35: Campaign conversion rate update. This would require linking the offer back to a campaign.
            # For MVP, this might be a separate process or require campaign_id on the offer model.
            # If offer.campaign_id exists and campaign can be found:
            # campaign = Campaign.query.get(offer.campaign_id)
            # if campaign:
            #     campaign.conversion_count += 1 # Assuming a new field for conversion count
            #     # Recalculate conversion rate based on attempted/sent count
            #     if campaign.attempted_count > 0:
            #         campaign.conversion_rate = (campaign.conversion_count / campaign.attempted_count) * 100
            #     db.session.add(campaign)

        elif event_type in journey_start_events:
            # Only update to 'Journey Started' if it's not already 'Converted', 'Expired', or 'Rejected'
            if offer.offer_status not in ['Converted', 'Expired', 'Rejected']:
                offer.offer_status = 'Journey Started'
                logger.info(f"Offer {offer.offer_id} (LAN: {loan_application_number}) status updated to 'Journey Started' due to LOS event: {event_type}.")
        
        elif event_type in rejection_events:
            offer.offer_status = 'Rejected'
            logger.info(f"Offer {offer.offer_id} (LAN: {loan_application_number}) status updated to 'Rejected' due to LOS event: {event_type}.")

        db.session.add(offer) # Mark for update

        db.session.commit()
        logger.info(f"LOS event '{event_type}' for LAN {loan_application_number} processed successfully.")
        return {"status": "success", "message": "LOS event recorded and offer status updated"}

    except ValueError as e:
        db.session.rollback()
        logger.error(f"Timestamp parsing error for LOS event: {e} - Data: {event_data}")
        return {"status": "error", "message": f"Invalid timestamp format: {e}"}
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error processing LOS event: {e} - Data: {event_data}", exc_info=True)
        return {"status": "error", "message": f"Database error: {e}"}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error processing LOS event: {e} - Data: {event_data}", exc_info=True)
        return {"status": "error", "message": f"An unexpected error occurred: {e}"}