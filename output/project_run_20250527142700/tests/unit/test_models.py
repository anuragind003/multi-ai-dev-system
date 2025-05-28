import pytest
from datetime import datetime, date
import uuid
import json

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import UUID, JSONB # Used for type hints, will map to generic types for SQLite

# --- Fixtures for Test Environment ---

class TestConfig:
    """Configuration for the test Flask app."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:" # Use in-memory SQLite for fast unit tests
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

@pytest.fixture(scope='session')
def app():
    """Fixture for a test Flask app instance with initialized database and models."""
    _app = Flask(__name__)
    _app.config.from_object(TestConfig)

    # Initialize db with the app
    _db = SQLAlchemy(_app)
    _app.db = _db # Attach db to app for easy access in tests

    # Define models directly within the fixture for self-contained testing.
    # In a real project, these would be imported from `app.models`.
    with _app.app_context():
        class Customer(_db.Model):
            __tablename__ = 'customers'
            customer_id = _db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            mobile_number = _db.Column(_db.String(20), unique=True, nullable=False)
            pan = _db.Column(_db.String(10), unique=True)
            aadhaar_ref_number = _db.Column(_db.String(12), unique=True)
            ucid = _db.Column(_db.String(50), unique=True)
            previous_loan_app_number = _db.Column(_db.String(50), unique=True)
            customer_attributes = _db.Column(JSONB)
            customer_segment = _db.Column(_db.String(10))
            is_dnd = _db.Column(_db.Boolean, default=False)
            created_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow)
            updated_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

            offers = _db.relationship('Offer', backref='customer', lazy=True)
            events = _db.relationship('CustomerEvent', backref='customer', lazy=True)

            def __repr__(self):
                return f"<Customer {self.mobile_number}>"

        class Offer(_db.Model):
            __tablename__ = 'offers'
            offer_id = _db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            customer_id = _db.Column(UUID(as_uuid=True), _db.ForeignKey('customers.customer_id'), nullable=False)
            offer_type = _db.Column(_db.String(20))
            offer_status = _db.Column(_db.String(20))
            propensity_flag = _db.Column(_db.String(50))
            offer_start_date = _db.Column(_db.Date)
            offer_end_date = _db.Column(_db.Date)
            loan_application_number = _db.Column(_db.String(50))
            attribution_channel = _db.Column(_db.String(50))
            created_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow)
            updated_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

            def __repr__(self):
                return f"<Offer {self.offer_id} for Customer {self.customer_id}>"

        class CustomerEvent(_db.Model):
            __tablename__ = 'customer_events'
            event_id = _db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            customer_id = _db.Column(UUID(as_uuid=True), _db.ForeignKey('customers.customer_id'), nullable=False)
            event_type = _db.Column(_db.String(50), nullable=False)
            event_source = _db.Column(_db.String(20), nullable=False)
            event_timestamp = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow)
            event_details = _db.Column(JSONB)

            def __repr__(self):
                return f"<CustomerEvent {self.event_type} for Customer {self.customer_id}>"

        class Campaign(_db.Model):
            __tablename__ = 'campaigns'
            campaign_id = _db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            campaign_unique_identifier = _db.Column(_db.String(100), unique=True, nullable=False)
            campaign_name = _db.Column(_db.String(255), nullable=False)
            campaign_date = _db.Column(_db.Date)
            targeted_customers_count = _db.Column(_db.Integer)
            attempted_count = _db.Column(_db.Integer)
            successfully_sent_count = _db.Column(_db.Integer)
            failed_count = _db.Column(_db.Integer)
            success_rate = _db.Column(_db.Numeric(5,2))
            conversion_rate = _db.Column(_db.Numeric(5,2))
            created_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow)
            updated_at = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

            def __repr__(self):
                return f"<Campaign {self.campaign_name}>"

        class DataIngestionLog(_db.Model):
            __tablename__ = 'data_ingestion_logs'
            log_id = _db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
            file_name = _db.Column(_db.String(255), nullable=False)
            upload_timestamp = _db.Column(_db.DateTime(timezone=True), default=datetime.utcnow)
            status = _db.Column(_db.String(20), nullable=False)
            error_details = _db.Column(_db.Text)
            uploaded_by = _db.Column(_db.String(100))

            def __repr__(self):
                return f"<DataIngestionLog {self.file_name} - {self.status}>"

        # Attach models to app for easy access in tests
        _app.Customer = Customer
        _app.Offer = Offer
        _app.CustomerEvent = CustomerEvent
        _app.Campaign = Campaign
        _app.DataIngestionLog = DataIngestionLog

        _db.create_all() # Create tables for all models

    yield _app

    with _app.app_context():
        _db.drop_all() # Clean up after tests

@pytest.fixture(scope='function')
def db_session(app):
    """Fixture for a database session, ensuring a clean state for each test."""
    with app.app_context():
        _db = app.db
        connection = _db.engine.connect()
        transaction = connection.begin()

        options = dict(bind=connection, binds={})
        session = _db.create_scoped_session(options=options)

        _db.session = session # Bind the session to the db object

        yield session

        transaction.rollback() # Rollback changes after each test
        connection.close()
        session.remove() # Remove the session

# --- Unit Tests for Models ---

def test_customer_creation(db_session, app):
    """Test creating a Customer instance and persisting it."""
    Customer = app.Customer
    customer = Customer(
        mobile_number="9876543210",
        pan="ABCDE1234F",
        aadhaar_ref_number="123456789012",
        ucid="UCID12345",
        previous_loan_app_number="LAN001",
        customer_attributes={"age": 30, "city": "Mumbai"},
        customer_segment="C1",
        is_dnd=False
    )
    db_session.add(customer)
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="9876543210").first()
    assert retrieved_customer is not None
    assert retrieved_customer.mobile_number == "9876543210"
    assert retrieved_customer.pan == "ABCDE1234F"
    assert retrieved_customer.customer_attributes == {"age": 30, "city": "Mumbai"}
    assert isinstance(retrieved_customer.customer_id, uuid.UUID)
    assert isinstance(retrieved_customer.created_at, datetime)
    assert isinstance(retrieved_customer.updated_at, datetime)
    assert retrieved_customer.is_dnd is False

def test_customer_mobile_number_unique_constraint(db_session, app):
    """Test the unique constraint on mobile_number."""
    Customer = app.Customer
    customer1 = Customer(mobile_number="1111111111")
    db_session.add(customer1)
    db_session.commit()

    customer2 = Customer(mobile_number="1111111111")
    db_session.add(customer2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback() # Rollback to clear the failed transaction

def test_customer_nullable_fields(db_session, app):
    """Test creating a Customer with only required fields."""
    Customer = app.Customer
    customer = Customer(mobile_number="9999999999")
    db_session.add(customer)
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="9999999999").first()
    assert retrieved_customer is not None
    assert retrieved_customer.pan is None
    assert retrieved_customer.customer_attributes is None
    assert retrieved_customer.is_dnd is False # Check default value

def test_offer_creation(db_session, app):
    """Test creating an Offer instance and persisting it."""
    Customer = app.Customer
    Offer = app.Offer
    customer = Customer(mobile_number="1234567890")
    db_session.add(customer)
    db_session.commit()

    offer = Offer(
        customer_id=customer.customer_id,
        offer_type="Fresh",
        offer_status="Active",
        propensity_flag="dominant tradeline",
        offer_start_date=date(2023, 1, 1),
        offer_end_date=date(2023, 12, 31),
        loan_application_number="LAN002",
        attribution_channel="Moengage"
    )
    db_session.add(offer)
    db_session.commit()

    retrieved_offer = db_session.query(Offer).filter_by(customer_id=customer.customer_id).first()
    assert retrieved_offer is not None
    assert retrieved_offer.offer_type == "Fresh"
    assert retrieved_offer.offer_status == "Active"
    assert retrieved_offer.customer.mobile_number == "1234567890" # Test relationship backref
    assert isinstance(retrieved_offer.offer_id, uuid.UUID)
    assert isinstance(retrieved_offer.created_at, datetime)

def test_offer_foreign_key_constraint(db_session, app):
    """Test foreign key constraint for Offer to Customer."""
    Offer = app.Offer
    # Attempt to create an offer with a non-existent customer_id
    offer = Offer(
        customer_id=uuid.uuid4(), # Random UUID, not in DB
        offer_type="Fresh",
        offer_status="Active"
    )
    db_session.add(offer)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_customer_event_creation(db_session, app):
    """Test creating a CustomerEvent instance and persisting it."""
    Customer = app.Customer
    CustomerEvent = app.CustomerEvent
    customer = Customer(mobile_number="2345678901")
    db_session.add(customer)
    db_session.commit()

    event = CustomerEvent(
        customer_id=customer.customer_id,
        event_type="SMS_SENT",
        event_source="Moengage",
        event_details={"campaign_id": "CMP001", "message": "Offer sent"}
    )
    db_session.add(event)
    db_session.commit()

    retrieved_event = db_session.query(CustomerEvent).filter_by(customer_id=customer.customer_id).first()
    assert retrieved_event is not None
    assert retrieved_event.event_type == "SMS_SENT"
    assert retrieved_event.event_source == "Moengage"
    assert retrieved_event.event_details == {"campaign_id": "CMP001", "message": "Offer sent"}
    assert retrieved_event.customer.mobile_number == "2345678901" # Test relationship backref
    assert isinstance(retrieved_event.event_id, uuid.UUID)
    assert isinstance(retrieved_event.event_timestamp, datetime)

def test_customer_event_nullable_fields(db_session, app):
    """Test creating a CustomerEvent with nullable fields as None."""
    Customer = app.Customer
    CustomerEvent = app.CustomerEvent
    customer = Customer(mobile_number="3456789012")
    db_session.add(customer)
    db_session.commit()

    event = CustomerEvent(
        customer_id=customer.customer_id,
        event_type="APP_STAGE_LOGIN",
        event_source="LOS"
    ) # event_details is nullable
    db_session.add(event)
    db_session.commit()

    retrieved_event = db_session.query(CustomerEvent).filter_by(customer_id=customer.customer_id).first()
    assert retrieved_event is not None
    assert retrieved_event.event_details is None

def test_campaign_creation(db_session, app):
    """Test creating a Campaign instance and persisting it."""
    Campaign = app.Campaign
    campaign = Campaign(
        campaign_unique_identifier="CMP_20231027_001",
        campaign_name="Diwali Loan Offer",
        campaign_date=date(2023, 10, 27),
        targeted_customers_count=1000,
        attempted_count=950,
        successfully_sent_count=900,
        failed_count=50,
        success_rate=94.74, # 900/950 * 100
        conversion_rate=5.00 # Assuming 50 conversions
    )
    db_session.add(campaign)
    db_session.commit()

    retrieved_campaign = db_session.query(Campaign).filter_by(campaign_unique_identifier="CMP_20231027_001").first()
    assert retrieved_campaign is not None
    assert retrieved_campaign.campaign_name == "Diwali Loan Offer"
    assert retrieved_campaign.targeted_customers_count == 1000
    assert float(retrieved_campaign.success_rate) == pytest.approx(94.74) # Use pytest.approx for float/numeric comparison
    assert isinstance(retrieved_campaign.campaign_id, uuid.UUID)
    assert isinstance(retrieved_campaign.created_at, datetime)

def test_campaign_unique_identifier_constraint(db_session, app):
    """Test the unique constraint on campaign_unique_identifier."""
    Campaign = app.Campaign
    campaign1 = Campaign(campaign_unique_identifier="CMP_TEST_001", campaign_name="Test Campaign 1")
    db_session.add(campaign1)
    db_session.commit()

    campaign2 = Campaign(campaign_unique_identifier="CMP_TEST_001", campaign_name="Test Campaign 2")
    db_session.add(campaign2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

def test_data_ingestion_log_creation(db_session, app):
    """Test creating a DataIngestionLog instance and persisting it."""
    DataIngestionLog = app.DataIngestionLog
    log = DataIngestionLog(
        file_name="customer_upload_20231027.csv",
        status="SUCCESS",
        uploaded_by="admin_user",
        error_details=None
    )
    db_session.add(log)
    db_session.commit()

    retrieved_log = db_session.query(DataIngestionLog).filter_by(file_name="customer_upload_20231027.csv").first()
    assert retrieved_log is not None
    assert retrieved_log.status == "SUCCESS"
    assert retrieved_log.uploaded_by == "admin_user"
    assert retrieved_log.error_details is None
    assert isinstance(retrieved_log.log_id, uuid.UUID)
    assert isinstance(retrieved_log.upload_timestamp, datetime)

def test_data_ingestion_log_with_errors(db_session, app):
    """Test creating a DataIngestionLog with error details."""
    DataIngestionLog = app.DataIngestionLog
    log = DataIngestionLog(
        file_name="customer_upload_errors.csv",
        status="FAILED",
        uploaded_by="admin_user",
        error_details="Row 5: Invalid mobile number; Row 10: Missing PAN"
    )
    db_session.add(log)
    db_session.commit()

    retrieved_log = db_session.query(DataIngestionLog).filter_by(file_name="customer_upload_errors.csv").first()
    assert retrieved_log is not None
    assert retrieved_log.status == "FAILED"
    assert retrieved_log.error_details == "Row 5: Invalid mobile number; Row 10: Missing PAN"

def test_customer_offers_relationship(db_session, app):
    """Test the one-to-many relationship from Customer to Offer."""
    Customer = app.Customer
    Offer = app.Offer
    customer = Customer(mobile_number="4444444444")
    db_session.add(customer)
    db_session.commit()

    offer1 = Offer(customer_id=customer.customer_id, offer_type="Fresh", offer_status="Active")
    offer2 = Offer(customer_id=customer.customer_id, offer_type="Enrich", offer_status="Expired")
    db_session.add_all([offer1, offer2])
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="4444444444").first()
    assert len(retrieved_customer.offers) == 2
    assert any(o.offer_type == "Fresh" for o in retrieved_customer.offers)
    assert any(o.offer_type == "Enrich" for o in retrieved_customer.offers)

def test_customer_events_relationship(db_session, app):
    """Test the one-to-many relationship from Customer to CustomerEvent."""
    Customer = app.Customer
    CustomerEvent = app.CustomerEvent
    customer = Customer(mobile_number="5555555555")
    db_session.add(customer)
    db_session.commit()

    event1 = CustomerEvent(customer_id=customer.customer_id, event_type="SMS_SENT", event_source="Moengage")
    event2 = CustomerEvent(customer_id=customer.customer_id, event_type="CONVERSION", event_source="LOS")
    db_session.add_all([event1, event2])
    db_session.commit()

    retrieved_customer = db_session.query(Customer).filter_by(mobile_number="5555555555").first()
    assert len(retrieved_customer.events) == 2
    assert any(e.event_type == "SMS_SENT" for e in retrieved_customer.events)
    assert any(e.event_type == "CONVERSION" for e in retrieved_customer.events)