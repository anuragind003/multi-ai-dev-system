from datetime import datetime, timedelta
import uuid
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_

# Assuming 'db' is initialized in backend/__init__.py and models are defined in backend/models.py
from backend import db
from backend.models import Customer, Offer, OfferHistory, Event, Campaign, DataError

def get_customer_by_identifiers(mobile_number=None, pan_number=None, aadhaar_number=None, ucid_number=None):
    """
    Retrieves a customer by any of the unique identifiers.
    Used for deduplication checks (FR3).
    """
    query = Customer.query
    conditions = []
    if mobile_number:
        conditions.append(Customer.mobile_number == mobile_number)
    if pan_number:
        conditions.append(Customer.pan_number == pan_number)
    if aadhaar_number:
        conditions.append(Customer.aadhaar_number == aadhaar_number)
    if ucid_number:
        conditions.append(Customer.ucid_number == ucid_number)

    if not conditions:
        return None

    return query.filter(or_(*conditions)).first()

def create_or_update_customer(customer_data):
    """
    Creates a new customer or updates an existing one based on identifiers.
    Returns the customer object and a boolean indicating if it was new.
    """
    mobile = customer_data.get('mobile_number')
    pan = customer_data.get('pan_number')
    aadhaar = customer_data.get('aadhaar_number')
    ucid = customer_data.get('ucid_number')

    customer = get_customer_by_identifiers(mobile, pan, aadhaar, ucid)
    is_new_customer = False

    try:
        if customer:
            # Update existing customer
            for key, value in customer_data.items():
                if hasattr(customer, key) and value is not None:
                    setattr(customer, key, value)
            customer.updated_at = datetime.now()
        else:
            # Create new customer
            customer_id = customer_data.get('customer_id', str(uuid.uuid4()))
            customer = Customer(customer_id=customer_id, **customer_data)
            db.session.add(customer)
            is_new_customer = True
        db.session.commit()
        return customer, is_new_customer
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error creating/updating customer: {e}")
        raise

def create_offer(offer_data):
    """
    Creates a new offer record.
    """
    try:
        offer_id = offer_data.get('offer_id', str(uuid.uuid4()))
        offer = Offer(offer_id=offer_id, **offer_data)
        db.session.add(offer)
        db.session.commit()
        return offer
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error creating offer: {e}")
        raise

def update_offer(offer_id, update_data):
    """
    Updates an existing offer record (FR7, FR16).
    Records status changes in offer_history.
    """
    try:
        offer = Offer.query.get(offer_id)
        if not offer:
            return None

        old_status = offer.offer_status
        for key, value in update_data.items():
            if hasattr(offer, key) and value is not None:
                setattr(offer, key, value)
        offer.updated_at = datetime.now()

        # Record status change in offer_history if status changed
        if 'offer_status' in update_data and old_status != update_data['offer_status']:
            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status=update_data['offer_status'],
                change_reason=update_data.get('change_reason', 'Status updated via API/process')
            )
            db.session.add(history_entry)

        db.session.commit()
        return offer
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error updating offer {offer_id}: {e}")
        raise

def mark_offer_as_duplicate(offer_id, original_offer_id):
    """
    Marks an offer as a duplicate and links it to the original offer (FR18).
    """
    try:
        offer = Offer.query.get(offer_id)
        if offer:
            old_status = offer.offer_status
            offer.is_duplicate = True
            offer.offer_status = 'Inactive' # Or 'Duplicate' if that's a defined status
            offer.original_offer_id = original_offer_id
            offer.updated_at = datetime.now()
            
            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status='Inactive', # Or 'Duplicate'
                change_reason='Marked as duplicate'
            )
            db.session.add(history_entry)
            db.session.commit()
            return True
        return False
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error marking offer {offer_id} as duplicate: {e}")
        raise

def expire_offers_by_lan_validity():
    """
    Marks offers as expired if their associated Loan Application Number (LAN) validity is over (FR36).
    This function is intended to be called by a scheduled job.
    """
    try:
        offers_to_expire = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.loan_application_number.isnot(None),
            Offer.valid_until < datetime.now()
        ).all()

        updated_count = 0
        for offer in offers_to_expire:
            old_status = offer.offer_status
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.now()
            history_entry = OfferHistory(
                offer_id=offer.offer_id,
                old_status=old_status,
                new_status='Expired',
                change_reason='LAN validity expired'
            )
            db.session.add(history_entry)
            updated_count += 1

        db.session.commit()
        return updated_count
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error expiring offers by LAN validity: {e}")
        raise

