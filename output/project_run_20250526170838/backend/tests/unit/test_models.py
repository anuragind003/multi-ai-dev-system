import pytest
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# --- Minimal Flask App and SQLAlchemy Setup for Testing ---
# These model definitions are included directly in the test file for self-containment
# and to make the test runnable without needing the full project structure.
# In a real project, these would be imported from `backend/src/models.py`.

db = SQLAlchemy()


class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True)
    pan_number = db.Column(db.Text, unique=True)
    aadhaar_number = db.Column(db.Text, unique=True)
    ucid_number = db.Column(db.Text, unique=True)
    loan_application_number = db.Column(db.Text, unique=True)
    dnd_flag = db.Column(db.Boolean, default=False)
    segment = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Customer {self.customer_id}>"


class Offer(db.Model):
    __tablename__ = 'offers'
    offer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text)
    offer_status = db.Column(db.Text)
    propensity = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    channel = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Offer {self.offer_id}>"


class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text)
    event_source = db.Column(db.Text)
    event_timestamp = db.Column(db.TIMESTAMP)
    # Use JSON for SQLite compatibility; JSONB would be used for PostgreSQL
    event_details = db.Column(db.JSON)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<Event {self.event_id}>"


class CampaignMetric(db.Model):
    __tablename__ = 'campaign_metrics'
    metric_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text)
    campaign_date = db.Column(db.Date)
    attempted_count = db.Column(db.Integer)
    sent_success_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    conversion_rate = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)

    def __repr__(self):
        return f"<CampaignMetric {self.metric_id}>"


class IngestionLog(db.Model):
    __tablename__ = 'ingestion_logs'
    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    status = db.Column(db.Text)
    error_description = db.Column(db.Text)

    def __repr__(self):
        return f"<IngestionLog {self.log_id}>"


# --- Pytest Fixtures ---

@pytest.fixture(scope='session')
def app():
    """
    Sets up a Flask app for testing with an in-memory SQLite database.
    This fixture runs once per test session.
    """
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()  # Create tables for all models
        yield app
        db.drop_all()  # Drop tables after all tests in the session are done


