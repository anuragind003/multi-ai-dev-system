import pytest
from datetime import datetime, timedelta
import uuid
import json

# --- Minimal Flask App and SQLAlchemy Models for Testing Context ---
# In a real project, these would be imported from backend/app.py and backend/models.py.
# For the purpose of making this test file runnable in isolation,
# we define minimal versions here.

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Text, primary_key=True)
    mobile_number = db.Column(db.Text, unique=True)
    pan_number = db.Column(db.Text, unique=True)
    aadhaar_number = db.Column(db.Text, unique=True)
    ucid_number = db.Column(db.Text, unique=True)
    loan_application_number = db.Column(db.Text, unique=True)
    dnd_flag = db.Column(db.Boolean, default=False)
    segment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    offers = db.relationship('Offer', backref='customer', lazy=True, cascade="all, delete-orphan")
    events = db.relationship('Event', backref='customer', lazy=True, cascade="all, delete-orphan")

class Offer(db.Model):
    __tablename__ = 'offers'
    offer_id = db.Column(db.Text, primary_key=True)
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    offer_type = db.Column(db.Text)
    offer_status = db.Column(db.Text)
    propensity = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    channel = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Event(db.Model):
    __tablename__ = 'events'
    event_id = db.Column(db.Text, primary_key=True)
    customer_id = db.Column(db.Text, db.ForeignKey('customers.customer_id'), nullable=False)
    event_type = db.Column(db.Text)
    event_source = db.Column(db.Text)
    event_timestamp = db.Column(db.DateTime)
    event_details = db.Column(db.JSON) # Use JSON for SQLite, JSONB for PostgreSQL
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CampaignMetric(db.Model):
    __tablename__ = 'campaign_metrics'
    metric_id = db.Column(db.Text, primary_key=True)
    campaign_unique_id = db.Column(db.Text, unique=True, nullable=False)
    campaign_name = db.Column(db.Text)
    campaign_date = db.Column(db.Date)
    attempted_count = db.Column(db.Integer)
    sent_success_count = db.Column(db.Integer)
    failed_count = db.Column(db.Integer)
    conversion_rate = db.Column(db.Numeric(5, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class IngestionLog(db.Model):
    __tablename__ = 'ingestion_logs'
    log_id = db.Column(db.Text, primary_key=True)
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Text)
    error_description = db.Column(db.Text)

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

# --- End Minimal Flask App and SQLAlchemy Models ---


# --- Scheduled Job Functions (would typically be in backend/jobs/scheduled_tasks.py) ---

def update_offer_statuses():
    """
    Simulates the scheduled job to update offer statuses based on expiry logic.
    FR41: Mark offers as expired based on offer end dates for non-journey started customers.
    FR43: Mark offers as expired for journey started customers whose LAN validity is over.
    """
    now = datetime.utcnow()

    # FR41: Expire offers for non-journey started customers
    # Find active offers with end_date in the past, where the customer has no associated events.
    offers_to_expire_no_journey = db.session.query(Offer).join(Customer).filter(
        Offer.offer_status == 'Active',
        Offer.end_date < now.date(),
        ~db.session.query(Event).filter(Event.customer_id == Customer.customer_id).exists()
    ).all()

    for offer in offers_to_expire_no_journey:
        offer.offer_status = 'Expired'
        offer.updated_at = now

    # FR43: Expire offers for journey started customers whose LAN validity is over
    # For testing, we'll assume if an offer has a loan_application_number and its end_date is past,
    # it should be expired, as the LAN itself implies a journey.
    offers_to_expire_journey_started = db.session.query(Offer).join(Customer).filter(
        Offer.offer_status == 'Active',
        Offer.end_date < now.date(),
        Customer.loan_application_number.isnot(None)
    ).all()

    for offer in offers_to_expire_journey_started:
        offer.offer_status = 'Expired'
        offer.updated_at = now

    db.session.commit()


def cleanup_old_data():
    """
    Simulates the scheduled job to clean up old data based on retention policies.
    FR19, NFR8: Maintain Offer history for the past 6 months. (Delete offers older than 6 months)
    FR28, NFR9: Maintain all data in LTFS Offer CDP for previous 3 months before deletion.
    (Delete customers, events, campaign_metrics, ingestion_logs older than 3 months)
    """
    now = datetime.utcnow()
    six_months_ago = now - timedelta(days=6 * 30)
    three_months_ago = now - timedelta(days=3 * 30)

    # FR19, NFR8: Delete offers older than 6 months
    # Offers are deleted first as they have a longer retention period than other data types
    # and to avoid FK issues when deleting customers.
    Offer.query.filter(Offer.created_at < six_months_ago).delete(synchronize_session=False)

    # FR28, NFR9: Delete all data (events, campaign_metrics, ingestion_logs) older than 3 months
    Event.query.filter(Event.created_at < three_months_ago).delete(synchronize_session=False)
    CampaignMetric.query.filter(CampaignMetric.created_at < three_months_ago).delete(synchronize_session=False)
    IngestionLog.query.filter(IngestionLog.upload_timestamp < three_months_ago).delete(synchronize_session=False)

    # Delete old customers
    # A customer should only be deleted if ALL their associated data (offers, events)
    # are also older than 3 months.
    customers_to_delete_query = db.session.query(Customer.customer_id).filter(
        Customer.created_at < three_months_ago,
        ~db.session.query(Offer).filter(
            Offer.customer_id == Customer.customer_id,
            Offer.created_at >= three_months_ago
        ).exists(),
        ~db.session.query(Event).filter(
            Event.customer_id == Customer.customer_id,
            Event.created_at >= three_months_ago
        ).exists()
    )
    Customer.query.filter(Customer.customer_id.in_(customers_to_delete_query)).delete(synchronize_session=False)

    db.session.commit()


# --- Pytest Fixtures ---

@pytest.fixture(scope='module')
def app():
    """
    Fixture to create and configure the Flask app for testing.
    Uses an in-memory SQLite database for speed and isolation.
    """
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """
    Fixture for a Flask test client.
    Ensures a clean database state for each test function.
    """
    with app.app_context():
        # Clear data before each test
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield app.test_client()
        db.session.rollback() # Rollback any uncommitted changes after test


# --- Test Cases ---

def test_offer_status_update_job_no_journey_expired(client):
    """
    Tests FR41: Mark offers as expired based on offer end dates for non-journey started customers.
    """
    with client.application.app_context():
        customer_id = str(uuid.uuid4())
        customer = Customer(
            customer_id=customer_id,
            mobile_number='1234567890',
            pan_number='ABCDE1234F',
            created_at=datetime.utcnow()
        )
        db.session.add(customer)
        db.session.commit()

        offer_id = str(uuid.uuid4())
        past_date = datetime.utcnow().date() - timedelta(days=10)
        offer = Offer(
            offer_id=offer_id,
            customer_id=customer_id,
            offer_status='Active',
            end_date=past_date,
            created_at=datetime.utcnow()
        )
        db.session.add(offer)
        db.session.commit()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Active'

        update_offer_statuses()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Expired'


def test_offer_status_update_job_journey_started_lan_expired(client):
    """
    Tests FR43: Mark offers as expired for journey started customers whose LAN validity is over.
    """
    with client.application.app_context():
        customer_id = str(uuid.uuid4())
        customer = Customer(
            customer_id=customer_id,
            mobile_number='0987654321',
            pan_number='FGHIJ5678K',
            loan_application_number='LAN12345',
            created_at=datetime.utcnow()
        )
        db.session.add(customer)
        db.session.commit()

        offer_id = str(uuid.uuid4())
        past_date = datetime.utcnow().date() - timedelta(days=5)
        offer = Offer(
            offer_id=offer_id,
            customer_id=customer_id,
            offer_status='Active',
            end_date=past_date,
            created_at=datetime.utcnow()
        )
        db.session.add(offer)
        db.session.commit()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Active'

        update_offer_statuses()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Expired'


def test_offer_status_update_job_no_expiry_needed(client):
    """
    Tests that active offers with future end dates are not expired.
    """
    with client.application.app_context():
        customer_id = str(uuid.uuid4())
        customer = Customer(
            customer_id=customer_id,
            mobile_number='1112223333',
            pan_number='KLMNO9876P',
            created_at=datetime.utcnow()
        )
        db.session.add(customer)
        db.session.commit()

        offer_id = str(uuid.uuid4())
        future_date = datetime.utcnow().date() + timedelta(days=30)
        offer = Offer(
            offer_id=offer_id,
            customer_id=customer_id,
            offer_status='Active',
            end_date=future_date,
            created_at=datetime.utcnow()
        )
        db.session.add(offer)
        db.session.commit()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Active'

        update_offer_statuses()

        retrieved_offer = Offer.query.get(offer_id)
        assert retrieved_offer.offer_status == 'Active'


def test_cleanup_old_data_offers_6_months(client):
    """
    Tests FR19, NFR8: Deletion of offers older than 6 months.
    """
    with client.application.app_context():
        customer_id = str(uuid.uuid4())
        customer = Customer(
            customer_id=customer_id,
            mobile_number='2223334444',
            pan_number='QRSTU1234V',
            created_at=datetime.utcnow() - timedelta(days=200)
        )
        db.session.add(customer)
        db.session.commit()

        old_offer_id = str(uuid.uuid4())
        old_offer = Offer(
            offer_id=old_offer_id,
            customer_id=customer_id,
            offer_status='Expired',
            created_at=datetime.utcnow() - timedelta(days=190)
        )
        db.session.add(old_offer)

        recent_offer_id = str(uuid.uuid4())
        recent_offer = Offer(
            offer_id=recent_offer_id,
            customer_id=customer_id,
            offer_status='Active',
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(recent_offer)
        db.session.commit()

        assert Offer.query.count() == 2

        cleanup_old_data()

        assert Offer.query.count() == 1
        assert Offer.query.get(old_offer_id) is None
        assert Offer.query.get(recent_offer_id) is not None


def test_cleanup_old_data_all_data_3_months_with_recent_customer_data(client):
    """
    Tests FR28, NFR9: Deletion of all data (events, campaign_metrics, ingestion_logs)
    older than 3 months, and ensures customers with recent associated data are NOT deleted.
    """
    with client.application.app_context():
        # Customer whose created_at is old, but has a recent offer/event
        customer_id_with_recent_data = str(uuid.uuid4())
        customer_with_recent_data = Customer(
            customer_id=customer_id_with_recent_data,
            mobile_number='3334445555',
            pan_number='WXYZA5678B',
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(customer_with_recent_data)

        # Old event (should be deleted)
        old_event_id = str(uuid.uuid4())
        old_event = Event(
            event_id=old_event_id,
            customer_id=customer_id_with_recent_data,
            event_type='SMS_SENT',
            event_source='Moengage',
            event_timestamp=datetime.utcnow() - timedelta(days=100),
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(old_event)

        # Recent event (should prevent customer deletion)
        recent_event_id = str(uuid.uuid4())
        recent_event = Event(
            event_id=recent_event_id,
            customer_id=customer_id_with_recent_data,
            event_type='EKYC_ACHIEVED',
            event_source='LOS',
            event_timestamp=datetime.utcnow() - timedelta(days=10),
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db.session.add(recent_event)

        # Old campaign metric (should be deleted)
        old_campaign_metric_id = str(uuid.uuid4())
        old_campaign_metric = CampaignMetric(
            metric_id=old_campaign_metric_id,
            campaign_unique_id='OLD_CAMPAIGN_1',
            campaign_date=datetime.utcnow().date() - timedelta(days=100),
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(old_campaign_metric)

        # Recent campaign metric (should be retained)
        recent_campaign_metric_id = str(uuid.uuid4())
        recent_campaign_metric = CampaignMetric(
            metric_id=recent_campaign_metric_id,
            campaign_unique_id='RECENT_CAMPAIGN_1',
            campaign_date=datetime.utcnow().date() - timedelta(days=10),
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db.session.add(recent_campaign_metric)

        # Old ingestion log (should be deleted)
        old_ingestion_log_id = str(uuid.uuid4())
        old_ingestion_log = IngestionLog(
            log_id=old_ingestion_log_id,
            file_name='old_data.csv',
            upload_timestamp=datetime.utcnow() - timedelta(days=100),
            status='SUCCESS'
        )
        db.session.add(old_ingestion_log)

        # Recent ingestion log (should be retained)
        recent_ingestion_log_id = str(uuid.uuid4())
        recent_ingestion_log = IngestionLog(
            log_id=recent_ingestion_log_id,
            file_name='recent_data.csv',
            upload_timestamp=datetime.utcnow() - timedelta(days=10),
            status='SUCCESS'
        )
        db.session.add(recent_ingestion_log)

        # Old offer (older than 6 months, should be deleted by 6-month rule)
        old_offer_id = str(uuid.uuid4())
        old_offer = Offer(
            offer_id=old_offer_id,
            customer_id=customer_id_with_recent_data,
            offer_status='Expired',
            created_at=datetime.utcnow() - timedelta(days=190)
        )
        db.session.add(old_offer)

        # Recent offer (younger than 3 months, should prevent customer deletion)
        recent_offer_id = str(uuid.uuid4())
        recent_offer = Offer(
            offer_id=recent_offer_id,
            customer_id=customer_id_with_recent_data,
            offer_status='Active',
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db.session.add(recent_offer)
        db.session.commit()

        # Initial counts
        assert Customer.query.count() == 1
        assert Offer.query.count() == 2
        assert Event.query.count() == 2
        assert CampaignMetric.query.count() == 2
        assert IngestionLog.query.count() == 2

        cleanup_old_data()

        # Assertions for 6-month offer deletion
        assert Offer.query.get(old_offer_id) is None
        assert Offer.query.get(recent_offer_id) is not None

        # Assertions for 3-month data deletion
        assert Event.query.get(old_event_id) is None
        assert Event.query.get(recent_event_id) is not None

        assert CampaignMetric.query.get(old_campaign_metric_id) is None
        assert CampaignMetric.query.get(recent_campaign_metric_id) is not None

        assert IngestionLog.query.get(old_ingestion_log_id) is None
        assert IngestionLog.query.get(recent_ingestion_log_id) is not None

        # Customer should NOT be deleted because it has recent offer/event
        assert Customer.query.get(customer_id_with_recent_data) is not None
        assert Customer.query.count() == 1


def test_cleanup_old_data_customer_with_no_recent_data_deleted(client):
    """
    Tests that a customer and all their associated data are deleted if all are older than 3 months.
    """
    with client.application.app_context():
        # Customer and all associated data older than 3 months
        old_customer_id = str(uuid.uuid4())
        old_customer = Customer(
            customer_id=old_customer_id,
            mobile_number='5556667777',
            pan_number='HIJKL3456M',
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(old_customer)

        old_offer_id = str(uuid.uuid4())
        old_offer = Offer(
            offer_id=old_offer_id,
            customer_id=old_customer_id,
            offer_status='Expired',
            created_at=datetime.utcnow() - timedelta(days=190)
        )
        db.session.add(old_offer)

        old_event_id = str(uuid.uuid4())
        old_event = Event(
            event_id=old_event_id,
            customer_id=old_customer_id,
            event_type='LOAN_LOGIN',
            event_source='LOS',
            event_timestamp=datetime.utcnow() - timedelta(days=100),
            created_at=datetime.utcnow() - timedelta(days=100)
        )
        db.session.add(old_event)
        db.session.commit()

        assert Customer.query.count() == 1
        assert Offer.query.count() == 1
        assert Event.query.count() == 1

        cleanup_old_data()

        assert Customer.query.get(old_customer_id) is None
        assert Offer.query.get(old_offer_id) is None
        assert Event.query.get(old_event_id) is None

        assert Customer.query.count() == 0
        assert Offer.query.count() == 0
        assert Event.query.count() == 0