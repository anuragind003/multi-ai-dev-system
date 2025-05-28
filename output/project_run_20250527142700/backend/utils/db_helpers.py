import uuid
from datetime import datetime, timezone, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import JSONB

db = SQLAlchemy()

def init_db(app):
    """Initializes the SQLAlchemy object with the Flask app."""
    db.init_app(app)
    with app.app_context():
        # This will create tables if they don't exist.
        # In a production environment, migrations (e.g., Flask-Migrate) are preferred.
        db.create_all()

# --- Database Models ---

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=True)
    pan_number = db.Column(db.String(10), unique=True, nullable=True)
    aadhaar_number = db.Column(db.String(12), unique=True, nullable=True)
    ucid_number = db.Column(db.String(50), unique=True, nullable=True)
    customer_360_id = db.Column(db.String(50), nullable=True) # For integration with Customer 360
    is_dnd = db.Column(db.Boolean, default=False)
    segment = db.Column(db.String(50), nullable=True) # C1-C8, etc.
    attributes = db.Column(JSONB, nullable=True) # For other customer attributes
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    offers = db.relationship('Offer', backref='customer', lazy=True)
    events = db.relationship('Event', backref='customer', lazy=True)

    def __repr__(self):
        return f"<Customer {self.customer_id} - Mobile: {self.mobile_number}>"

class Offer(db.Model):
    __tablename__ = 'offers'
    offer_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    source_offer_id = db.Column(db.String(100), nullable=True) # Original ID from Offermart/E-aggregator
    offer_type = db.Column(db.String(50), nullable=True) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(50), default='Active') # 'Active', 'Inactive', 'Expired'
    propensity = db.Column(db.String(50), nullable=True)
    loan_application_number = db.Column(db.String(100), nullable=True) # LAN
    valid_until = db.Column(db.TIMESTAMP(timezone=True), nullable=True)
    source_system = db.Column(db.String(50), nullable=True) # 'Offermart', 'E-aggregator'
    channel = db.Column(db.String(50), nullable=True) # For attribution
    is_duplicate = db.Column(db.Boolean, default=False) # Flagged by deduplication
    original_offer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=True) # Points to the offer it duplicated/enriched
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    offer_history = db.relationship('OfferHistory', backref='offer', lazy=True)
    events = db.relationship('Event', backref='offer', lazy=True)

    def __repr__(self):
        return f"<Offer {self.offer_id} - Customer: {self.customer_id} - Status: {self.offer_status}>"

class OfferHistory(db.Model):
    __tablename__ = 'offer_history'
    history_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=False)
    status_change_date = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    old_status = db.Column(db.String(50), nullable=True)
    new_status = db.Column(db.String(50), nullable=False)
    change_reason = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<OfferHistory {self.history_id} - Offer: {self.offer_id} - {self.old_status} -> {self.new_status}>"

class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=True)
    offer_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('offers.offer_id'), nullable=True)
    event_type = db.Column(db.String(100), nullable=False) # SMS_SENT, EKYC_ACHIEVED, JOURNEY_LOGIN, etc.
    event_timestamp = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    source_system = db.Column(db.String(50), nullable=False) # Moengage, LOS
    event_details = db.Column(JSONB, nullable=True) # Raw event payload

    def __repr__(self):
        return f"<Event {self.event_id} - Type: {self.event_type} - Source: {self.source_system}>"

class Campaign(db.Model):
    __tablename__ = 'campaigns'
    campaign_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date, nullable=False)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    attempted_count = db.Column(db.Integer, default=0)
    sent_count = db.Column(db.Integer, default=0)
    failed_count = db.Column(db.Integer, default=0)
    success_rate = db.Column(db.Numeric(5,2), default=0.0)
    conversion_rate = db.Column(db.Numeric(5,2), default=0.0)
    created_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Campaign {self.campaign_id} - Name: {self.campaign_name}>"

