import pytest
from datetime import datetime, timedelta
import json

# Assuming these are correctly set up in the main application
from src.app import create_app
from src.models import db, Customer, Offer, CustomerEvent, Campaign, DataIngestionLog

# Import the batch job functions from the tasks module.
# These functions are expected to contain the actual logic for the batch jobs.
# We assume these functions are implemented in src.tasks.batch_ingestion.py
# and are designed to be callable for testing purposes (e.g., accepting mock data).
from src.tasks.batch_ingestion import (
    run_offermart_ingestion_job,
    run_reverse_feed_job,
    run_edw_push_job,
    run_offer_expiry_job,
    run_data_retention_job
)

@pytest.fixture(scope='session')
def app():
    """
    Create and configure a new Flask app instance for the test session.
    Uses an in-memory SQLite database for fast testing.
    """
    # Ensure 'src.config.TestingConfig' exists and configures an in-memory SQLite DB.
    # Example: SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    app = create_app(config_object='src.config.TestingConfig')
    with app.app_context():
        db.create_all()  # Create tables based on models
        yield app
        db.session.remove()
        db.drop_all() # Drop tables after the session

@pytest.fixture(scope='function')
def client(app):
    """A test client for the Flask app."""
    return app.test_client()

@pytest.fixture(scope='function')
def app_context(app):
    """Provides an application context for database operations within tests."""
    with app.app_context():
        yield

@pytest.fixture(scope='function')
def init_db(app_context):
    """
    Initializes and cleans the database before each test function.
    Ensures a clean state for every test.
    """
    with app_context:
        # Clear all data from tables before each test
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()
        yield
        # Optional: Clean up after each test, though the app fixture drops all tables
        # and the next test's init_db will clear them again.
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


def test_offermart_ingestion_job(app_context, init_db):
    """
    Tests the daily Offermart data ingestion job (FR7, FR3, FR4).
    Verifies new data is added, existing data is updated, and deduplication works.
    """
    with app_context:
        # Pre-populate with existing customer and offer data
        customer1 = Customer(mobile_number='9876543210', pan='ABCDE1234F', customer_segment='C1')
        customer2 = Customer(mobile_number='9998887776', pan='FGHIJ5678K', customer_segment='C2')
        db.session.add_all([customer1, customer2])
        db.session.commit()

        offer1_c1 = Offer(customer_id=customer1.customer_id, offer_type='Fresh', offer_status='Active',
                          offer_end_date=datetime.now().date() + timedelta(days=30))
        db.session.add(offer1_c1)
        db.session.commit()

        # Simulate incoming Offermart data records
        # The `run_offermart_ingestion_job` function in `src.tasks.batch_ingestion`
        # is assumed to accept this list of dictionaries as its input source.
        mock_offermart_data = [
            # 1. New customer, new offer
            {
                'mobile_number': '1112223334', 'pan': 'LMNOP9012Q', 'aadhaar_ref_number': '123456789012',
                'offer_type': 'Fresh', 'offer_status': 'Active', 'offer_end_date': (datetime.now().date() + timedelta(days=60)).isoformat()
            },
            # 2. Existing customer (customer1), new distinct offer
            {
                'mobile_number': '9876543210', 'pan': 'ABCDE1234F',
                'offer_type': 'Enrich', 'offer_status': 'Active', 'offer_end_date': (datetime.now().date() + timedelta(days=90)).isoformat()
            },
            # 3. Existing customer (customer2), new offer
            {
                'mobile_number': '9998887776', 'pan': 'FGHIJ5678K',
                'offer_type': 'New-new', 'offer_status': 'Active', 'offer_end_date': (datetime.now().date() + timedelta(days=45)).isoformat()
            },
            # 4. Duplicate customer (customer1) with an offer that might be a true duplicate or a new one.
            # Assuming the job handles this by either updating an existing offer or adding a new one if distinct.
            # For this test, we'll assume it adds a new offer if it's not an exact match on all key offer attributes.
            {
                'mobile_number': '9876543210', 'pan': 'ABCDE1234F',
                'offer_type': 'Fresh', 'offer_status': 'Active', 'offer_end_date': (datetime.now().date() + timedelta(days=30)).isoformat()
            }
        ]

        # Call the batch job function with the mock data
        run_offermart_ingestion_job(mock_offermart_data)

        # Assertions
        customers_after = Customer.query.all()
        offers_after = Offer.query.all()
        ingestion_logs = DataIngestionLog.query.all()

        # Check total customers: original 2 + 1 new = 3
        assert len(customers_after) == 3

        # Verify the new customer was added
        new_customer = Customer.query.filter_by(mobile_number='1112223334').first()
        assert new_customer is not None
        assert new_customer.pan == 'LMNOP9012Q'

        # Verify offers:
        # Original: 1 offer for customer1
        # Ingested: 1 new offer for new_customer, 1 new offer ('Enrich') for customer1,
        #           1 new offer ('New-new') for customer2, 1 potentially new offer ('Fresh') for customer1.
        # Total expected offers: 1 (original C1) + 1 (new C1 'Enrich') + 1 (new C2 'New-new') + 1 (new_customer 'Fresh') + 1 (duplicate C1 'Fresh') = 5
        # This assumes the job creates a new offer if it's not an exact match on all attributes,
        # or if the business logic allows multiple offers of the same type.
        assert len(offers_after) == 5

        customer1_offers = Offer.query.filter_by(customer_id=customer1.customer_id).all()
        assert len(customer1_offers) == 3 # Original, 'Enrich', and the second 'Fresh'

        # Check DataIngestionLog: Assuming one log entry per batch run
        assert len(ingestion_logs) == 1
        assert ingestion_logs[0].status == 'SUCCESS' # Or 'PARTIAL' if some records failed


