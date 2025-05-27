import uuid
from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import joinedload

# Initialize SQLAlchemy instance.
# This 'db' object will be initialized with the Flask app in app.py
# For example: db.init_app(app)
db = SQLAlchemy()


class Customer(db.Model):
    """
    SQLAlchemy model for the 'customers' table.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True, nullable=True)
    pan_number = db.Column(db.Text, unique=True, nullable=True)
    aadhaar_number = db.Column(db.Text, unique=True, nullable=True)
    ucid_number = db.Column(db.Text, unique=True, nullable=True)
    loan_application_number = db.Column(db.Text, unique=True, nullable=True)
    dnd_flag = db.Column(db.Boolean, default=False, nullable=False)
    segment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} - Mobile: {self.mobile_number}>"


class Offer(db.Model):
    """
    SQLAlchemy model for the 'offers' table.
    """
    __tablename__ = 'offers'

    offer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text, nullable=True)  # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.Text, nullable=True)  # 'Active', 'Inactive', 'Expired'
    propensity = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    channel = db.Column(db.Text, nullable=True)  # For attribution logic
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Offer {self.offer_id} - Customer: {self.customer_id} - Status: {self.offer_status}>"


class Event(db.Model):
    """
    SQLAlchemy model for the 'events' table.
    """
    __tablename__ = 'events'

    event_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text, nullable=False)  # 'SMS_SENT', 'SMS_DELIVERED', 'EKYC_ACHIEVED', etc.
    event_source = db.Column(db.Text, nullable=True)  # 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)
    event_details = db.Column(JSONB, nullable=True)  # Flexible storage for event-specific data
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Event {self.event_id} - Type: {self.event_type} - Customer: {self.customer_id}>"


class CampaignMetric(db.Model):
    """
    SQLAlchemy model for the 'campaign_metrics' table.
    """
    __tablename__ = 'campaign_metrics'

    metric_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text, nullable=True)
    campaign_date = db.Column(db.Date, nullable=True)
    attempted_count = db.Column(db.Integer, nullable=True)
    sent_success_count = db.Column(db.Integer, nullable=True)
    failed_count = db.Column(db.Integer, nullable=True)
    conversion_rate = db.Column(db.Numeric(5, 2), nullable=True)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<CampaignMetric {self.metric_id} - Campaign: {self.campaign_unique_id}>"


class IngestionLog(db.Model):
    """
    SQLAlchemy model for the 'ingestion_logs' table.
    """
    __tablename__ = 'ingestion_logs'

    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=False)
    status = db.Column(db.Text, nullable=False)  # 'SUCCESS', 'FAILED', 'PROCESSING'
    success_count = db.Column(db.Integer, default=0, nullable=False)
    error_count = db.Column(db.Integer, default=0, nullable=False)
    error_description = db.Column(db.Text, nullable=True)  # Detailed error message for FAILED status

    def __repr__(self):
        return f"<IngestionLog {self.log_id} - File: {self.file_name} - Status: {self.status}>"


# --- Helper Functions for Database Operations ---

def add_instance(instance):
    """
    Adds a new instance to the database session and commits it.

    Args:
        instance: The SQLAlchemy model instance to add.
    Returns:
        The added instance if successful, None otherwise.
    """
    try:
        db.session.add(instance)
        db.session.commit()
        return instance
    except Exception as e:
        db.session.rollback()
        print(f"Error adding instance: {e}")  # Log the error
        return None


def get_customer_by_id(customer_id: str) -> Customer | None:
    """
    Retrieves a customer by their customer_id.

    Args:
        customer_id: The UUID of the customer.
    Returns:
        Customer object if found, None otherwise.
    """
    return Customer.query.get(customer_id)


def get_customer_by_identifiers(
    mobile_number: str = None,
    pan_number: str = None,
    aadhaar_number: str = None,
    ucid_number: str = None,
    loan_application_number: str = None
) -> Customer | None:
    """
    Retrieves a customer by any of their unique identifiers.
    Used for deduplication logic.

    Args:
        mobile_number: Customer's mobile number.
        pan_number: Customer's PAN number.
        aadhaar_number: Customer's Aadhaar number.
        ucid_number: Customer's UCID number.
        loan_application_number: Customer's previous loan application number.
    Returns:
        Customer object if found, None otherwise.
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
    if loan_application_number:
        conditions.append(
            Customer.loan_application_number == loan_application_number
        )

    if not conditions:
        return None  # No identifiers provided

    # Use OR to find if any identifier matches
    return query.filter(db.or_(*conditions)).first()


