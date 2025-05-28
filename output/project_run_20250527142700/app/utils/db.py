from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app

# Assuming db and models are defined in app.extensions and app.models respectively.
# This is a common Flask project structure for managing extensions and models.
from app.extensions import db
from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog

def get_customer_by_identifiers(mobile_number=None, pan=None, aadhaar_ref_number=None, ucid=None, previous_loan_app_number=None):
    """
    Retrieves a customer based on any of the provided unique identifiers.
    Supports FR2 (single profile view) and deduplication (FR3, FR4).
    """
    query_filters = []
    if mobile_number:
        query_filters.append(Customer.mobile_number == mobile_number)
    if pan:
        query_filters.append(Customer.pan == pan)
    if aadhaar_ref_number:
        query_filters.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
    if ucid:
        query_filters.append(Customer.ucid == ucid)
    if previous_loan_app_number:
        query_filters.append(Customer.previous_loan_app_number == previous_loan_app_number)

    if not query_filters:
        current_app.logger.warning("No identifiers provided to get_customer_by_identifiers.")
        return None

    try:
        # Use or_ to find a customer matching any of the provided identifiers
        customer = Customer.query.filter(or_(*query_filters)).first()
        return customer
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error fetching customer by identifiers: {e}")
        db.session.rollback()
        return None

def create_or_update_customer(customer_data):
    """
    Creates a new customer record or updates an existing one based on identifiers.
    Handles data ingestion (FR7, FR9) and admin uploads (FR29).
    Returns the Customer object and a boolean indicating if it was created (True) or updated (False).
    """
    mobile_number = customer_data.get('mobile_number')
    pan = customer_data.get('pan')
    aadhaar_ref_number = customer_data.get('aadhaar_ref_number')
    ucid = customer_data.get('ucid')
    previous_loan_app_number = customer_data.get('previous_loan_app_number')

    customer = get_customer_by_identifiers(
        mobile_number=mobile_number,
        pan=pan,
        aadhaar_ref_number=aadhaar_ref_number,
        ucid=ucid,
        previous_loan_app_number=previous_loan_app_number
    )

    is_created = False
    try:
        if customer:
            # Update existing customer
            current_app.logger.info(f"Updating existing customer: {customer.customer_id}")
            for key, value in customer_data.items():
                # Only update if the value is provided and not None, and attribute exists
                if hasattr(customer, key) and value is not None:
                    setattr(customer, key, value)
            customer.updated_at = datetime.now()
        else:
            # Create new customer
            current_app.logger.info(f"Creating new customer with mobile: {mobile_number}")
            customer = Customer(**customer_data)
            db.session.add(customer)
            is_created = True

        db.session.commit()
        return customer, is_created
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating/updating customer: {e}. Data: {customer_data}")
        # This can happen if two concurrent requests try to create the same customer
        # or if a unique constraint is violated by an update.
        # Attempt to retrieve the customer again if it was a unique constraint violation
        # that happened after the initial check.
        customer = get_customer_by_identifiers(
            mobile_number=mobile_number,
            pan=pan,
            aadhaar_ref_number=aadhaar_ref_number,
            ucid=ucid,
            previous_loan_app_number=previous_loan_app_number
        )
        if customer:
            current_app.logger.info("Customer found after IntegrityError, likely a race condition. Returning existing customer.")
            return customer, False
        else:
            current_app.logger.error("IntegrityError occurred and customer not found after retry. This indicates a deeper issue.")
            raise e # Re-raise if still not found, or handle as a critical error
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error creating/updating customer: {e}. Data: {customer_data}")
        raise e # Re-raise for higher-level handling

def create_offer(customer_id, offer_data):
    """
    Creates a new offer for a given customer.
    """
    try:
        offer = Offer(customer_id=customer_id, **offer_data)
        db.session.add(offer)
        db.session.commit()
        current_app.logger.info(f"Offer created for customer {customer_id}: {offer.offer_id}")
        return offer
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error creating offer for customer {customer_id}: {e}. Data: {offer_data}")
        raise e

def update_offer_status(offer_id, new_status):
    """
    Updates the status of an existing offer.
    Supports FR15, FR37, FR38.
    """
    try:
        offer = Offer.query.get(offer_id)
        if offer:
            offer.offer_status = new_status
            offer.updated_at = datetime.now()
            db.session.commit()
            current_app.logger.info(f"Offer {offer_id} status updated to {new_status}")
            return offer
        else:
            current_app.logger.warning(f"Offer with ID {offer_id} not found for status update.")
            return None
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error updating offer {offer_id} status to {new_status}: {e}")
        raise e

def add_customer_event(customer_id, event_type, event_source, event_details=None):
    """
    Logs a customer event.
    Supports FR21, FR22.
    """
    try:
        event = CustomerEvent(
            customer_id=customer_id,
            event_type=event_type,
            event_source=event_source,
            event_details=event_details if event_details is not None else {}
        )
        db.session.add(event)
        db.session.commit()
        current_app.logger.info(f"Customer event logged for {customer_id}: {event_type} from {event_source}")
        return event
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error adding customer event for {customer_id}: {e}. Event: {event_type}")
        raise e

