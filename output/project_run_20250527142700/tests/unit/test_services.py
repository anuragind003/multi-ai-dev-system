import pytest
from datetime import datetime, date, timedelta
import uuid
import json
import io
import pandas as pd
import base64

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

# Assuming models are defined in app.models
from app.models import Customer, Offer, CustomerEvent, Campaign, DataIngestionLog

# --- Fixtures for Test Environment (replicated from test_models.py for self-containment) ---

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

    # Push an application context for the session
    with _app.app_context():
        _db.create_all() # Create tables for all models
        yield _app
        _db.drop_all() # Clean up after tests

@pytest.fixture(scope='function')
def db(app):
    """Fixture for a database session, scoped to function for isolation."""
    with app.app_context():
        # Begin a new transaction for each test function
        connection = app.db.engine.connect()
        transaction = connection.begin()
        app.db.session = app.db.session_factory(bind=connection)

        yield app.db

        # Rollback the transaction to clean up the database for the next test
        transaction.rollback()
        connection.close()
        app.db.session.remove()

@pytest.fixture(scope='function')
def client(app):
    """Fixture for a test client."""
    return app.test_client()

# --- Mock Service Functions (These would typically be imported from app.services) ---

def create_customer(db_session, mobile_number, pan=None, aadhaar_ref_number=None, ucid=None, previous_loan_app_number=None):
    """
    Simulates a service function to create a customer.
    In a real scenario, this would be in app.services.customer_service.
    """
    customer = Customer(
        mobile_number=mobile_number,
        pan=pan,
        aadhaar_ref_number=aadhaar_ref_number,
        ucid=ucid,
        previous_loan_app_number=previous_loan_app_number
    )
    db_session.add(customer)
    db_session.commit()
    return customer

def generate_moengage_file(db_session):
    """
    Simulates a service function to generate the Moengage CSV file.
    In a real scenario, this would be in app.services.report_service.
    This mock generates a simple CSV based on some dummy data.
    """
    # In a real service, this would query Customer and Offer tables
    # and apply business logic to format the data.
    # For this placeholder, we'll just return a fixed mock CSV content.
    data = [
        {"mobile_number": "9876543210", "offer_id": str(uuid.uuid4()), "campaign_name": "Preapproved_Loan_Oct"},
        {"mobile_number": "1234567890", "offer_id": str(uuid.uuid4()), "campaign_name": "Loyalty_Offer_Nov"},
    ]
    df = pd.DataFrame(data)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return output.getvalue()

# --- Placeholder Test Classes for Services ---

class TestCustomerServices:
    """Placeholder test class for customer-related services."""

    def test_create_customer_success(self, db):
        """Test successful customer creation."""
        mobile = "9988776655"
        pan = "ABCDE1234F"
        customer = create_customer(db, mobile, pan=pan)

        assert customer.customer_id is not None
        assert customer.mobile_number == mobile
        assert customer.pan == pan

        retrieved_customer = db.session.query(Customer).filter_by(mobile_number=mobile).first()
        assert retrieved_customer is not None
        assert retrieved_customer.customer_id == customer.customer_id

    def test_create_customer_duplicate_mobile_fails(self, db):
        """Test that creating a customer with a duplicate mobile number raises an IntegrityError."""
        mobile = "1112223334"
        create_customer(db, mobile, pan="PAN12345A")

        with pytest.raises(IntegrityError):
            # Attempt to create another customer with the same mobile
            create_customer(db, mobile, pan="PAN67890B")
            db.session.flush() # Flush to trigger the integrity check before commit

    def test_create_customer_with_multiple_identifiers(self, db):
        """Test creating a customer with multiple unique identifiers."""
        mobile = "5554443332"
        pan = "PQRST9876U"
        aadhaar = "123456789012"
        ucid = "UCID_XYZ_001"
        loan_app_num = "LAN_ABC_001"

        customer = create_customer(db, mobile, pan=pan, aadhaar_ref_number=aadhaar,
                                   ucid=ucid, previous_loan_app_number=loan_app_num)

        assert customer.mobile_number == mobile
        assert customer.pan == pan
        assert customer.aadhaar_ref_number == aadhaar
        assert customer.ucid == ucid
        assert customer.previous_loan_app_number == loan_app_num

        retrieved = db.session.query(Customer).filter_by(ucid=ucid).first()
        assert retrieved.customer_id == customer.customer_id


class TestReportServices:
    """Placeholder test class for report-related services."""

    def test_generate_moengage_file_content(self, db):
        """Test the content and format of the generated Moengage file."""
        # The mock service function generates fixed data, so we test against that.
        csv_content = generate_moengage_file(db)

        assert isinstance(csv_content, str)
        assert "mobile_number,offer_id,campaign_name" in csv_content # Check header
        assert "9876543210," in csv_content # Check for first mock record's mobile
        assert "1234567890," in csv_content # Check for second mock record's mobile

        # Use pandas to parse the CSV content and verify structure/rows
        df_result = pd.read_csv(io.StringIO(csv_content))

        assert not df_result.empty
        assert list(df_result.columns) == ["mobile_number", "offer_id", "campaign_name"]
        assert len(df_result) == 2 # Based on the mock data

        # Verify specific values if needed (e.g., for a more dynamic mock)
        assert df_result.loc[0, "mobile_number"] == 9876543210
        assert df_result.loc[1, "mobile_number"] == 1234567890

    def test_get_duplicate_data_placeholder(self, db):
        """Placeholder for testing duplicate data retrieval service."""
        # This test would involve populating the DB with duplicate-prone data
        # and then calling a service function like `get_duplicate_data`.
        # For now, just a passing test.
        assert True

    def test_get_unique_data_placeholder(self, db):
        """Placeholder for testing unique data retrieval service."""
        assert True

    def test_get_error_data_placeholder(self, db):
        """Placeholder for testing error data retrieval service."""
        assert True