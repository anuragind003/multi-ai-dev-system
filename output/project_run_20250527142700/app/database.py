from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import text, func
import uuid
from datetime import datetime

# Initialize SQLAlchemy without an app.
# The Flask application instance will be passed later using db.init_app(app).
db = SQLAlchemy()

# --- Database Models ---
# These models define the structure of the database tables based on the
# 'database_schema' provided in the project context.

class Customer(db.Model):
    """
    Represents a customer profile in the CDP.
    Corresponds to the 'customers' table in the database schema.
    """
    __tablename__ = 'customers'

    customer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    mobile_number = db.Column(db.String(20), unique=True, nullable=False)
    pan = db.Column(db.String(10), unique=True)
    aadhaar_ref_number = db.Column(db.String(12), unique=True)
    ucid = db.Column(db.String(50), unique=True)
    previous_loan_app_number = db.Column(db.String(50), unique=True)
    customer_attributes = db.Column(JSONB)  # Stores various customer attributes as JSON
    customer_segment = db.Column(db.String(10))  # e.g., C1 to C8
    is_dnd = db.Column(db.Boolean, default=False)  # Flag for Do Not Disturb customers
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Relationships
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('CustomerEvent', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} | Mobile: {self.mobile_number}>"

class Offer(db.Model):
    """
    Represents an offer associated with a customer.
    Corresponds to the 'offers' table in the database schema.
    """
    __tablename__ = 'offers'

    offer_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.String(20))  # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.String(20))  # 'Active', 'Inactive', 'Expired'
    propensity_flag = db.Column(db.String(50))  # e.g., 'dominant tradeline'
    offer_start_date = db.Column(db.Date)
    offer_end_date = db.Column(db.Date)
    loan_application_number = db.Column(db.String(50))  # Nullable, if journey not started
    attribution_channel = db.Column(db.String(50))
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Offer {self.offer_id} | Customer: {self.customer_id} | Status: {self.offer_status}>"

class CustomerEvent(db.Model):
    """
    Stores event data related to customer interactions (e.g., SMS, application stages).
    Corresponds to the 'customer_events' table in the database schema.
    """
    __tablename__ = 'customer_events'

    event_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id = db.Column(UUID(as_uuid=True), db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.String(50), nullable=False)  # 'SMS_SENT', 'SMS_DELIVERED', 'SMS_CLICK', 'CONVERSION', 'APP_STAGE_LOGIN', etc.
    event_source = db.Column(db.String(20), nullable=False)  # 'Moengage', 'LOS'
    event_timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    event_details = db.Column(JSONB)  # Stores specific event data (e.g., application stage details)

    def __repr__(self):
        return f"<CustomerEvent {self.event_id} | Type: {self.event_type} | Source: {self.event_source}>"

class Campaign(db.Model):
    """
    Maintains details about marketing campaigns.
    Corresponds to the 'campaigns' table in the database schema.
    """
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
    created_at = db.Column(db.DateTime(timezone=True), default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Campaign {self.campaign_id} | Name: {self.campaign_name}>"

class DataIngestionLog(db.Model):
    """
    Logs details of data ingestion processes, especially file uploads.
    Corresponds to the 'data_ingestion_logs' table in the database schema.
    """
    __tablename__ = 'data_ingestion_logs'

    log_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_name = db.Column(db.String(255), nullable=False)
    upload_timestamp = db.Column(db.DateTime(timezone=True), default=func.now())
    status = db.Column(db.String(20), nullable=False)  # 'SUCCESS', 'FAILED', 'PARTIAL'
    error_details = db.Column(db.Text)  # Stores error messages for failed records
    uploaded_by = db.Column(db.String(100))

    def __repr__(self):
        return f"<DataIngestionLog {self.log_id} | File: {self.file_name} | Status: {self.status}>"

# Helper functions for database management (e.g., for development/testing)
def create_tables(app):
    """
    Creates all defined database tables.
    This should typically be called within a Flask application context.
    For production, consider using Flask-Migrate for schema management.
    """
    with app.app_context():
        db.create_all()
        print("Database tables created.")

def drop_tables(app):
    """
    Drops all defined database tables. Use with extreme caution, especially in production.
    This should typically be called within a Flask application context.
    """
    with app.app_context():
        db.drop_all()
        print("Database tables dropped.")