def cleanup_old_data():
    """
    Cleans up old data based on retention policies (FR20, FR29, NFR10, NFR11).
    This function is intended to be called by a scheduled job.
    """
    try:
        offer_history_retention_months = 6
        main_data_retention_months = 3

        offer_history_cutoff = datetime.now() - timedelta(days=offer_history_retention_months * 30)
        main_data_cutoff = datetime.now() - timedelta(days=main_data_retention_months * 30)

        deleted_history_count = OfferHistory.query.filter(
            OfferHistory.status_change_date < offer_history_cutoff
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_history_count} old offer history records.")

        deleted_event_count = Event.query.filter(
            Event.event_timestamp < main_data_cutoff
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_event_count} old event records.")

        # Delete inactive/expired offers older than main_data_cutoff
        deleted_offer_count = Offer.query.filter(
            Offer.created_at < main_data_cutoff,
            Offer.offer_status.in_(['Inactive', 'Expired'])
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_offer_count} old inactive/expired offer records.")

        # Customer deletion logic is complex and should be handled with extreme care,
        # typically only if a customer has no active offers and no recent activity.
        # For safety, direct customer deletion is omitted here.
        # A more robust solution would involve archiving or soft-deleting.

        db.session.commit()
        return {
            "deleted_history": deleted_history_count,
            "deleted_events": deleted_event_count,
            "deleted_offers": deleted_offer_count
        }
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error during data cleanup: {e}")
        raise

def get_dnd_customers_mobile_numbers():
    """
    Retrieves mobile numbers of customers marked as DND (FR24).
    """
    try:
        dnd_mobiles = db.session.query(Customer.mobile_number).filter(Customer.is_dnd == True).all()
        return [mobile for mobile, in dnd_mobiles]
    except SQLAlchemyError as e:
        print(f"Error retrieving DND customer mobile numbers: {e}")
        raise

def get_eligible_offers_for_moengage_export():
    """
    Retrieves active, non-duplicate offers for non-DND customers, suitable for Moengage export (FR30, FR24).
    """
    try:
        eligible_offers = db.session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.segment,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.propensity,
            Offer.loan_application_number,
            Offer.valid_until,
            Offer.source_system,
            Offer.channel
        ).join(Offer, Customer.customer_id == Offer.customer_id).filter(
            Customer.is_dnd == False,
            Offer.offer_status == 'Active',
            Offer.is_duplicate == False
        ).all()
        return eligible_offers
    except SQLAlchemyError as e:
        print(f"Error retrieving eligible offers for Moengage export: {e}")
        raise

def get_duplicate_customer_data():
    """
    Retrieves data for offers identified as duplicates (FR31).
    """
    try:
        duplicate_offers = db.session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Offer.offer_id,
            Offer.source_offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.is_duplicate,
            Offer.original_offer_id,
            Offer.created_at
        ).join(Customer, Customer.customer_id == Offer.customer_id).filter(
            Offer.is_duplicate == True
        ).all()
        return duplicate_offers
    except SQLAlchemyError as e:
        print(f"Error retrieving duplicate customer data: {e}")
        raise

def get_unique_customer_data():
    """
    Retrieves data for unique customer profiles with their active, non-duplicate offers (FR32).
    """
    try:
        unique_customers_with_offers = db.session.query(
            Customer.customer_id,
            Customer.mobile_number,
            Customer.pan_number,
            Customer.aadhaar_number,
            Customer.ucid_number,
            Customer.segment,
            Offer.offer_id,
            Offer.offer_type,
            Offer.offer_status,
            Offer.propensity,
            Offer.valid_until
        ).join(Offer, Customer.customer_id == Offer.customer_id).filter(
            Customer.is_dnd == False,
            Offer.offer_status == 'Active',
            Offer.is_duplicate == False
        ).distinct(Customer.customer_id).all()
        return unique_customers_with_offers
    except SQLAlchemyError as e:
        print(f"Error retrieving unique customer data: {e}")
        raise

def get_data_errors(start_date=None, end_date=None, source_system=None):
    """
    Retrieves data validation errors for reporting (FR33).
    Assumes a 'DataError' model exists in backend.models.
    """
    query = DataError.query
    if start_date:
        query = query.filter(DataError.created_at >= start_date)
    if end_date:
        query = query.filter(DataError.created_at <= end_date)
    if source_system:
        query = query.filter(DataError.source_system == source_system)

    try:
        errors = query.order_by(DataError.created_at.desc()).all()
        return errors
    except SQLAlchemyError as e:
        print(f"Error retrieving data errors: {e}")
        raise

def add_event(event_data):
    """
    Adds a new event record (FR23, FR25, FR26, FR27).
    """
    try:
        event_id = event_data.get('event_id', str(uuid.uuid4()))
        event = Event(event_id=event_id, **event_data)
        db.session.add(event)
        db.session.commit()
        return event
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error adding event: {e}")
        raise

def update_campaign_metrics(campaign_unique_identifier, metrics_data):
    """
    Updates campaign metrics (FR35). Creates a new campaign entry if it doesn't exist.
    """
    try:
        campaign = Campaign.query.filter_by(campaign_unique_identifier=campaign_unique_identifier).first()
        if not campaign:
            campaign_id = str(uuid.uuid4())
            campaign_name = metrics_data.get('campaign_name', f"Campaign {campaign_unique_identifier}")
            campaign_date = metrics_data.get('campaign_date', datetime.now().date())
            campaign = Campaign(
                campaign_id=campaign_id,
                campaign_name=campaign_name,
                campaign_date=campaign_date,
                campaign_unique_identifier=campaign_unique_identifier
            )
            db.session.add(campaign)

        for key, value in metrics_data.items():
            if hasattr(campaign, key) and value is not None:
                setattr(campaign, key, value)
        campaign.updated_at = datetime.now()

        db.session.commit()
        return campaign
    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Error updating campaign metrics for {campaign_unique_identifier}: {e}")
        raise