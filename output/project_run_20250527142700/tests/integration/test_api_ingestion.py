import pytest
import json
import base64
import uuid
from datetime import datetime

# Assuming create_app is in src/app/__init__.py or src/app.py
# and models are in src/models.py
from src.app import create_app
from src.models import db, Customer, Offer, CustomerEvent, DataIngestionLog

@pytest.fixture(scope='module')
def app():
    """Create and configure a new app instance for each test module."""
    app = create_app()
    app.config['TESTING'] = True
    # Use an in-memory SQLite database for testing for simplicity.
    # For a true integration test with PostgreSQL, you'd configure a separate test PostgreSQL database.
    # Example: app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@host:port/test_cdp_db'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False # Suppress warning

    with app.app_context():
        db.create_all()  # Create tables based on models
        yield app  # Provide the app to the tests
        db.drop_all()  # Drop tables after all tests in the module are done

@pytest.fixture(scope='function')
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(autouse=True)
def setup_and_teardown_db(app):
    """
    Ensures a clean database state for each test function.
    This fixture runs automatically for every test.
    """
    with app.app_context():
        # Clear data from tables before each test
        # Order matters for foreign key constraints
        db.session.query(CustomerEvent).delete()
        db.session.query(Offer).delete()
        db.session.query(DataIngestionLog).delete()
        db.session.query(Customer).delete()
        db.session.commit()
        yield
        # Rollback any pending transactions to ensure a clean state for the next test
        db.session.rollback()

# Test cases for /api/leads
def test_create_lead_success(client):
    """
    Test successful lead creation via /api/leads.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    lead_data = {
        "mobile_number": "9876543210",
        "pan": "ABCDE1234F",
        "loan_type": "Personal Loan",
        "source_channel": "Insta",
        "application_id": str(uuid.uuid4())
    }
    response = client.post('/api/leads', json=lead_data)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'customer_id' in response.json
    with client.application.app_context():
        customer = Customer.query.filter_by(mobile_number="9876543210").first()
        assert customer is not None
        assert customer.pan == "ABCDE1234F"

def test_create_lead_missing_mobile_number(client):
    """Test lead creation with missing required field (mobile_number)."""
    lead_data = {
        "pan": "ABCDE1234F",
        "loan_type": "Personal Loan",
        "source_channel": "Insta",
        "application_id": str(uuid.uuid4())
    }
    response = client.post('/api/leads', json=lead_data)
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert 'message' in response.json
    assert "mobile_number is required" in response.json['message'] # Assuming specific error message

def test_create_lead_duplicate_mobile_number_updates_customer(client):
    """
    Test lead creation with a duplicate mobile number.
    Should update existing customer's attributes if new data is provided,
    or at least not create a new customer, due to deduplication (FR3).
    """
    mobile = "9999988888"
    pan1 = "PAN12345A"
    pan2 = "PAN12345B"
    app_id1 = str(uuid.uuid4())
    app_id2 = str(uuid.uuid4())

    # First lead
    lead_data_1 = {
        "mobile_number": mobile,
        "pan": pan1,
        "loan_type": "Home Loan",
        "source_channel": "E-aggregator",
        "application_id": app_id1
    }
    response1 = client.post('/api/leads', json=lead_data_1)
    assert response1.status_code == 200

    # Second lead with same mobile number, different PAN
    lead_data_2 = {
        "mobile_number": mobile,
        "pan": pan2,
        "loan_type": "Car Loan",
        "source_channel": "Insta",
        "application_id": app_id2
    }
    response2 = client.post('/api/leads', json=lead_data_2)
    assert response2.status_code == 200
    assert response2.json['status'] == 'success'

    with client.application.app_context():
        customers = Customer.query.filter_by(mobile_number=mobile).all()
        assert len(customers) == 1 # Should be only one customer profile due to deduplication
        customer = customers[0]
        # Assuming the latest PAN or a merge logic applies. For this test, just check one exists.
        assert customer.pan in [pan1, pan2]

# Test cases for /api/eligibility
def test_eligibility_success(client):
    """
    Test successful eligibility data ingestion via /api/eligibility.
    FR9, FR10.
    """
    mobile = "9876543211"
    loan_app_num = "LAN123456789"
    offer_id = str(uuid.uuid4())

    # First, create a customer to link eligibility to
    lead_data = {
        "mobile_number": mobile,
        "pan": "ABCDE1234G",
        "loan_type": "Personal Loan",
        "source_channel": "Insta",
        "application_id": str(uuid.uuid4())
    }
    client.post('/api/leads', json=lead_data)

    eligibility_data = {
        "mobile_number": mobile,
        "loan_application_number": loan_app_num,
        "eligibility_status": "ELIGIBLE",
        "offer_id": offer_id
    }
    response = client.post('/api/eligibility', json=eligibility_data)
    assert response.status_code == 200
    assert response.json['status'] == 'success'

    with client.application.app_context():
        customer = Customer.query.filter_by(mobile_number=mobile).first()
        assert customer is not None
        # Assuming eligibility creates/updates an offer
        offer = Offer.query.filter_by(loan_application_number=loan_app_num, offer_id=uuid.UUID(offer_id)).first()
        assert offer is not None
        assert offer.customer_id == customer.customer_id
        assert offer.offer_status == "Active" # Assuming 'ELIGIBLE' maps to 'Active'

def test_eligibility_missing_required_field(client):
    """Test eligibility with missing required field (mobile_number)."""
    eligibility_data = {
        "loan_application_number": "LAN123456789",
        "eligibility_status": "ELIGIBLE",
        "offer_id": str(uuid.uuid4())
    }
    response = client.post('/api/eligibility', json=eligibility_data)
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert "mobile_number is required" in response.json['message']

def test_eligibility_customer_not_found(client):
    """Test eligibility for a mobile number that doesn't exist in CDP."""
    eligibility_data = {
        "mobile_number": "9999999999", # Non-existent mobile
        "loan_application_number": "LAN_NONEXISTENT",
        "eligibility_status": "ELIGIBLE",
        "offer_id": str(uuid.uuid4())
    }
    response = client.post('/api/eligibility', json=eligibility_data)
    assert response.status_code == 404 # Or 400, depending on specific error handling
    assert response.json['status'] == 'error'
    assert "Customer not found" in response.json['message'] # Assuming specific error message