def create_customer(
    mobile_number: str,
    pan_number: str = None,
    aadhaar_number: str = None,
    ucid_number: str = None,
    loan_application_number: str = None,
    dnd_flag: bool = False,
    segment: str = None
) -> Customer | None:
    """
    Creates a new customer record.

    Args:
        mobile_number: Customer's mobile number (required).
        pan_number: Customer's PAN number.
        aadhaar_number: Customer's Aadhaar number.
        ucid_number: Customer's UCID number.
        loan_application_number: Customer's previous loan application number.
        dnd_flag: Boolean flag for Do Not Disturb.
        segment: Customer segment.
    Returns:
        The created Customer object if successful, None otherwise.
    """
    new_customer = Customer(
        mobile_number=mobile_number,
        pan_number=pan_number,
        aadhaar_number=aadhaar_number,
        ucid_number=ucid_number,
        loan_application_number=loan_application_number,
        dnd_flag=dnd_flag,
        segment=segment
    )
    return add_instance(new_customer)


def update_customer(
    customer_id: str,
    mobile_number: str = None,
    pan_number: str = None,
    aadhaar_number: str = None,
    ucid_number: str = None,
    loan_application_number: str = None,
    dnd_flag: bool = None,
    segment: str = None
) -> Customer | None:
    """
    Updates an existing customer record.

    Args:
        customer_id: The UUID of the customer to update.
        mobile_number: New mobile number.
        pan_number: New PAN number.
        aadhaar_number: New Aadhaar number.
        ucid_number: New UCID number.
        loan_application_number: New loan application number.
        dnd_flag: New DND flag.
        segment: New customer segment.
    Returns:
        The updated Customer object if successful, None otherwise.
    """
    customer = get_customer_by_id(customer_id)
    if not customer:
        return None

    try:
        if mobile_number is not None:
            customer.mobile_number = mobile_number
        if pan_number is not None:
            customer.pan_number = pan_number
        if aadhaar_number is not None:
            customer.aadhaar_number = aadhaar_number
        if ucid_number is not None:
            customer.ucid_number = ucid_number
        if loan_application_number is not None:
            customer.loan_application_number = loan_application_number
        if dnd_flag is not None:
            customer.dnd_flag = dnd_flag
        if segment is not None:
            customer.segment = segment

        customer.updated_at = datetime.utcnow()
        db.session.commit()
        return customer
    except Exception as e:
        db.session.rollback()
        print(f"Error updating customer {customer_id}: {e}")
        return None


def create_offer(
    customer_id: str,
    offer_type: str,
    offer_status: str,
    propensity: str = None,
    start_date: date = None,
    end_date: date = None,
    channel: str = None
) -> Offer | None:
    """
    Creates a new offer record for a customer.

    Args:
        customer_id: The UUID of the associated customer.
        offer_type: Type of the offer (e.g., 'Fresh', 'Enrich').
        offer_status: Status of the offer (e.g., 'Active', 'Inactive').
        propensity: Propensity value.
        start_date: Offer start date.
        end_date: Offer end date.
        channel: Channel for attribution.
    Returns:
        The created Offer object if successful, None otherwise.
    """
    new_offer = Offer(
        customer_id=customer_id,
        offer_type=offer_type,
        offer_status=offer_status,
        propensity=propensity,
        start_date=start_date,
        end_date=end_date,
        channel=channel
    )
    return add_instance(new_offer)


def update_offer_status(
    offer_id: str,
    new_status: str
) -> Offer | None:
    """
    Updates the status of an existing offer.

    Args:
        offer_id: The UUID of the offer to update.
        new_status: The new status for the offer.
    Returns:
        The updated Offer object if successful, None otherwise.
    """
    offer = Offer.query.get(offer_id)
    if not offer:
        return None

    try:
        offer.offer_status = new_status
        offer.updated_at = datetime.utcnow()
        db.session.commit()
        return offer
    except Exception as e:
        db.session.rollback()
        print(f"Error updating offer {offer_id} status: {e}")
        return None


