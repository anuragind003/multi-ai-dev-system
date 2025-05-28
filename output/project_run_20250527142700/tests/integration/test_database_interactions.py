import pytest
import os
from datetime import datetime, date, timedelta
import uuid

# Adjust import path based on your actual project structure
# Assuming app, db, and models are defined in src/app.py
from src.app import app, db, Customer, Offer, CustomerEvent, Campaign, DataIngestionLog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

@pytest.fixture(scope='session')
def flask_app():
    """
    Configures the Flask app for testing and yields the app context.
    This fixture runs once per test session.
    """
    app.config['TESTING'] = True
    # Use a separate test database for integration tests
    # Ensure this database exists and is accessible for testing
    # For example, create a database named 'cdp_test_db' in your PostgreSQL instance.
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'TEST_DATABASE_URL',
        'postgresql://user:password@localhost:5432/cdp_test_db' # Replace with your test DB credentials
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        # Create all tables in the test database
        db.create_all()
        yield app
        # Drop all tables after the session tests are complete
        db.drop_all()

@pytest.fixture(scope='function')
def client(flask_app):
    """
    Provides a test client for each test function.
    Ensures a clean database state for each test by clearing data.
    """
    with flask_app.app_context():
        # Clean up data before each test function
        # This ensures tests are isolated and don't affect each other
        # Delete from tables in reverse order to handle foreign key constraints
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()

        yield flask_app.test_client()

        # Clean up data after each test function
        db.session.remove() # Remove session to prevent lingering connections/transactions
        db.session.rollback() # Rollback any uncommitted transactions
        # Re-delete data to ensure clean state if a test failed mid-transaction
        for table in reversed(db.metadata.sorted_tables):
            db.session.execute(table.delete())
        db.session.commit()


# Placeholder tests for database interactions

def test_customer_creation_and_retrieval(client):
    """
    Test that a customer can be successfully created and retrieved from the database.
    (FR2, FR33)
    """
    with app.app_context():
        mobile_number = '9876543210'
        pan = 'ABCDE1234F'
        new_customer = Customer(
            mobile_number=mobile_number,
            pan=pan,
            customer_segment='C1',
            customer_attributes={'age': 30, 'city': 'Mumbai'}
        )
        db.session.add(new_customer)
        db.session.commit()

        retrieved_customer = Customer.query.filter_by(mobile_number=mobile_number).first()
        assert retrieved_customer is not None
        assert retrieved_customer.pan == pan
        assert retrieved_customer.customer_segment == 'C1'
        assert retrieved_customer.customer_attributes['city'] == 'Mumbai'
        assert retrieved_customer.customer_id is not None

def test_offer_association_with_customer(client):
    """
    Test that an offer can be associated with an existing customer.
    (FR15, FR16, FR33)
    """
    with app.app_context():
        customer = Customer(mobile_number='9988776655', pan='FGHIJ5678K')
        db.session.add(customer)
        db.session.commit()

        new_offer = Offer(
            customer_id=customer.customer_id,
            offer_type='Fresh',
            offer_status='Active',
            propensity_flag='dominant tradeline',
            offer_start_date=date.today(),
            offer_end_date=date.today() + timedelta(days=30)
        )
        db.session.add(new_offer)
        db.session.commit()

        retrieved_offer = Offer.query.filter_by(customer_id=customer.customer_id).first()
        assert retrieved_offer is not None
        assert retrieved_offer.offer_type == 'Fresh'
        assert retrieved_offer.offer_status == 'Active'
        assert retrieved_offer.propensity_flag == 'dominant tradeline'
        assert retrieved_offer.customer.mobile_number == '9988776655'
        assert retrieved_offer.offer_id is not None

def test_customer_event_logging(client):
    """
    Test that customer events can be logged and retrieved.
    (FR21, FR22)
    """
    with app.app_context():
        customer = Customer(mobile_number='1122334455', pan='LMNOP9012Q')
        db.session.add(customer)
        db.session.commit()

        event = CustomerEvent(
            customer_id=customer.customer_id,
            event_type='SMS_SENT',
            event_source='Moengage',
            event_details={'campaign_id': 'CMP001', 'message': 'Your offer is here!'}
        )
        db.session.add(event)
        db.session.commit()

        retrieved_event = CustomerEvent.query.filter_by(customer_id=customer.customer_id).first()
        assert retrieved_event is not None
        assert retrieved_event.event_type == 'SMS_SENT'
        assert retrieved_event.event_source == 'Moengage'
        assert retrieved_event.event_details['campaign_id'] == 'CMP001'
        assert retrieved_event.event_id is not None

