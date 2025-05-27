from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from uuid import UUID
from datetime import datetime, date, timedelta

from app.db import models
from app import schemas

# --- Customer CRUD Operations ---

def get_customer_by_id(db: Session, customer_id: UUID):
    """Retrieves a customer by their UUID."""
    return db.query(models.Customer).filter(models.Customer.customer_id == customer_id).first()

def get_customer_by_identifiers(
    db: Session,
    mobile_number: str = None,
    pan_number: str = None,
    aadhaar_ref_number: str = None,
    ucid_number: str = None,
    previous_loan_app_number: str = None
):
    """
    Retrieves a customer by any of the provided unique identifiers.
    Used for deduplication (FR3, FR5).
    """
    filters = []
    if mobile_number:
        filters.append(models.Customer.mobile_number == mobile_number)
    if pan_number:
        filters.append(models.Customer.pan_number == pan_number)
    if aadhaar_ref_number:
        filters.append(models.Customer.aadhaar_ref_number == aadhaar_ref_number)
    if ucid_number:
        filters.append(models.Customer.ucid_number == ucid_number)
    if previous_loan_app_number:
        filters.append(models.Customer.previous_loan_app_number == previous_loan_app_number)

    if not filters:
        return None # No identifiers provided

    return db.query(models.Customer).filter(or_(*filters)).first()

def create_customer(db: Session, customer: schemas.CustomerCreate):
    """Creates a new customer record."""
    db_customer = models.Customer(
        customer_id=customer.customer_id,
        mobile_number=customer.mobile_number,
        pan_number=customer.pan_number,
        aadhaar_ref_number=customer.aadhaar_ref_number,
        ucid_number=customer.ucid_number,
        previous_loan_app_number=customer.previous_loan_app_number,
        customer_attributes=customer.customer_attributes,
        customer_segments=customer.customer_segments,
        propensity_flag=customer.propensity_flag,
        dnd_status=customer.dnd_status
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

def update_customer(db: Session, customer_id: UUID, customer_update: schemas.CustomerUpdate):
    """Updates an existing customer record."""
    db_customer = db.query(models.Customer).filter(models.Customer.customer_id == customer_id).first()
    if db_customer:
        update_data = customer_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_customer, key, value)
        db_customer.updated_at = datetime.now()
        db.commit()
        db.refresh(db_customer)
    return db_customer

def get_all_customers(db: Session, skip: int = 0, limit: int = 100):
    """Retrieves all customer records with pagination."""
    return db.query(models.Customer).offset(skip).limit(limit).all()

# --- Offer CRUD Operations ---

def get_offer_by_id(db: Session, offer_id: UUID):
    """Retrieves an offer by its UUID."""
    return db.query(models.Offer).filter(models.Offer.offer_id == offer_id).first()

def get_offers_by_customer_id(db: Session, customer_id: UUID):
    """Retrieves all offers associated with a specific customer."""
    return db.query(models.Offer).filter(models.Offer.customer_id == customer_id).all()

def get_active_offers_for_customer(db: Session, customer_id: UUID):
    """Retrieves active offers for a given customer (FR18)."""
    return db.query(models.Offer).filter(
        models.Offer.customer_id == customer_id,
        models.Offer.offer_status == "Active",
        models.Offer.offer_end_date >= date.today() # Ensure offer is not past its end date
    ).all()

def create_offer(db: Session, offer: schemas.OfferCreate):
    """Creates a new offer record."""
    db_offer = models.Offer(
        offer_id=offer.offer_id,
        customer_id=offer.customer_id,
        offer_type=offer.offer_type,
        offer_status=offer.offer_status,
        product_type=offer.product_type,
        offer_details=offer.offer_details,
        offer_start_date=offer.offer_start_date,
        offer_end_date=offer.offer_end_date,
        is_journey_started=offer.is_journey_started,
        loan_application_id=offer.loan_application_id
    )
    db.add(db_offer)
    db.commit()
    db.refresh(db_offer)
    return db_offer

def update_offer(db: Session, offer_id: UUID, offer_update: schemas.OfferUpdate):
    """Updates an existing offer record."""
    db_offer = db.query(models.Offer).filter(models.Offer.offer_id == offer_id).first()
    if db_offer:
        update_data = offer_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_offer, key, value)
        db_offer.updated_at = datetime.now()
        db.commit()
        db.refresh(db_offer)
    return db_offer

def mark_offer_as_expired(db: Session, offer_id: UUID, reason: str = "Offer expired by system"):
    """Marks an offer as 'Expired' (FR51, FR53) and records history."""
    db_offer = get_offer_by_id(db, offer_id)
    if db_offer and db_offer.offer_status != "Expired":
        old_status = db_offer.offer_status
        db_offer.offer_status = "Expired"
        db_offer.updated_at = datetime.now()
        db.commit()
        db.refresh(db_offer)
        create_offer_history_entry(
            db,
            schemas.OfferHistoryCreate(
                offer_id=db_offer.offer_id,
                customer_id=db_offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Expired",
                change_reason=reason,
                snapshot_offer_details=db_offer.offer_details
            )
        )
    return db_offer