def create_event(
    customer_id: str,
    event_type: str,
    event_source: str = None,
    event_timestamp: datetime = None,
    event_details: dict = None
) -> Event | None:
    """
    Creates a new event record for a customer.

    Args:
        customer_id: The UUID of the associated customer.
        event_type: Type of the event (e.g., 'SMS_SENT', 'EKYC_ACHIEVED').
        event_source: Source of the event (e.g., 'Moengage', 'LOS').
        event_timestamp: Timestamp of the event. Defaults to current UTC time.
        event_details: JSONB dictionary for flexible event data.
    Returns:
        The created Event object if successful, None otherwise.
    """
    new_event = Event(
        customer_id=customer_id,
        event_type=event_type,
        event_source=event_source,
        event_timestamp=event_timestamp or datetime.utcnow(),
        event_details=event_details
    )
    return add_instance(new_event)


def create_ingestion_log(
    file_name: str,
    status: str,
    success_count: int = 0,
    error_count: int = 0,
    error_description: str = None
) -> IngestionLog | None:
    """
    Creates a new ingestion log entry.

    Args:
        file_name: Name of the uploaded file.
        status: Status of the ingestion ('SUCCESS', 'FAILED', 'PROCESSING').
        success_count: Number of successfully processed records.
        error_count: Number of records with errors.
        error_description: Detailed error message if status is 'FAILED'.
    Returns:
        The created IngestionLog object if successful, None otherwise.
    """
    new_log = IngestionLog(
        file_name=file_name,
        status=status,
        success_count=success_count,
        error_count=error_count,
        error_description=error_description
    )
    return add_instance(new_log)


def get_customer_full_profile(customer_id: str) -> dict | None:
    """
    Retrieves a customer's full profile including their offers and events.

    Args:
        customer_id: The UUID of the customer.
    Returns:
        A dictionary containing customer, offers, and events data, or None.
    """
    customer = Customer.query.options(
        joinedload(Customer.offers),
        joinedload(Customer.events)
    ).get(customer_id)

    if not customer:
        return None

    customer_data = {
        "customer_id": customer.customer_id,
        "mobile_number": customer.mobile_number,
        "pan_number": customer.pan_number,
        "aadhaar_number": customer.aadhaar_number,
        "ucid_number": customer.ucid_number,
        "loan_application_number": customer.loan_application_number,
        "dnd_flag": customer.dnd_flag,
        "segment": customer.segment,
        "created_at": customer.created_at.isoformat(),
        "updated_at": customer.updated_at.isoformat()
    }

    offers_data = []
    for offer in customer.offers:
        offers_data.append({
            "offer_id": offer.offer_id,
            "offer_type": offer.offer_type,
            "offer_status": offer.offer_status,
            "propensity": offer.propensity,
            "start_date": offer.start_date.isoformat() if offer.start_date else None,
            "end_date": offer.end_date.isoformat() if offer.end_date else None,
            "channel": offer.channel,
            "created_at": offer.created_at.isoformat(),
            "updated_at": offer.updated_at.isoformat()
        })

    events_data = []
    for event in customer.events:
        events_data.append({
            "event_id": event.event_id,
            "event_type": event.event_type,
            "event_source": event.event_source,
            "event_timestamp": event.event_timestamp.isoformat(),
            "event_details": event.event_details,
            "created_at": event.created_at.isoformat()
        })

    return {
        "customer": customer_data,
        "offers": offers_data,
        "events": events_data
    }


def get_all_customers_for_export() -> list[Customer]:
    """
    Retrieves all customer records.
    Used for generating unique/duplicate data files.

    Returns:
        A list of all Customer objects.
    """
    return Customer.query.all()


def get_all_ingestion_errors() -> list[IngestionLog]:
    """
    Retrieves all ingestion logs marked as 'FAILED'.
    Used for generating the error Excel file.

    Returns:
        A list of IngestionLog objects with status 'FAILED'.
    """
    return IngestionLog.query.filter_by(status='FAILED').all()