def test_data_ingestion_log_entry(client):
    """
    Test that a data ingestion log entry can be created.
    (FR31, FR32)
    """
    with app.app_context():
        file_name = 'offermart_daily_feed_20231027.csv'
        log_entry = DataIngestionLog(
            file_name=file_name,
            status='SUCCESS',
            uploaded_by='system_user'
        )
        db.session.add(log_entry)
        db.session.commit()

        retrieved_log = DataIngestionLog.query.filter_by(file_name=file_name).first()
        assert retrieved_log is not None
        assert retrieved_log.status == 'SUCCESS'
        assert retrieved_log.uploaded_by == 'system_user'
        assert retrieved_log.log_id is not None

def test_campaign_data_storage(client):
    """
    Test that campaign data can be stored and retrieved.
    (FR34)
    """
    with app.app_context():
        campaign_uid = 'CMP_LOAN_NOV23'
        campaign = Campaign(
            campaign_unique_identifier=campaign_uid,
            campaign_name='November Personal Loan Campaign',
            campaign_date=date(2023, 11, 1),
            targeted_customers_count=10000,
            attempted_count=9500,
            successfully_sent_count=9000,
            failed_count=500,
            success_rate=94.74,
            conversion_rate=2.50
        )
        db.session.add(campaign)
        db.session.commit()

        retrieved_campaign = Campaign.query.filter_by(campaign_unique_identifier=campaign_uid).first()
        assert retrieved_campaign is not None
        assert retrieved_campaign.campaign_name == 'November Personal Loan Campaign'
        assert retrieved_campaign.targeted_customers_count == 10000
        assert retrieved_campaign.success_rate == 94.74
        assert retrieved_campaign.campaign_id is not None

def test_customer_deduplication_unique_constraint(client):
    """
    Test that unique constraints prevent duplicate customer entries based on mobile number.
    (FR2, FR3)
    """
    with app.app_context():
        mobile_number = '1234567890'
        customer1 = Customer(mobile_number=mobile_number, pan='PAN12345')
        db.session.add(customer1)
        db.session.commit()

        customer2 = Customer(mobile_number=mobile_number, pan='PAN67890') # Same mobile number
        db.session.add(customer2)

        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback() # Rollback the failed transaction

        # Verify only one customer exists
        customers = Customer.query.filter_by(mobile_number=mobile_number).all()
        assert len(customers) == 1
        assert customers[0].pan == 'PAN12345'

def test_offer_history_retention_logic_placeholder(client):
    """
    Placeholder to test offer history retention logic (FR18, NFR3).
    Actual implementation would involve creating offers with old dates and running cleanup task.
    """
    with app.app_context():
        customer = Customer(mobile_number='1112223333', pan='HIST1234H')
        db.session.add(customer)
        db.session.commit()

        # Create an offer that should be retained (e.g., 3 months old)
        offer_retained = Offer(
            customer_id=customer.customer_id,
            offer_type='Fresh',
            offer_status='Active',
            offer_start_date=date.today() - timedelta(days=90),
            offer_end_date=date.today() - timedelta(days=60)
        )
        db.session.add(offer_retained)
        db.session.commit()

        # In a real test, you would call the cleanup function here
        # from app.tasks.data_cleanup import cleanup_old_data
        # cleanup_old_data()

        # Verify the offer is still present (within 6 months retention)
        assert Offer.query.filter_by(offer_id=offer_retained.offer_id).first() is not None

        # Create an offer that should be deleted (e.g., 7 months old)
        offer_deleted = Offer(
            customer_id=customer.customer_id,
            offer_type='Fresh',
            offer_status='Expired',
            offer_start_date=date.today() - timedelta(days=210), # 7 months ago
            offer_end_date=date.today() - timedelta(days=180)
        )
        db.session.add(offer_deleted)
        db.session.commit()

        # In a real test, you would call the cleanup function here
        # cleanup_old_data()

        # Verify the offer is deleted (after 6 months retention)
        # assert Offer.query.filter_by(offer_id=offer_deleted.offer_id).first() is None
        # This assertion is commented out as cleanup_old_data is not actually called here.
        # It serves as a placeholder for the logic.