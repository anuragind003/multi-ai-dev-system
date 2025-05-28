import os
from datetime import datetime, date
import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()

def init_db(app):
    """
    Initializes the SQLAlchemy database connection with the Flask app.
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    with app.app_context():
        # This will create tables if they don't exist.
        # In a production environment, migrations (e.g., Flask-Migrate) are preferred
        # to manage schema changes and initial data loading.
        db.create_all()

# --- Database Models ---
class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    pan = db.Column(db.String(10), unique=True)
    aadhaar_ref_number = db.Column(db.String(12), unique=True)
    ucid = db.Column(db.String(50), unique=True)
    previous_loan_app_number = db.Column(db.String(50), unique=True)
    customer_attributes = db.Column(JSONB) # Stores various customer attributes
    customer_segment = db.Column(db.String(10)) # e.g., C1 to C8
    is_dnd = db.Column(db.Boolean, default=False) # Flag for Do Not Disturb customers
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('CustomerEvent', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} - {self.mobile_number}>"

class Offer(db.Model):
    __tablename__ = 'offers'

    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.String(20)) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(20)) # 'Active', 'Inactive', 'Expired'
    propensity_flag = db.Column(db.String(50)) # e.g., 'dominant tradeline'
    offer_start_date = db.Column(db.Date)
    offer_end_date = db.Column(db.Date)
    loan_application_number = db.Column(db.String(50), unique=True) # Nullable, if journey not started
    attribution_channel = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id}>"

class CustomerEvent(db.Model):
    __tablename__ = 'customer_events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False) # 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK', 'CONVERSION', 'APP_STAGE_LOGIN', etc.
    event_source = db.Column(db.String(20), nullable=False) # 'Moengage', 'LOS'
    event_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now)
    event_details = db.Column(JSONB) # Stores specific event data (e.g., application stage details)

    def __repr__(self):
        return f"<CustomerEvent {self.event_id} - {self.event_type}>"

class Campaign(db.Model):
    __tablename__ = 'campaigns'

    campaign_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_unique_identifier = db.Column(db.String(100), unique=True, nullable=False)
    campaign_name = db.Column(db.String(255), nullable=False)
    campaign_date = db.Column(db.Date)
    targeted_customers_count = db.Column(db.Integer)
    attempted_count = db.Column(db.Integer)
    successfully_sent_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    success_rate = db.Column(db.Numeric(5,2))
    conversion_rate = db.Column(db.Numeric(5,2))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now)
    updated_at = db.Column(db.DateTime(timezone=True), default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<Campaign {self.campaign_id} - {self.campaign_name}>"

class DataIngestionLog(db.Model):
    __tablename__ = 'data_ingestion_logs'

    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime(timezone=True), default=datetime.now)
    status = db.Column(db.String(20), nullable=False) # 'SUCCESS', 'FAILED', 'PARTIAL'
    error_details = db.Column(db.Text) # Stores error messages for failed records
    uploaded_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<DataIngestionLog {self.log_id} - {self.file_name} - {self.status}>"

# --- Utility Functions for Database Operations ---

def get_customer_by_identifiers(mobile_number=None, pan=None, aadhaar_ref_number=None, ucid=None, previous_loan_app_number=None):
    """
    Retrieves a customer by any of the unique identifiers.
    Used for deduplication (FR3, FR4, FR5) and single profile view (FR2).
    """
    query = Customer.query
    filters = []
    if mobile_number:
        filters.append(Customer.mobile_number == mobile_number)
    if pan:
        filters.append(Customer.pan == pan)
    if aadhaar_ref_number:
        filters.append(Customer.aadhaar_ref_number == aadhaar_ref_number)
    if ucid:
        filters.append(Customer.ucid == ucid)
    if previous_loan_app_number:
        filters.append(Customer.previous_loan_app_number == previous_loan_app_number)

    if not filters:
        return None # No identifiers provided

    # Use OR to find a customer matching any of the provided identifiers
    return query.filter(db.or_(*filters)).first()

def create_or_update_customer(customer_data):
    """
    Creates a new customer or updates an existing one based on identifiers.
    Returns the Customer object and a boolean indicating if it was created.
    Used for data ingestion (FR7, FR9, FR10, FR29).
    """
    existing_customer = get_customer_by_identifiers(
        mobile_number=customer_data.get('mobile_number'),
        pan=customer_data.get('pan'),
        aadhaar_ref_number=customer_data.get('aadhaar_ref_number'),
        ucid=customer_data.get('ucid'),
        previous_loan_app_number=customer_data.get('previous_loan_app_number')
    )

    if existing_customer:
        # Update existing customer (FR6, FR14)
        for key, value in customer_data.items():
            # Only update if the value is provided and different
            if hasattr(existing_customer, key) and value is not None and getattr(existing_customer, key) != value:
                setattr(existing_customer, key, value)
        db.session.add(existing_customer)
        db.session.commit()
        return existing_customer, False
    else:
        # Create new customer
        new_customer = Customer(**customer_data)
        db.session.add(new_customer)
        db.session.commit()
        return new_customer, True

def create_offer(offer_data):
    """
    Creates a new offer record.
    Used for data ingestion (FR7).
    """
    new_offer = Offer(**offer_data)
    db.session.add(new_offer)
    db.session.commit()
    return new_offer

def update_offer_status(offer_id, new_status, loan_application_number=None):
    """
    Updates the status of an offer.
    Used for offer expiry logic (FR13, FR15, FR37, FR38).
    Optionally updates loan_application_number if provided.
    """
    offer = Offer.query.get(offer_id)
    if offer:
        offer.offer_status = new_status
        if loan_application_number:
            offer.loan_application_number = loan_application_number
        db.session.commit()
        return offer
    return None

def create_customer_event(event_data):
    """
    Records a customer event.
    Used for event tracking (FR21, FR22).
    """
    new_event = CustomerEvent(**event_data)
    db.session.add(new_event)
    db.session.commit()
    return new_event

def log_data_ingestion(file_name, status, uploaded_by=None, error_details=None):
    """
    Logs the result of a data ingestion process (e.g., file upload).
    Used for Admin Portal uploads (FR31, FR32).
    """
    log_entry = DataIngestionLog(
        file_name=file_name,
        status=status,
        uploaded_by=uploaded_by,
        error_details=error_details
    )
    db.session.add(log_entry)
    db.session.commit()
    return log_entry

def get_customer_profile_view(customer_id):
    """
    Retrieves a single customer's profile with associated offers and events.
    Used for FR36 (customer level view).
    """
    customer = Customer.query.options(db.joinedload(Customer.offers), db.joinedload(Customer.events))\
                             .filter_by(customer_id=customer_id).first()
    if customer:
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
            "created_at": customer.created_at.isoformat() if customer.created_at else None,
            "updated_at": customer.updated_at.isoformat() if customer.updated_at else None,
            "active_offers": [],
            "application_stages": []
        }

        for offer in customer.offers:
            # Assuming 'Active' offers are those relevant for a current view
            if offer.offer_status == 'Active':
                customer_data["active_offers"].append({
                    "offer_id": str(offer.offer_id),
                    "offer_type": offer.offer_type,
                    "offer_status": offer.offer_status,
                    "propensity_flag": offer.propensity_flag,
                    "offer_start_date": offer.offer_start_date.isoformat() if offer.offer_start_date else None,
                    "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
                    "loan_application_number": offer.loan_application_number,
                    "attribution_channel": offer.attribution_channel
                })
        
        for event in customer.events:
            # Filter for application stage events
            if event.event_type and event.event_type.startswith('APP_STAGE_'):
                customer_data["application_stages"].append({
                    "event_type": event.event_type,
                    "event_source": event.event_source,
                    "event_timestamp": event.event_timestamp.isoformat() if event.event_timestamp else None,
                    "event_details": event.event_details
                })
        return customer_data
    return None

def get_offers_for_moengage_file():
    """
    Retrieves data for the Moengage file generation.
    This typically involves active offers for non-DND customers. (FR25, FR39)
    """
    # Join Customer and Offer tables, filter for active offers and non-DND customers.
    # The specific fields for Moengage file would be defined by the analytics team.
    offers_data = db.session.query(Offer, Customer)\
        .join(Customer, Offer.customer_id == Customer.customer_id)\
        .filter(Offer.offer_status == 'Active', Customer.is_dnd == False)\
        .all()
    
    results = []
    for offer, customer in offers_data:
        results.append({
            "customer_id": str(customer.customer_id),
            "mobile_number": customer.mobile_number,
            "offer_id": str(offer.offer_id),
            "offer_type": offer.offer_type,
            "offer_end_date": offer.offer_end_date.isoformat() if offer.offer_end_date else None,
            "customer_segment": customer.customer_segment,
            "pan": customer.pan, # Include other relevant customer details for Moengage
            "loan_application_number": offer.loan_application_number,
            "attribution_channel": offer.attribution_channel,
            "propensity_flag": offer.propensity_flag
            # ... add any other fields required for Moengage
        })
    return results

def get_duplicate_data_for_report():
    """
    Retrieves data identified as duplicates.
    As the `customers` table is deduplicated, this function would typically query a staging
    area or a deduplication log. Without such a table in the schema,
    this function returns all customers, and the logic to identify "duplicates"
    for the report would reside in the service layer that processes this data.
    (FR26)
    """
    # In a real scenario, this would query a dedicated `deduplication_log` table
    # or a staging table that holds records identified as duplicates before merging.
    # For now, returning all customers as a placeholder.
    return Customer.query.all()

def get_unique_data_for_report():
    """
    Retrieves unique customer profiles. (FR27)
    This is essentially all records in the `customers` table after deduplication.
    """
    return Customer.query.all()

def get_error_data_for_report():
    """
    Retrieves data ingestion logs marked as 'FAILED' or 'PARTIAL'. (FR28)
    """
    return DataIngestionLog.query.filter(
        (DataIngestionLog.status == 'FAILED') | (DataIngestionLog.status == 'PARTIAL')
    ).all()

def get_daily_tally_report(report_date: date):
    """
    Retrieves daily data tally reports. (FR35)
    This is a conceptual function that would aggregate data.
    """
    # Counts for the given date
    total_customers_processed = Customer.query.filter(
        func.date(Customer.created_at) == report_date
    ).count()

    new_offers_generated = Offer.query.filter(
        func.date(Offer.created_at) == report_date
    ).count()

    # The 'deduplicated_customers' metric is complex without a specific log table.
    # It could mean customers newly created as unique, or existing customers updated due to deduplication.
    # For now, it's a placeholder. A more precise definition or a dedicated audit table is needed.
    deduplicated_customers_count = 0 # Placeholder

    return {
        "date": report_date.isoformat(),
        "total_customers_processed": total_customers_processed,
        "new_offers_generated": new_offers_generated,
        "deduplicated_customers": deduplicated_customers_count
    }

def get_all_customers():
    """Retrieves all customer records."""
    return Customer.query.all()

def get_all_offers():
    """Retrieves all offer records."""
    return Offer.query.all()

def get_all_customer_events():
    """Retrieves all customer event records."""
    return CustomerEvent.query.all()

def get_all_campaigns():
    """Retrieves all campaign records."""
    return Campaign.query.all()

def get_all_data_ingestion_logs():
    """Retrieves all data ingestion log records."""
    return DataIngestionLog.query.all()

def delete_old_offer_history(months_to_retain=6):
    """
    Deletes offer history older than specified months. (FR18, NFR3)
    This function should be run as a scheduled job.
    """
    cutoff_date = datetime.now() - func.interval(f'{months_to_retain} months')
    # Only delete offers that are 'Expired' or 'Inactive' and older than retention period
    # To avoid deleting active offers that might still be relevant but old.
    # The BRD says "maintain offer history for the past 06 months for reference purposes."
    # This implies deleting *beyond* 6 months.
    # If an offer is active but older than 6 months, it should probably not be deleted.
    # This needs clarification. Assuming it means *any* offer older than 6 months.
    # If "offer history" means *all* offers, then the filter is just by date.
    # If it means *completed/expired* offers, then status filter is needed.
    # Sticking to the literal "offer history for the past 06 months" meaning delete older.
    deleted_count = Offer.query.filter(Offer.created_at < cutoff_date).delete(synchronize_session=False)
    db.session.commit()
    return deleted_count

def delete_old_cdp_data(months_to_retain=3):
    """
    Deletes all CDP data (excluding customer profiles and active offers) older than specified months.
    This applies to `customer_events` and `data_ingestion_logs` as per NFR4.
    Campaigns might also be subject to this, but often retained longer for analytics.
    This function should be run as a scheduled job.
    """
    cutoff_date = datetime.now() - func.interval(f'{months_to_retain} months')
    
    deleted_events_count = CustomerEvent.query.filter(CustomerEvent.event_timestamp < cutoff_date).delete(synchronize_session=False)
    deleted_logs_count = DataIngestionLog.query.filter(DataIngestionLog.upload_timestamp < cutoff_date).delete(synchronize_session=False)
    
    db.session.commit()
    return {"events_deleted": deleted_events_count, "logs_deleted": deleted_logs_count}

# --- Session Management Helpers (for use in services/routes) ---
def commit_session():
    """Commits the current database session."""
    db.session.commit()

def rollback_session():
    """Rolls back the current database session."""
    db.session.rollback()

def close_session():
    """Closes the current database session."""
    db.session.close()