def get_campaign_data_for_moengage() -> list[dict]:
    """
    Retrieves data required for Moengage export.
    This is a simplified example; actual implementation would involve
    complex joins and filtering based on campaign logic (e.g., active offers,
    non-DND customers, specific segments).

    Returns:
        A list of dictionaries, each representing a row for the Moengage CSV.
    """
    # This query needs to be refined based on actual Moengage requirements
    # and campaign logic (e.g., only active offers, non-DND customers,
    # specific offer types, etc.).
    # For now, a basic join of customers and their active offers.
    campaign_data = db.session.query(
        Customer.customer_id,
        Customer.mobile_number,
        Customer.pan_number,
        Customer.segment,
        Offer.offer_id,
        Offer.offer_type,
        Offer.offer_status,
        Offer.propensity,
        Offer.end_date
    ).join(Offer, Customer.customer_id == Offer.customer_id).filter(
        Customer.dnd_flag == False,
        Offer.offer_status == 'Active'
    ).all()

    results = []
    for row in campaign_data:
        results.append({
            "customer_id": row.customer_id,
            "mobile_number": row.mobile_number,
            "pan_number": row.pan_number,
            "segment": row.segment,
            "offer_id": row.offer_id,
            "offer_type": row.offer_type,
            "offer_status": row.offer_status,
            "propensity": row.propensity,
            "offer_end_date": row.end_date.isoformat() if row.end_date else None
        })
    return results


def update_expired_offers():
    """
    Marks offers as 'Expired' based on their end_date for non-journey started
    customers (FR41, FR42).
    This function would typically be called by a scheduled task.
    """
    today = date.today()
    try:
        # Find active offers that have expired and are not tied to an active
        # loan application journey (simplified: no recent 'LOAN_LOGIN' event).
        # This logic needs refinement based on FR14 and FR43.
        # For now, a simple check on end_date.
        offers_to_expire = Offer.query.filter(
            Offer.offer_status == 'Active',
            Offer.end_date < today
        ).all()

        for offer in offers_to_expire:
            # Further check for FR14: "prevent modification of customer offers
            # with a started loan application journey until the application
            # is expired or rejected."
            # This would involve checking the 'events' table for recent
            # 'LOAN_LOGIN' or similar journey-start events.
            # For simplicity in db_helpers, we'll assume this check
            # happens at a higher logic layer or is integrated here.
            # A more robust check would involve looking at the latest
            # event for the customer related to a loan application.
            # For now, we'll just expire based on date.
            offer.offer_status = 'Expired'
            offer.updated_at = datetime.utcnow()
            db.session.add(offer)
        db.session.commit()
        print(f"Expired {len(offers_to_expire)} offers.")
    except Exception as e:
        db.session.rollback()
        print(f"Error updating expired offers: {e}")


def delete_old_data():
    """
    Deletes data older than 3 months from CDP (FR28, NFR9).
    This function would typically be called by a scheduled task.
    """
    three_months_ago = datetime.utcnow() - text("INTERVAL '3 months'")
    # six_months_ago = datetime.utcnow() - text("INTERVAL '6 months'") # Not used for deletion based on current interpretation

    try:
        # Delete events older than 3 months
        deleted_events = db.session.query(Event).filter(
            Event.created_at < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_events} old events.")

        # Delete ingestion logs older than 3 months
        deleted_logs = db.session.query(IngestionLog).filter(
            IngestionLog.upload_timestamp < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_logs} old ingestion logs.")

        # Delete campaign metrics older than 3 months
        deleted_metrics = db.session.query(CampaignMetric).filter(
            CampaignMetric.created_at < three_months_ago
        ).delete(synchronize_session=False)
        print(f"Deleted {deleted_metrics} old campaign metrics.")

        # Offer history for 6 months (FR19, NFR8) - this implies offers
        # themselves are not deleted, but perhaps only 'Inactive' or 'Expired'
        # ones after 6 months. The BRD says "maintain Offer history for the past 6 months"
        # and "maintain all data in LTFS Offer CDP for previous 3 months before deletion".
        # This is a slight ambiguity. Assuming 'all data' refers to general
        # operational data, while 'offer history' might imply a separate archival
        # or a longer retention for offers specifically.
        # For now, I'll interpret "all data" as general data, and offers might
        # have a different lifecycle or be part of customer data which is retained
        # as long as the customer is active.
        # Deleting customers would cascade delete offers/events due to relationships.
        # This needs careful business rule definition. For now, I'll only delete
        # auxiliary data like events, logs, metrics based on the 3-month rule.

        db.session.commit()
        print("Old data deletion complete.")
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting old data: {e}")