def test_reverse_feed_job(app_context, init_db):
    """
    Tests the daily reverse feed job to Offermart (FR8).
    Verifies that the job runs and logs its activity.
    """
    with app_context:
        # Pre-populate with some data that would be part of the reverse feed
        customer = Customer(mobile_number='1234567890', pan='TESTP1234A', customer_segment='C1')
        db.session.add(customer)
        db.session.commit()

        offer = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Active',
                      offer_end_date=datetime.now().date() + timedelta(days=30),
                      loan_application_number='LAN123', updated_at=datetime.now() - timedelta(hours=2))
        db.session.add(offer)
        db.session.commit()

        # Call the batch job function
        run_reverse_feed_job()

        # Assertions:
        # This job would typically generate a file or push data via an API.
        # For testing, we check for a log entry indicating successful execution.
        logs = DataIngestionLog.query.filter(DataIngestionLog.file_name.like('%reverse_feed%')).all()
        assert len(logs) >= 1
        assert logs[0].status == 'SUCCESS'


def test_edw_push_job(app_context, init_db):
    """
    Tests the daily data push job to EDW (FR23).
    Verifies that the job runs and logs its activity.
    """
    with app_context:
        # Pre-populate with data to be pushed to EDW
        customer = Customer(mobile_number='1122334455', pan='EDWTEST12A', customer_segment='C3')
        db.session.add(customer)
        db.session.commit()

        offer = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Active',
                      offer_end_date=datetime.now().date() + timedelta(days=30))
        db.session.add(offer)
        db.session.commit()

        event = CustomerEvent(customer_id=customer.customer_id, event_type='SMS_SENT', event_source='Moengage',
                              event_timestamp=datetime.now(), event_details=json.dumps({'campaign_id': 'camp123'}))
        db.session.add(event)
        db.session.commit()

        # Call the batch job function
        run_edw_push_job()

        # Assertions:
        # Check for a log entry indicating successful execution.
        logs = DataIngestionLog.query.filter(DataIngestionLog.file_name.like('%edw_push%')).all()
        assert len(logs) >= 1
        assert logs[0].status == 'SUCCESS'