# Test cases for /api/status
def test_status_update_success(client):
    """
    Test successful loan application status update via /api/status.
    FR9, FR10.
    """
    mobile = "9876543212"
    loan_app_num = "APP123456789"

    # First, create a customer and an offer/application
    lead_data = {
        "mobile_number": mobile,
        "pan": "ABCDE1234H",
        "loan_type": "Personal Loan",
        "source_channel": "Insta",
        "application_id": loan_app_num
    }
    client.post('/api/leads', json=lead_data)

    # Simulate an offer being created with this application ID
    with client.application.app_context():
        customer = Customer.query.filter_by(mobile_number=mobile).first()
        offer = Offer(customer_id=customer.customer_id,
                      offer_type="Fresh",
                      offer_status="Active",
                      loan_application_number=loan_app_num)
        db.session.add(offer)
        db.session.commit()

    status_data = {
        "loan_application_number": loan_app_num,
        "application_stage": "eKYC",
        "status_details": "eKYC completed successfully",
        "event_timestamp": datetime.now().isoformat()
    }
    response = client.post('/api/status', json=status_data)
    assert response.status_code == 200
    assert response.json['status'] == 'success'

    with client.application.app_context():
        # Check if event is logged
        customer = Customer.query.filter_by(mobile_number=mobile).first()
        event = CustomerEvent.query.filter_by(
            event_type="APP_STAGE_eKYC",
            event_source="LOS", # Assuming LOS is the source for application stages
            customer_id=customer.customer_id
        ).first()
        assert event is not None
        assert event.event_details['application_stage'] == "eKYC"
        assert event.event_details['status_details'] == "eKYC completed successfully"

def test_status_update_invalid_loan_app_number(client):
    """Test status update for a non-existent loan application number."""
    status_data = {
        "loan_application_number": "NONEXISTENT_LAN",
        "application_stage": "eKYC",
        "status_details": "eKYC completed successfully",
        "event_timestamp": datetime.now().isoformat()
    }
    response = client.post('/api/status', json=status_data)
    assert response.status_code == 404 # Or 400 depending on specific error handling
    assert response.json['status'] == 'error'
    assert "Loan application not found" in response.json['message'] # Assuming specific error message

# Test cases for /api/admin/upload/customer-details
def test_admin_upload_customer_details_success(client):
    """
    Test successful customer details file upload via /api/admin/upload/customer-details.
    FR29: The Admin Portal shall allow uploading customer details for Prospect, TW Loyalty, Topup, and Employee loans.
    FR30: The Admin Portal shall generate a lead for customers in the system upon successful file upload.
    FR31: The Admin Portal shall generate a success file upon successful upload of all data.
    """
    # Simulate a CSV file content
    csv_content = "mobile_number,pan,loan_type,source_channel\n9876543213,ABCDE1234I,Prospect,AdminUpload\n9876543214,ABCDE1234J,TW Loyalty,AdminUpload"
    encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

    upload_data = {
        "file_type": "Prospect", # This should be one of the allowed types
        "file_content_base64": encoded_content,
        "uploaded_by": "test_admin"
    }
    response = client.post('/api/admin/upload/customer-details', json=upload_data)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'log_id' in response.json

    with client.application.app_context():
        customer1 = Customer.query.filter_by(mobile_number="9876543213").first()
        customer2 = Customer.query.filter_by(mobile_number="9876543214").first()
        assert customer1 is not None
        assert customer2 is not None
        log = DataIngestionLog.query.filter_by(log_id=response.json['log_id']).first()
        assert log is not None
        assert log.status == 'SUCCESS' # Assuming all records are valid for this test

def test_admin_upload_customer_details_invalid_file_type(client):
    """Test customer details file upload with an invalid file type."""
    csv_content = "mobile_number,pan\n123,ABC"
    encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

    upload_data = {
        "file_type": "InvalidType", # This is the invalid part
        "file_content_base64": encoded_content,
        "uploaded_by": "test_admin"
    }
    response = client.post('/api/admin/upload/customer-details', json=upload_data)
    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert "Invalid file_type" in response.json['message'] # Assuming specific error message

def test_admin_upload_customer_details_malformed_csv(client):
    """Test customer details file upload with malformed CSV content."""
    malformed_csv_content = "mobile_number,pan\n9876543215,ABCDE1234K,extra_column" # Too many columns
    encoded_content = base64.b64encode(malformed_csv_content.encode('utf-8')).decode('utf-8')

    upload_data = {
        "file_type": "Prospect",
        "file_content_base64": encoded_content,
        "uploaded_by": "test_admin"
    }
    response = client.post('/api/admin/upload/customer-details', json=upload_data)
    assert response.status_code == 400 # Or 500 depending on parsing error handling
    assert response.json['status'] == 'error'
    assert "Error processing CSV" in response.json['message'] # Assuming specific error message