class DataError(db.Model):
    __tablename__ = 'data_errors'
    error_id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_system = db.Column(db.String(50), nullable=False)
    record_identifier = db.Column(db.Text, nullable=True) # e.g., original row data, or a key
    error_message = db.Column(db.Text, nullable=False)
    error_details = db.Column(JSONB, nullable=True)
    timestamp = db.Column(db.TIMESTAMP(timezone=True), default=datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DataError {self.error_id} - Source: {self.source_system} - Message: {self.error_message}>"

# --- Helper Functions for DB Operations ---

def add_or_update_customer(data):
    """
    Adds a new customer or updates an existing one based on unique identifiers.
    Returns the Customer object and a boolean indicating if it was created (True) or updated (False).
    FR1, FR3: Deduplication based on Mobile, Pan, Aadhaar, UCID.
    """
    mobile = data.get('mobile_number')
    pan = data.get('pan_number')
    aadhaar = data.get('aadhaar_number')
    ucid = data.get('ucid_number')

    customer = get_customer_by_identifiers(mobile, pan, aadhaar, ucid)

    if customer:
        # Update existing customer
        for key, value in data.items():
            if hasattr(customer, key) and value is not None:
                setattr(customer, key, value)
        db.session.add(customer)
        db.session.commit()
        return customer, False
    else:
        # Create new customer
        new_customer = Customer(**data)
        db.session.add(new_customer)
        db.session.commit()
        return new_customer, True

def get_customer_by_identifiers(mobile=None, pan=None, aadhaar=None, ucid=None):
    """
    Retrieves a customer by any of their unique identifiers.
    Used for deduplication checks (FR3).
    """
    filters = []
    if mobile:
        filters.append(Customer.mobile_number == mobile)
    if pan:
        filters.append(Customer.pan_number == pan)
    if aadhaar:
        filters.append(Customer.aadhaar_number == aadhaar)
    if ucid:
        filters.append(Customer.ucid_number == ucid)

    if not filters:
        return None

    # Find if any existing customer matches any of the provided identifiers
    # This is a basic OR match. Complex deduplication logic (FR4, FR5, FR6)
    # would be handled by a dedicated service using these lookup functions.
    customer = Customer.query.filter(db.or_(*filters)).first()
    return customer

def get_customer_by_id(customer_id):
    """Retrieves a customer by their customer_id."""
    return Customer.query.get(customer_id)

def add_offer(data):
    """Adds a new offer to the database."""
    try:
        new_offer = Offer(**data)
        db.session.add(new_offer)
        db.session.commit()
        # Log initial offer status to history (FR20)
        add_offer_history(new_offer.offer_id, None, new_offer.offer_status, "Initial offer creation")
        return new_offer
    except Exception as e:
        db.session.rollback()
        print(f"Error adding offer: {e}")
        raise

def update_offer_status(offer_id, new_status, reason="Status updated"):
    """
    Updates an offer's status and logs the change to offer_history.
    FR16: Maintain flags for Offer statuses: Active, Inactive, and Expired.
    FR36: Mark offers as expired if LAN validity is over for journey-started customers.
    """
    offer = Offer.query.get(offer_id)
    if offer:
        old_status = offer.offer_status
        if old_status != new_status:
            offer.offer_status = new_status
            db.session.add(offer)
            db.session.commit()
            add_offer_history(offer_id, old_status, new_status, reason)
            return True
    return False

def add_offer_history(offer_id, old_status, new_status, reason):
    """Adds an entry to the offer_history table (FR20, NFR10)."""
    try:
        history_entry = OfferHistory(
            offer_id=offer_id,
            old_status=old_status,
            new_status=new_status,
            change_reason=reason
        )
        db.session.add(history_entry)
        db.session.commit()
        return history_entry
    except Exception as e:
        db.session.rollback()
        print(f"Error adding offer history: {e}")
        raise

def get_active_offers_for_customer(customer_id):
    """Retrieves all active offers for a given customer."""
    return Offer.query.filter_by(customer_id=customer_id, offer_status='Active').all()

def add_event(data):
    """Adds a new event to the database (FR23, FR25, FR26, FR27)."""
    try:
        new_event = Event(**data)
        db.session.add(new_event)
        db.session.commit()
        return new_event
    except Exception as e:
        db.session.rollback()
        print(f"Error adding event: {e}")
        raise

def add_campaign(data):
    """Adds a new campaign to the database (FR34, FR35)."""
    try:
        new_campaign = Campaign(**data)
        db.session.add(new_campaign)
        db.session.commit()
        return new_campaign
    except Exception as e:
        db.session.rollback()
        print(f"Error adding campaign: {e}")
        raise

def get_campaign_by_identifier(identifier):
    """Retrieves a campaign by its unique identifier."""
    return Campaign.query.filter_by(campaign_unique_identifier=identifier).first()

def update_campaign_metrics(campaign_id, attempted_delta=0, sent_delta=0, failed_delta=0, conversion_rate=None):
    """Updates campaign metrics (FR35)."""
    campaign = Campaign.query.get(campaign_id)
    if campaign:
        campaign.attempted_count += attempted_delta
        campaign.sent_count += sent_delta
        campaign.failed_count += failed_delta
        
        if campaign.attempted_count > 0:
            campaign.success_rate = (campaign.sent_count / campaign.attempted_count) * 100
        else:
            campaign.success_rate = 0.0
        
        if conversion_rate is not None:
            campaign.conversion_rate = conversion_rate # This might be updated separately or calculated
        
        db.session.add(campaign)
        db.session.commit()
        return True
    return False

def get_customers_for_moengage_export():
    """
    Generates data for Moengage-formatted CSV file (FR30).
    Excludes DND customers (FR24).
    Includes active offers.
    """
    # Subquery to get the latest active offer for each customer based on creation time
    # This assumes the "latest" active offer is the one most recently created.
    latest_active_offer_subquery = db.session.query(
        Offer.customer_id,
        func.max(Offer.created_at).label('latest_offer_created_at')
    ).filter(Offer.offer_status == 'Active').group_by(Offer.customer_id).subquery()

    # Join Customer with their latest active offer, excluding DND customers
    customers_with_offers = db.session.query(Customer, Offer).join(
        latest_active_offer_subquery,
        Customer.customer_id == latest_active_offer_subquery.c.customer_id
    ).join(
        Offer,
        db.and_(
            Offer.customer_id == latest_active_offer_subquery.c.customer_id,
            Offer.created_at == latest_active_offer_subquery.c.latest_offer_created_at,
            Offer.offer_status == 'Active'
        )
    ).filter(Customer.is_dnd == False).all()

    results = []
    for customer, offer in customers_with_offers:
        results.append({
            'customer_id': str(customer.customer_id),
            'mobile_number': customer.mobile_number,
            'pan_number': customer.pan_number,
            'aadhaar_number': customer.aadhaar_number,
            'ucid_number': customer.ucid_number,
            'segment': customer.segment,
            'offer_id': str(offer.offer_id),
            'offer_type': offer.offer_type,
            'offer_status': offer.offer_status,
            'propensity': offer.propensity,
            'loan_application_number': offer.loan_application_number,
            'valid_until': offer.valid_until.isoformat() if offer.valid_until else None,
            'source_system': offer.source_system,
            'channel': offer.channel,
            'is_duplicate_offer': offer.is_duplicate,
            'customer_attributes': customer.attributes # JSONB field
        })
    return results

def get_duplicate_customer_data():
    """
    Retrieves data for the Duplicate Data File (FR31).
    This function identifies customers who have at least one offer marked as `is_duplicate=True`.
    In a more advanced system, this might involve a dedicated `duplicate_customer_mapping` table
    or a more complex query based on the deduplication service's output.
    """
    # Find customer IDs that are associated with any offer flagged as a duplicate
    customer_ids_with_duplicate_offers = db.session.query(Offer.customer_id).filter(Offer.is_duplicate == True).distinct().subquery()
    
    # Retrieve the full customer records for these identified customer IDs
    duplicate_customers = Customer.query.filter(Customer.customer_id.in_(list(customer_ids_with_duplicate_offers.select()))).all()

    results = []
    for customer in duplicate_customers:
        results.append({
            'customer_id': str(customer.customer_id),
            'mobile_number': customer.mobile_number,
            'pan_number': customer.pan_number,
            'aadhaar_number': customer.aadhaar_number,
            'ucid_number': customer.ucid_number,
            'is_dnd': customer.is_dnd,
            'segment': customer.segment,
            'attributes': customer.attributes
        })
    return results

def get_unique_customer_data():
    """
    Retrieves data for the Unique Data File (FR32).
    As per FR1, the `customers` table itself should represent the de-duplicated single profile view.
    Therefore, this function returns all records from the `customers` table.
    """
    unique_customers = Customer.query.all()
    results = []
    for customer in unique_customers:
        results.append({
            'customer_id': str(customer.customer_id),
            'mobile_number': customer.mobile_number,
            'pan_number': customer.pan_number,
            'aadhaar_number': customer.aadhaar_number,
            'ucid_number': customer.ucid_number,
            'is_dnd': customer.is_dnd,
            'segment': customer.segment,
            'attributes': customer.attributes
        })
    return results

def get_error_data():
    """
    Retrieves data for the Error Excel file for data uploads (FR33).
    Fetches all logged data errors.
    """
    errors = DataError.query.order_by(DataError.timestamp.desc()).all()
    results = []
    for error in errors:
        results.append({
            'error_id': str(error.error_id),
            'source_system': error.source_system,
            'record_identifier': error.record_identifier,
            'error_message': error.error_message,
            'error_details': error.error_details,
            'timestamp': error.timestamp.isoformat()
        })
    return results

def log_data_error(source_system, record_identifier, error_message, error_details=None):
    """Logs a data validation error (FR2, NFR8)."""
    try:
        new_error = DataError(
            source_system=source_system,
            record_identifier=record_identifier,
            error_message=error_message,
            error_details=error_details
        )
        db.session.add(new_error)
        db.session.commit()
        return new_error
    except Exception as e:
        db.session.rollback()
        print(f"Error logging data error: {e}")
        raise

def cleanup_old_data():
    """
    Performs data retention cleanup based on NFRs.
    NFR10: Offer history shall be maintained for 6 months.
    NFR11: All data in CDP shall be maintained for 3 months before deletion.
    """
    now = datetime.now(timezone.utc)
    
    # Cleanup OfferHistory (older than 6 months)
    six_months_ago = now - timedelta(days=6 * 30) # Approximate 6 months
    deleted_history_count = OfferHistory.query.filter(OfferHistory.status_change_date < six_months_ago).delete()
    print(f"Deleted {deleted_history_count} old offer history records.")

    # Cleanup Events (older than 3 months)
    three_months_ago = now - timedelta(days=3 * 30) # Approximate 3 months
    deleted_events_count = Event.query.filter(Event.event_timestamp < three_months_ago).delete()
    print(f"Deleted {deleted_events_count} old event records.")

    # Cleanup Offers: Delete offers that are 'Expired' AND created more than 3 months ago.
    # This ensures that active offers are not deleted prematurely.
    deleted_offers_count = Offer.query.filter(
        Offer.offer_status == 'Expired',
        Offer.created_at < three_months_ago
    ).delete()
    print(f"Deleted {deleted_offers_count} old expired offer records.")

    # Note on Customer/Campaign deletion:
    # Deleting `Customer` records based on `created_at` is generally not advisable for a CDP
    # as it aims for a "single customer view" (FR1) and customer 360 integration (NFR17).
    # Customer records are typically retained indefinitely or soft-deleted.
    # `Campaign` records (FR34, FR35) are also usually kept for historical metrics.
    # The NFR11 "All data in CDP shall be maintained for 3 months before deletion" is interpreted
    # to apply to transactional/event data and expired offers, not core customer or campaign definitions.

    db.session.commit()
    print("Database cleanup completed.")

def bulk_insert_customers_and_offers(customer_data_list, offer_data_list):
    """
    Performs bulk insertion of customer and offer data.
    Useful for initial data migration from MAS (Assumption 1).
    """
    try:
        customer_objects = []
        for data in customer_data_list:
            customer_objects.append(Customer(**data))
        db.session.bulk_save_objects(customer_objects)
        db.session.flush() # Flush to assign IDs before offers if needed for linking

        offer_objects = []
        for data in offer_data_list:
            offer_objects.append(Offer(**data))
        db.session.bulk_save_objects(offer_objects)
        db.session.commit()
        print(f"Bulk inserted {len(customer_objects)} customers and {len(offer_objects)} offers.")
    except Exception as e:
        db.session.rollback()
        print(f"Error during bulk insert: {e}")
        raise

def validate_customer_data(data):
    """Performs basic column-level data validation for customer data (FR2, NFR8)."""
    errors = []
    # Check for at least one unique identifier
    if not any(data.get(key) for key in ['mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number']):
        errors.append("At least one unique identifier (mobile_number, pan_number, aadhaar_number, or ucid_number) is required.")
    
    # Example: Basic type and format checks
    if data.get('mobile_number') and not isinstance(data['mobile_number'], str):
        errors.append("Mobile number must be a string.")
    if data.get('pan_number') and not isinstance(data['pan_number'], str):
        errors.append("PAN number must be a string.")
    # Add more specific validation (e.g., regex for PAN, Aadhaar, length constraints)
    
    return errors

def validate_offer_data(data):
    """Performs basic column-level data validation for offer data (FR2, NFR8)."""
    errors = []
    if not data.get('customer_id'):
        errors.append("Customer ID is required for an offer.")
    if not data.get('offer_type'):
        errors.append("Offer type is required.")
    
    # Validate valid_until format
    if 'valid_until' in data and data['valid_until'] is not None:
        if isinstance(data['valid_until'], str):
            try:
                # Attempt to parse ISO format string to datetime
                data['valid_until'] = datetime.fromisoformat(data['valid_until'])
            except ValueError:
                errors.append("Invalid format for 'valid_until'. Must be a datetime object or ISO formatted string.")
        elif not isinstance(data['valid_until'], datetime):
            errors.append("'valid_until' must be a datetime object or ISO formatted string.")
    
    # Add more specific validation (e.g., allowed offer_type values)
    
    return errors