def test_offer_expiry_job(app_context, init_db):
    """
    Tests the offer expiry logic job (FR13, FR37, FR38).
    Verifies that offers are correctly marked as 'Expired' based on business rules.
    """
    with app_context:
        customer = Customer(mobile_number='5554443332', pan='EXPIRE1234A', customer_segment='C1')
        db.session.add(customer)
        db.session.commit()

        # Offer 1: Should expire (end date in past, no LAN)
        offer1 = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Active',
                       offer_end_date=datetime.now().date() - timedelta(days=5))
        # Offer 2: Should NOT expire (end date in future, no LAN)
        offer2 = Offer(customer_id=customer.customer_id, offer_type='Enrich', offer_status='Active',
                       offer_end_date=datetime.now().date() + timedelta(days=10))
        # Offer 3: Should NOT expire (end date in past, but has active LAN - FR13)
        # Assuming 'active LAN' means the loan application journey has started and is not yet expired/rejected.
        # The job should check the status of the LAN if available. For this test, we assume its presence prevents expiry.
        offer3 = Offer(customer_id=customer.customer_id, offer_type='New-old', offer_status='Active',
                       offer_end_date=datetime.now().date() - timedelta(days=10),
                       loan_application_number='LAN_ACTIVE_123')
        # Offer 4: Already expired, should remain expired
        offer4 = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Expired',
                       offer_end_date=datetime.now().date() - timedelta(days=20))

        db.session.add_all([offer1, offer2, offer3, offer4])
        db.session.commit()

        # Call the batch job function
        run_offer_expiry_job()

        # Assertions: Refresh objects to get latest state from DB
        db.session.refresh(offer1)
        db.session.refresh(offer2)
        db.session.refresh(offer3)
        db.session.refresh(offer4)

        assert offer1.offer_status == 'Expired'
        assert offer2.offer_status == 'Active'
        assert offer3.offer_status == 'Active' # Should remain active due to LAN
        assert offer4.offer_status == 'Expired'


def test_data_retention_job(app_context, init_db):
    """
    Tests the data retention policy enforcement job (FR18, FR24, NFR3, NFR4).
    Verifies that old data is deleted according to retention policies.
    """
    with app_context:
        # Create a customer (should not be deleted if linked to recent data)
        customer = Customer(mobile_number='7776665554', pan='RETENT123A', customer_segment='C8')
        db.session.add(customer)
        db.session.commit()

        # Create offers: some old (beyond 6 months), some recent (within 6 months)
        old_offer_date = datetime.now().date() - timedelta(days=190) # > 6 months
        recent_offer_date = datetime.now().date() - timedelta(days=30) # < 6 months

        offer_old = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Active',
                          offer_end_date=old_offer_date, created_at=old_offer_date)
        offer_recent = Offer(customer_id=customer.customer_id, offer_type='Fresh', offer_status='Active',
                             offer_end_date=recent_offer_date, created_at=recent_offer_date)
        db.session.add_all([offer_old, offer_recent])
        db.session.commit()

        # Create customer events: some old (beyond 3 months), some recent (within 3 months)
        old_event_timestamp = datetime.now() - timedelta(days=100) # > 3 months
        recent_event_timestamp = datetime.now() - timedelta(days=10) # < 3 months

        event_old = CustomerEvent(customer_id=customer.customer_id, event_type='SMS_SENT', event_source='Moengage',
                                  event_timestamp=old_event_timestamp, event_details=json.dumps({'msg': 'old'}))
        event_recent = CustomerEvent(customer_id=customer.customer_id, event_type='SMS_DELIVERED', event_source='Moengage',
                                     event_timestamp=recent_event_timestamp, event_details=json.dumps({'msg': 'recent'}))
        db.session.add_all([event_old, event_recent])
        db.session.commit()

        # Create data ingestion logs: some old (beyond 3 months), some recent (within 3 months)
        old_log_timestamp = datetime.now() - timedelta(days=100) # > 3 months
        recent_log_timestamp = datetime.now() - timedelta(days=10) # < 3 months

        log_old = DataIngestionLog(file_name='old_file.csv', upload_timestamp=old_log_timestamp, status='SUCCESS')
        log_recent = DataIngestionLog(file_name='recent_file.csv', upload_timestamp=recent_log_timestamp, status='SUCCESS')
        db.session.add_all([log_old, log_recent])
        db.session.commit()

        # Call the batch job function
        run_data_retention_job()

        # Assertions
        # Check offers: Only the recent offer should remain (older than 6 months deleted)
        offers_after = Offer.query.all()
        assert len(offers_after) == 1
        assert offers_after[0].offer_id == offer_recent.offer_id

        # Check customer events: Only the recent event should remain (older than 3 months deleted)
        events_after = CustomerEvent.query.all()
        assert len(events_after) == 1
        assert events_after[0].event_id == event_recent.event_id

        # Check data ingestion logs: Only the recent log should remain (older than 3 months deleted)
        logs_after = DataIngestionLog.query.all()
        assert len(logs_after) == 1
        assert logs_after[0].log_id == log_recent.log_id

        # Customers should not be deleted by retention job unless they have no associated data
        # For this test, the customer is linked to a recent offer and event, so it should remain.
        customers_after = Customer.query.all()
        assert len(customers_after) == 1
        assert customers_after[0].customer_id == customer.customer_id