def log_data_ingestion(file_name, status, uploaded_by, error_details=None):
    """
    Logs the status of a data ingestion process (e.g., file upload).
    Supports FR31, FR32.
    """
    try:
        log_entry = DataIngestionLog(
            file_name=file_name,
            status=status,
            uploaded_by=uploaded_by,
            error_details=error_details
        )
        db.session.add(log_entry)
        db.session.commit()
        current_app.logger.info(f"Data ingestion log created for {file_name} with status {status}. Log ID: {log_entry.log_id}")
        return log_entry
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error logging data ingestion for {file_name}: {e}")
        raise e

def get_customer_profile_with_details(customer_id):
    """
    Retrieves a single customer's profile view with associated offers and application stages.
    Supports FR36.
    """
    try:
        customer = Customer.query.get(customer_id)
        if not customer:
            return None

        customer_data = {
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "pan": customer.pan,
            "aadhaar_ref_number": customer.aadhaar_ref_number,
            "ucid": customer.ucid,
            "previous_loan_app_number": customer.previous_loan_app_number,
            "customer_attributes": customer.customer_attributes,
            "customer_segment": customer.customer_segment,
            "is_dnd": customer.is_dnd,
            "created_at": customer.created_at.isoformat(),
            "updated_at": customer.updated_at.isoformat(),
            "active_offers": [],
            "application_stages": []
        }

        # Get active offers
        active_offers = Offer.query.filter_by(customer_id=customer_id, offer_status='Active').all()
        customer_data["active_offers"] = [
            {
                "offer_id": str(offer.offer_id),
                "offer_type": offer.offer_type,
                "offer_status": offer.offer_status,
                "propensity_flag": offer.propensity_flag,
                "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                "loan_application_number": offer.loan_application_number,
                "attribution_channel": offer.attribution_channel,
                "created_at": offer.created_at.isoformat(),
                "updated_at": offer.updated_at.isoformat()
            } for offer in active_offers
        ]

        # Get application stages (events related to application journey)
        application_stages = CustomerEvent.query.filter(
            CustomerEvent.customer_id == customer_id,
            CustomerEvent.event_type.in_(['APP_STAGE_LOGIN', 'APP_STAGE_BUREAU_CHECK', 'APP_STAGE_OFFER_DETAILS',
                                          'APP_STAGE_EKYC', 'APP_STAGE_BANK_DETAILS', 'APP_STAGE_OTHER_DETAILS',
                                          'APP_STAGE_E_SIGN', 'CONVERSION'])
        ).order_by(CustomerEvent.event_timestamp).all()

        customer_data["application_stages"] = [
            {
                "event_id": str(event.event_id),
                "event_type": event.event_type,
                "event_source": event.event_source,
                "event_timestamp": event.event_timestamp.isoformat(),
                "event_details": event.event_details
            } for event in application_stages
        ]

        return customer_data
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error retrieving customer profile for {customer_id}: {e}")
        db.session.rollback()
        return None

def get_campaign_by_identifier(campaign_unique_identifier):
    """
    Retrieves a campaign by its unique identifier.
    """
    try:
        campaign = Campaign.query.filter_by(campaign_unique_identifier=campaign_unique_identifier).first()
        return campaign
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error fetching campaign by identifier {campaign_unique_identifier}: {e}")
        db.session.rollback()
        return None

def create_or_update_campaign(campaign_data):
    """
    Creates a new campaign record or updates an existing one based on unique identifier.
    Supports FR33, FR34.
    """
    campaign_unique_identifier = campaign_data.get('campaign_unique_identifier')
    if not campaign_unique_identifier:
        current_app.logger.error("Campaign unique identifier is required to create or update a campaign.")
        return None, False

    campaign = get_campaign_by_identifier(campaign_unique_identifier)
    is_created = False

    try:
        if campaign:
            current_app.logger.info(f"Updating existing campaign: {campaign.campaign_id}")
            for key, value in campaign_data.items():
                if hasattr(campaign, key) and value is not None:
                    setattr(campaign, key, value)
            campaign.updated_at = datetime.now()
        else:
            current_app.logger.info(f"Creating new campaign: {campaign_unique_identifier}")
            campaign = Campaign(**campaign_data)
            db.session.add(campaign)
            is_created = True

        db.session.commit()
        return campaign, is_created
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating/updating campaign: {e}. Data: {campaign_data}")
        # Attempt to retrieve the campaign again if it was a unique constraint violation
        # that happened after the initial check.
        campaign = get_campaign_by_identifier(campaign_unique_identifier)
        if campaign:
            current_app.logger.info("Campaign found after IntegrityError, likely a race condition. Returning existing campaign.")
            return campaign, False
        else:
            current_app.logger.error("IntegrityError occurred and campaign not found after retry. This indicates a deeper issue.")
            raise e
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Database error creating/updating campaign: {e}. Data: {campaign_data}")
        raise e