def mark_offer_as_duplicate(db: Session, offer_id: UUID, reason: str = "Marked as duplicate due to new offer"):
    """Marks an offer as 'Duplicate' (FR20) and records history."""
    db_offer = get_offer_by_id(db, offer_id)
    if db_offer and db_offer.offer_status != "Duplicate":
        old_status = db_offer.offer_status
        db_offer.offer_status = "Duplicate"
        db_offer.updated_at = datetime.now()
        db.commit()
        db.refresh(db_offer)
        create_offer_history_entry(
            db,
            schemas.OfferHistoryCreate(
                offer_id=db_offer.offer_id,
                customer_id=db_offer.customer_id,
                old_offer_status=old_status,
                new_offer_status="Duplicate",
                change_reason=reason,
                snapshot_offer_details=db_offer.offer_details
            )
        )
    return db_offer

def get_all_offers(db: Session, skip: int = 0, limit: int = 100):
    """Retrieves all offer records with pagination."""
    return db.query(models.Offer).offset(skip).limit(limit).all()

# --- Offer History CRUD Operations ---

def create_offer_history_entry(db: Session, history_entry: schemas.OfferHistoryCreate):
    """Creates a new offer history record (FR23)."""
    db_history = models.OfferHistory(
        history_id=history_entry.history_id,
        offer_id=history_entry.offer_id,
        customer_id=history_entry.customer_id,
        old_offer_status=history_entry.old_offer_status,
        new_offer_status=history_entry.new_offer_status,
        change_reason=history_entry.change_reason,
        snapshot_offer_details=history_entry.snapshot_offer_details
    )
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_offer_history_for_customer(db: Session, customer_id: UUID, months_back: int = 6):
    """
    Retrieves offer history for a customer for a specified number of months (FR23).
    Ordered by most recent.
    """
    six_months_ago = datetime.now() - timedelta(days=months_back * 30) # Approximation
    return db.query(models.OfferHistory).filter(
        models.OfferHistory.customer_id == customer_id,
        models.OfferHistory.change_timestamp >= six_months_ago
    ).order_by(models.OfferHistory.change_timestamp.desc()).all()

# --- Campaign Event CRUD Operations ---