@pytest.fixture(scope='function')
def session(app):
    """
    Provides a fresh database session for each test function.
    Rolls back transactions after each test to ensure isolation.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.configure(bind=connection)

        # Clean up data from previous tests (if any, though transaction should handle it)
        # This ensures a clean slate for each test function.
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

        yield db.session

        db.session.rollback()  # Rollback the transaction to clean up
        connection.close()


# --- Tests for Customer Model ---

def test_customer_creation(session):
    """Test successful creation of a Customer record."""
    customer = Customer(
        mobile_number='1234567890',
        pan_number='ABCDE1234F',
        aadhaar_number='123456789012',
        ucid_number='UCID123',
        loan_application_number='LAN001',
        segment='C1'
    )
    session.add(customer)
    session.commit()

    retrieved_customer = Customer.query.filter_by(mobile_number='1234567890').first()
    assert retrieved_customer is not None
    assert retrieved_customer.customer_id is not None
    assert retrieved_customer.mobile_number == '1234567890'
    assert retrieved_customer.pan_number == 'ABCDE1234F'
    assert retrieved_customer.aadhaar_number == '123456789012'
    assert retrieved_customer.ucid_number == 'UCID123'
    assert retrieved_customer.loan_application_number == 'LAN001'
    assert retrieved_customer.dnd_flag is False
    assert retrieved_customer.segment == 'C1'
    assert retrieved_customer.created_at is not None
    assert retrieved_customer.updated_at is not None
    assert isinstance(retrieved_customer.created_at, datetime)
    assert isinstance(retrieved_customer.updated_at, datetime)


def test_customer_unique_constraints(session):
    """Test unique constraints for Customer fields."""
    # Create a base customer
    base_customer = Customer(
        mobile_number='1111111111',
        pan_number='PAN1111',
        aadhaar_number='AADHAAR1111',
        ucid_number='UCID1111',
        loan_application_number='LAN1111'
    )
    session.add(base_customer)
    session.commit()

    # Test mobile_number uniqueness
    with pytest.raises(IntegrityError):
        duplicate_mobile = Customer(mobile_number='1111111111', pan_number='PAN2222')
        session.add(duplicate_mobile)
        session.commit()
    session.rollback()  # Rollback the failed transaction

    # Test pan_number uniqueness
    with pytest.raises(IntegrityError):
        duplicate_pan = Customer(mobile_number='2222222222', pan_number='PAN1111')
        session.add(duplicate_pan)
        session.commit()
    session.rollback()

    # Test aadhaar_number uniqueness
    with pytest.raises(IntegrityError):
        duplicate_aadhaar = Customer(mobile_number='3333333333', aadhaar_number='AADHAAR1111')
        session.add(duplicate_aadhaar)
        session.commit()
    session.rollback()

    # Test ucid_number uniqueness
    with pytest.raises(IntegrityError):
        duplicate_ucid = Customer(mobile_number='4444444444', ucid_number='UCID1111')
        session.add(duplicate_ucid)
        session.commit()
    session.rollback()

    # Test loan_application_number uniqueness
    with pytest.raises(IntegrityError):
        duplicate_lan = Customer(mobile_number='5555555555', loan_application_number='LAN1111')
        session.add(duplicate_lan)
        session.commit()
    session.rollback()


def test_customer_dnd_flag_default(session):
    """Test that dnd_flag defaults to False."""
    customer = Customer(mobile_number='9876543210')
    session.add(customer)
    session.commit()
    retrieved_customer = Customer.query.filter_by(mobile_number='9876543210').first()
    assert retrieved_customer.dnd_flag is False


def test_customer_relationships_cascade_delete(session):
    """Test cascade delete for related Offers and Events."""
    customer = Customer(mobile_number='5555555555')
    session.add(customer)
    session.commit()

    offer = Offer(
        customer_id=customer.customer_id,
        offer_type='Fresh',
        offer_status='Active',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30)
    )
    event = Event(
        customer_id=customer.customer_id,
        event_type='SMS_SENT',
        event_source='Moengage',
        event_timestamp=datetime.utcnow(),
        event_details={'message': 'test'}
    )
    session.add_all([offer, event])
    session.commit()

    retrieved_customer = Customer.query.get(customer.customer_id)
    assert len(retrieved_customer.offers) == 1
    assert retrieved_customer.offers[0].offer_type == 'Fresh'
    assert len(retrieved_customer.events) == 1
    assert retrieved_customer.events[0].event_type == 'SMS_SENT'

    # Delete the customer and check if related records are deleted
    session.delete(retrieved_customer)
    session.commit()

    assert Customer.query.get(customer.customer_id) is None
    assert Offer.query.filter_by(customer_id=customer.customer_id).first() is None
    assert Event.query.filter_by(customer_id=customer.customer_id).first() is None


# --- Tests for Offer Model ---

def test_offer_creation(session):
    """Test successful creation of an Offer record."""
    customer = Customer(mobile_number='1112223334')
    session.add(customer)
    session.commit()

    offer = Offer(
        customer_id=customer.customer_id,
        offer_type='Fresh',
        offer_status='Active',
        propensity='High',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30),
        channel='Web'
    )
    session.add(offer)
    session.commit()

    retrieved_offer = Offer.query.filter_by(customer_id=customer.customer_id).first()
    assert retrieved_offer is not None
    assert retrieved_offer.offer_id is not None
    assert retrieved_offer.customer_id == customer.customer_id
    assert retrieved_offer.offer_type == 'Fresh'
    assert retrieved_offer.offer_status == 'Active'
    assert retrieved_offer.propensity == 'High'
    assert retrieved_offer.start_date == date.today()
    assert retrieved_offer.end_date == date.today() + timedelta(days=30)
    assert retrieved_offer.channel == 'Web'
    assert retrieved_offer.created_at is not None
    assert retrieved_offer.updated_at is not None
    assert isinstance(retrieved_offer.created_at, datetime)
    assert isinstance(retrieved_offer.updated_at, datetime)
    assert isinstance(retrieved_offer.start_date, date)
    assert isinstance(retrieved_offer.end_date, date)


def test_offer_foreign_key_constraint(session):
    """Test foreign key constraint for customer_id in Offer model."""
    # Attempt to create an offer with a non-existent customer_id
    non_existent_customer_id = str(uuid.uuid4())
    offer = Offer(
        customer_id=non_existent_customer_id,
        offer_type='Fresh',
        offer_status='Active',
        start_date=date.today(),
        end_date=date.today() + timedelta(days=30)
    )
    session.add(offer)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# --- Tests for Event Model ---

def test_event_creation(session):
    """Test successful creation of an Event record."""
    customer = Customer(mobile_number='4445556667')
    session.add(customer)
    session.commit()

    event_details = {'loan_amount': 100000, 'stage': 'EKYC'}
    event = Event(
        customer_id=customer.customer_id,
        event_type='LOAN_LOGIN',
        event_source='LOS',
        event_timestamp=datetime.utcnow(),
        event_details=event_details
    )
    session.add(event)
    session.commit()

    retrieved_event = Event.query.filter_by(customer_id=customer.customer_id).first()
    assert retrieved_event is not None
    assert retrieved_event.event_id is not None
    assert retrieved_event.customer_id == customer.customer_id
    assert retrieved_event.event_type == 'LOAN_LOGIN'
    assert retrieved_event.event_source == 'LOS'
    assert retrieved_event.event_timestamp is not None
    assert retrieved_event.event_details == event_details
    assert retrieved_event.created_at is not None
    assert isinstance(retrieved_event.created_at, datetime)
    assert isinstance(retrieved_event.event_timestamp, datetime)


def test_event_json_field(session):
    """Test storing and retrieving data from the JSON field."""
    customer = Customer(mobile_number='7778889990')
    session.add(customer)
    session.commit()

    complex_details = {
        'campaign_id': 'CMP001',
        'response': {'status': 'success', 'code': 200},
        'items': [1, 2, 3]
    }
    event = Event(
        customer_id=customer.customer_id,
        event_type='SMS_DELIVERED',
        event_source='Moengage',
        event_timestamp=datetime.utcnow(),
        event_details=complex_details
    )
    session.add(event)
    session.commit()

    retrieved_event = Event.query.filter_by(customer_id=customer.customer_id).first()
    assert retrieved_event.event_details == complex_details
    assert retrieved_event.event_details['response']['status'] == 'success'
    assert retrieved_event.event_details['items'][1] == 2


# --- Tests for CampaignMetric Model ---

def test_campaign_metric_creation(session):
    """Test successful creation of a CampaignMetric record."""
    metric = CampaignMetric(
        campaign_unique_id='CAMP_XYZ_20231027',
        campaign_name='Diwali Loan Offer',
        campaign_date=date(2023, 10, 27),
        attempted_count=10000,
        sent_success_count=9500,
        failed_count=500,
        conversion_rate=2.55
    )
    session.add(metric)
    session.commit()

    retrieved_metric = CampaignMetric.query.filter_by(campaign_unique_id='CAMP_XYZ_20231027').first()
    assert retrieved_metric is not None
    assert retrieved_metric.metric_id is not None
    assert retrieved_metric.campaign_unique_id == 'CAMP_XYZ_20231027'
    assert retrieved_metric.campaign_name == 'Diwali Loan Offer'
    assert retrieved_metric.campaign_date == date(2023, 10, 27)
    assert retrieved_metric.attempted_count == 10000
    assert retrieved_metric.sent_success_count == 9500
    assert retrieved_metric.failed_count == 500
    assert retrieved_metric.conversion_rate == 2.55
    assert retrieved_metric.created_at is not None
    assert isinstance(retrieved_metric.created_at, datetime)
    assert isinstance(retrieved_metric.campaign_date, date)


def test_campaign_metric_unique_id_constraint(session):
    """Test unique constraint for campaign_unique_id."""
    metric1 = CampaignMetric(campaign_unique_id='UNIQUE_CAMP_001', campaign_name='Test1')
    session.add(metric1)
    session.commit()

    metric2 = CampaignMetric(campaign_unique_id='UNIQUE_CAMP_001', campaign_name='Test2')
    session.add(metric2)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


def test_campaign_metric_nullable_campaign_name(session):
    """Test that campaign_name can be null (not specified as NOT NULL)."""
    metric = CampaignMetric(
        campaign_unique_id='CAMP_NULL_NAME',
        campaign_date=date.today(),
        attempted_count=100,
        sent_success_count=90,
        failed_count=10,
        conversion_rate=1.0
    )
    session.add(metric)
    session.commit()
    retrieved_metric = CampaignMetric.query.filter_by(campaign_unique_id='CAMP_NULL_NAME').first()
    assert retrieved_metric.campaign_name is None


# --- Tests for IngestionLog Model ---

def test_ingestion_log_creation(session):
    """Test successful creation of an IngestionLog record."""
    log = IngestionLog(
        file_name='customer_upload_20231027.csv',
        status='SUCCESS',
        error_description=None
    )
    session.add(log)
    session.commit()

    retrieved_log = IngestionLog.query.filter_by(file_name='customer_upload_20231027.csv').first()
    assert retrieved_log is not None
    assert retrieved_log.log_id is not None
    assert retrieved_log.file_name == 'customer_upload_20231027.csv'
    assert retrieved_log.status == 'SUCCESS'
    assert retrieved_log.error_description is None
    assert retrieved_log.upload_timestamp is not None
    assert isinstance(retrieved_log.upload_timestamp, datetime)


def test_ingestion_log_with_error(session):
    """Test creation of an IngestionLog record with an error description."""
    log = IngestionLog(
        file_name='customer_upload_error.csv',
        status='FAILED',
        error_description='Missing required column: mobile_number'
    )
    session.add(log)
    session.commit()

    retrieved_log = IngestionLog.query.filter_by(file_name='customer_upload_error.csv').first()
    assert retrieved_log.status == 'FAILED'
    assert retrieved_log.error_description == 'Missing required column: mobile_number'


def test_ingestion_log_file_name_not_null(session):
    """Test that file_name cannot be null."""
    log = IngestionLog(status='SUCCESS')
    session.add(log)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()