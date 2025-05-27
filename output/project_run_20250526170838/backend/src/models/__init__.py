import uuid
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Define the Customer model
class Customer(db.Model):
    __tablename__ = 'customers'

    customer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True, nullable=True)
    pan_number = db.Column(db.Text, unique=True, nullable=True)
    aadhaar_number = db.Column(db.Text, unique=True, nullable=True)
    ucid_number = db.Column(db.Text, unique=True, nullable=True)
    loan_application_number = db.Column(db.Text, unique=True, nullable=True)
    dnd_flag = db.Column(db.Boolean, default=False, nullable=False)
    segment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)

    # Relationships
    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id} - Mobile: {self.mobile_number}>"

# Define the Offer model
class Offer(db.Model):
    __tablename__ = 'offers'

    offer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text, nullable=True) # 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status = db.Column(db.Text, nullable=True) # 'Active', 'Inactive', 'Expired'
    propensity = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    channel = db.Column(db.Text, nullable=True) # For attribution logic
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), onupdate=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return f"<Offer {self.offer_id} for Customer {self.customer_id} - Status: {self.offer_status}>"

# Define the Event model
class Event(db.Model):
    __tablename__ = 'events'

    event_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text, nullable=False) # 'SMS_SENT', 'SMS_DELIVERED', 'EKYC_ACHIEVED', 'LOAN_LOGIN', etc.
    event_source = db.Column(db.Text, nullable=False) # 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp = db.Column(db.DateTime, nullable=False) # No server_default, as per DDL
    event_details = db.Column(JSONB, nullable=True) # Flexible storage for event-specific data
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return f"<Event {self.event_id} - Type: {self.event_type} from {self.event_source}>"

# Define the CampaignMetric model
class CampaignMetric(db.Model):
    __tablename__ = 'campaign_metrics'

    metric_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text, nullable=True)
    campaign_date = db.Column(db.Date, nullable=True)
    attempted_count = db.Column(db.Integer, nullable=True)
    sent_success_count = db.Column(db.Integer, nullable=True)
    failed_count = db.Column(db.Integer, nullable=True)
    conversion_rate = db.Column(db.Numeric(5,2), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)

    def __repr__(self):
        return f"<CampaignMetric {self.metric_id} - Campaign: {self.campaign_unique_id}>"

# Define the IngestionLog model
class IngestionLog(db.Model):
    __tablename__ = 'ingestion_logs'

    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.DateTime, server_default=db.func.current_timestamp(), nullable=False)
    status = db.Column(db.Text, nullable=False) # 'SUCCESS', 'FAILED'
    error_description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<IngestionLog {self.log_id} - File: {self.file_name} - Status: {self.status}>"

# Helper function to initialize the database within a Flask app context
def init_db(app):
    """
    Initializes the SQLAlchemy database instance with the Flask app.
    This function should be called from your main app creation file (e.g., app.py).
    """
    db.init_app(app)
    with app.app_context():
        db.create_all() # Creates tables if they don't exist