def create_campaign_event(db: Session, event: schemas.CampaignEventCreate):
    """Creates a new campaign event record (FR33)."""
    db_event = models.CampaignEvent(
        event_id=event.event_id,
        customer_id=event.customer_id,
        offer_id=event.offer_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_details=event.event_details,
        event_timestamp=event.event_timestamp
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event

def get_campaign_events_for_customer(db: Session, customer_id: UUID, skip: int = 0, limit: int = 100):
    """Retrieves campaign events for a specific customer."""
    return db.query(models.CampaignEvent).filter(
        models.CampaignEvent.customer_id == customer_id
    ).order_by(models.CampaignEvent.event_timestamp.desc()).offset(skip).limit(limit).all()

# --- Reporting and File Generation Support Functions ---

def get_customers_for_moengage_file(db: Session):
    """
    Retrieves data for generating the Moengage file (FR54).
    This typically involves active, unique customers with relevant offer details.
    The exact columns and filtering might need further refinement based on Moengage template.
    For now, it fetches active offers and their associated customer details.
    """
    # Join customers and offers to get combined data
    return db.query(models.Customer, models.Offer).join(
        models.Offer, models.Customer.customer_id == models.Offer.customer_id
    ).filter(
        models.Offer.offer_status == "Active",
        models.Offer.offer_end_date >= date.today(),
        models.Customer.dnd_status == False # FR34: Avoid DND customers
    ).all()

def get_duplicate_customers_data(db: Session):
    """
    Retrieves data for the Duplicate Data File (FR40).
    This is a simplified approach. True deduplication logic is complex and
    would involve identifying customers with multiple profiles or offers that
    should have been merged/marked duplicate by business rules.
    Here, we'll return customers who have at least one offer explicitly marked as 'Duplicate'.
    """
    return db.query(models.Customer, models.Offer).join(
        models.Offer, models.Customer.customer_id == models.Offer.customer_id
    ).filter(
        models.Offer.offer_status == "Duplicate"
    ).all()

def get_unique_customers_data(db: Session):
    """
    Retrieves data for the Unique Data File (FR41).
    This implies customers who are not marked as part of a duplicate set,
    or who have only 'Active' offers and no 'Duplicate' offers.
    For simplicity, we'll return customers who have at least one 'Active' offer
    and no 'Duplicate' offers associated with them.
    A more robust solution would involve a subquery or `NOT EXISTS` to exclude
    customers with *any* duplicate offers.
    """
    # Get customer_ids that have 'Duplicate' offers
    duplicate_customer_ids = db.query(models.Offer.customer_id).filter(
        models.Offer.offer_status == "Duplicate"
    ).distinct().subquery()

    # Get customers who have 'Active' offers and are NOT in the duplicate_customer_ids list
    return db.query(models.Customer).join(
        models.Offer, models.Customer.customer_id == models.Offer.customer_id
    ).filter(
        models.Offer.offer_status == "Active",
        ~models.Customer.customer_id.in_(duplicate_customer_ids)
    ).distinct().all()


def get_daily_tally_report_data(db: Session, report_date: date):
    """
    Provides daily summary reports for data tally (FR49).
    Counts of unique customers, active offers, new leads, conversions for a given day.
    """
    # Total unique customers (as of report_date)
    total_customers = db.query(models.Customer).count()

    # Active offers (as of report_date)
    active_offers = db.query(models.Offer).filter(
        models.Offer.offer_status == "Active",
        models.Offer.offer_start_date <= report_date,
        models.Offer.offer_end_date >= report_date
    ).count()

    # New leads today (customers created on report_date)
    # Assuming 'created_at' timestamp for customers indicates lead generation
    new_leads_today = db.query(models.Customer).filter(
        func.date(models.Customer.created_at) == report_date
    ).count()

    # Conversions today (campaign events of type 'CONVERSION' on report_date)
    conversions_today = db.query(models.CampaignEvent).filter(
        models.CampaignEvent.event_type == "CONVERSION",
        func.date(models.CampaignEvent.event_timestamp) == report_date
    ).count()

    return {
        "report_date": report_date,
        "total_customers": total_customers,
        "active_offers": active_offers,
        "new_leads_today": new_leads_today,
        "conversions_today": conversions_today
    }

def get_customer_journey_view(db: Session, customer_id: UUID):
    """
    Retrieves a comprehensive view of a customer including their offers,
    attributes, segments, and journey stages (FR50).
    """
    customer = get_customer_by_id(db, customer_id)
    if not customer:
        return None

    offers = get_offers_by_customer_id(db, customer_id)
    campaign_events = get_campaign_events_for_customer(db, customer_id)

    # Determine overall journey status based on offers and events
    journey_status = "No Active Journey"
    if any(offer.is_journey_started for offer in offers):
        journey_status = "Journey Started"
        # More detailed status could be derived from latest LOS events
        los_events = [e for e in campaign_events if e.event_source == "LOS"]
        if los_events:
            latest_los_event = max(los_events, key=lambda e: e.event_timestamp)
            journey_status = f"LOS: {latest_los_event.event_type}"

    return {
        "customer_id": customer.customer_id,
        "mobile_number": customer.mobile_number,
        "pan_number": customer.pan_number,
        "aadhaar_ref_number": customer.aadhaar_ref_number,
        "ucid_number": customer.ucid_number,
        "previous_loan_app_number": customer.previous_loan_app_number,
        "customer_attributes": customer.customer_attributes,
        "customer_segments": customer.customer_segments,
        "propensity_flag": customer.propensity_flag,
        "dnd_status": customer.dnd_status,
        "current_offers": [schemas.Offer.model_validate(offer) for offer in offers if offer.offer_status == "Active"],
        "all_offers": [schemas.Offer.model_validate(offer) for offer in offers],
        "offer_history_summary": [schemas.OfferHistory.model_validate(h) for h in get_offer_history_for_customer(db, customer_id)],
        "campaign_events": [schemas.CampaignEvent.model_validate(e) for e in campaign_events],
        "journey_status": journey_status,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at
    }

def delete_old_data(db: Session, retention_months: int = 3):
    """
    Deletes data older than a specified retention period (FR37).
    This function should be called by a scheduled job.
    """
    # FR37: All data in LTFS Offer CDP shall be maintained for previous 3 months before deletion.
    # FR23: The system shall maintain offer history for the past 6 months for reference purposes.
    cdp_cutoff_date = datetime.now() - timedelta(days=retention_months * 30)
    history_cutoff_date = datetime.now() - timedelta(days=6 * 30)

    # Delete old campaign events
    deleted_events = db.query(models.CampaignEvent).filter(
        models.CampaignEvent.event_timestamp < cdp_cutoff_date
    ).delete(synchronize_session=False)

    # Delete old offer history
    deleted_history = db.query(models.OfferHistory).filter(
        models.OfferHistory.change_timestamp < history_cutoff_date
    ).delete(synchronize_session=False)

    # Delete offers that are 'Expired' or 'Duplicate' and older than CDP retention period
    # Active/Inactive offers should generally not be deleted by this cleanup.
    deleted_offers = db.query(models.Offer).filter(
        models.Offer.updated_at < cdp_cutoff_date,
        or_(models.Offer.offer_status == "Expired", models.Offer.offer_status == "Duplicate")
    ).delete(synchronize_session=False)

    # Customer deletion is complex and should be handled with extreme care.
    # A customer should only be deleted if they have no associated offers (active, expired, or history)
    # and no campaign events within the retention period. This logic is typically
    # handled by a separate, more cautious process or not at all for historical customer data.
    # For now, we will not implement automatic customer deletion here to prevent accidental data loss.

    db.commit()
    return {
        "deleted_events": deleted_events,
        "deleted_history": deleted_history,
        "deleted_offers": deleted_offers
    }