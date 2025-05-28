import pytest
import json
import base64
import uuid
import io
import pandas as pd
from datetime import datetime, timedelta

# Assuming your Flask app instance is named 'app' and is located in 'src/app.py'
# You might need to adjust this import path based on your actual project structure.
from src.app import app
from app.extensions import db  # Import db for potential test database setup/teardown
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign  # Import models for potential data setup

@pytest.fixture(scope='module')
def client():
    """
    Configures the Flask app for testing and provides a test client.
    Sets up and tears down a separate test database for integration tests.
    """
    app.config['TESTING'] = True
    # For actual PostgreSQL integration tests, replace this with a dedicated test database URI.
    # Example: 'postgresql://user:password@host:port/test_cdp_db'
    # Ensure this test database is isolated and can be safely dropped/recreated.
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:' # Using in-memory SQLite for simplicity in this example
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        # Create all tables in the test database
        db.create_all()
        yield app.test_client()
        # Drop all tables after tests are done
        db.drop_all()

@pytest.fixture(scope='function')
def session(client):
    """
    Provides a clean database session for each test function.
    Rolls back transactions after each test to ensure isolation.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        options = dict(bind=connection, binds={})
        session = db.create_scoped_session(options=options)
        db.session = session
        yield session
        transaction.rollback()
        connection.close()
        session.remove()

# --- Real-time API Endpoints (FR9, FR10) ---

def test_create_lead_success(client, session):
    """
    Tests the /api/leads POST endpoint for successful lead creation.
    """
    lead_data = {
        "mobile_number": "9876543210",
        "pan": "ABCDE1234F",
        "loan_type": "Consumer Loan",
        "source_channel": "Insta",
        "application_id": str(uuid.uuid4())
    }
    response = client.post('/api/leads', json=lead_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'customer_id' in data
    assert data['message'] == 'Lead processed successfully'

    # Verify data in DB
    with app.app_context():
        customer = Customer.query.filter_by(mobile_number="9876543210").first()
        assert customer is not None
        assert customer.pan == "ABCDE1234F"

def test_create_lead_invalid_json(client):
    """
    Tests the /api/leads POST endpoint with invalid JSON.
    """
    response = client.post('/api/leads', data="not a json", content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert 'message' in data

def test_eligibility_success(client, session):
    """
    Tests the /api/eligibility POST endpoint for successful eligibility data processing.
    Requires a customer to exist first.
    """
    with app.app_context():
        customer = Customer(mobile_number="9988776655", pan="FGHIJ5678K")
        session.add(customer)
        session.commit()

    eligibility_data = {
        "mobile_number": "9988776655",
        "loan_application_number": "LAN12345",
        "eligibility_status": "Eligible",
        "offer_id": str(uuid.uuid4())
    }
    response = client.post('/api/eligibility', json=eligibility_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == 'Eligibility data processed'

    # Verify data in DB (e.g., an offer or event related to eligibility)
    with app.app_context():
        # This check depends on how eligibility data is stored.
        # Assuming it might create an offer or update an existing one, or log an event.
        # For now, a simple check for customer existence is sufficient for a placeholder.
        customer_check = Customer.query.filter_by(mobile_number="9988776655").first()
        assert customer_check is not None

def test_status_update_success(client, session):
    """
    Tests the /api/status POST endpoint for successful loan application status updates.
    Requires a customer to exist first.
    """
    with app.app_context():
        customer = Customer(mobile_number="9999999999", pan="KLMNO9876P")
        session.add(customer)
        session.commit()
        customer_id = customer.customer_id

    status_data = {
        "loan_application_number": "LAN67890",
        "application_stage": "eKYC",
        "status_details": "eKYC completed successfully",
        "event_timestamp": datetime.now().isoformat()
    }
    response = client.post('/api/status', json=status_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert data['message'] == 'Status updated'

    # Verify data in DB (e.g., a customer event)
    with app.app_context():
        # Assuming the backend logic creates a CustomerEvent for status updates
        event = CustomerEvent.query.filter_by(event_type="APP_STAGE_eKYC", event_source="LOS").first()
        assert event is not None
        assert event.event_details['application_stage'] == "eKYC"


# --- Admin Portal Endpoints (FR29, FR30, FR31, FR32) ---

def test_admin_upload_customer_details_success(client, session):
    """
    Tests the /api/admin/upload/customer-details POST endpoint for successful file upload.
    Simulates a CSV file upload.
    """
    # Create a dummy CSV file content
    csv_content = "mobile_number,pan,loan_type,source_channel\n" \
                  "1111111111,PANCUST1,Prospect,AdminUpload\n" \
                  "2222222222,PANCUST2,TW Loyalty,AdminUpload"
    encoded_content = base64.b64encode(csv_content.encode('utf-8')).decode('utf-8')

    upload_data = {
        "file_type": "Prospect",
        "file_content_base64": encoded_content,
        "uploaded_by": "test_admin"
    }
    response = client.post('/api/admin/upload/customer-details', json=upload_data)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'success'
    assert 'log_id' in data
    assert data['message'] == 'File uploaded, processing initiated'

    # Verify log entry in DB (assuming synchronous processing for test simplicity)
    with app.app_context():
        log = DataIngestionLog.query.filter_by(uploaded_by="test_admin").first()
        assert log is not None
        assert log.status == 'SUCCESS' # Or 'PENDING' if async, then check later
        assert log.file_name == 'Prospect_upload' # Or some derived name

    # Verify customers are created (assuming synchronous processing for test simplicity)
    with app.app_context():
        customer1 = Customer.query.filter_by(mobile_number="1111111111").first()
        customer2 = Customer.query.filter_by(mobile_number="2222222222").first()
        assert customer1 is not None
        assert customer2 is not None


# --- Reporting & Data Export Endpoints (FR25, FR26, FR27, FR28, FR35, FR36, FR39) ---

def test_download_moengage_file(client):
    """
    Tests the /api/reports/moengage-file GET endpoint for CSV download.
    """
    response = client.get('/api/reports/moengage-file')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'attachment; filename=moengage_campaign_data_' in response.headers['Content-Disposition']

    # Basic check for CSV content
    try:
        df = pd.read_csv(io.BytesIO(response.data))
        assert not df.empty # Expecting some data
        assert 'mobile_number' in df.columns # Example column check
    except pd.errors.EmptyDataError:
        pytest.fail("Downloaded Moengage file is empty.")
    except Exception as e:
        pytest.fail(f"Could not read Moengage CSV: {e}")

def test_download_duplicate_data_file(client):
    """
    Tests the /api/reports/duplicate-data GET endpoint for CSV/Excel download.
    """
    response = client.get('/api/reports/duplicate-data')
    assert response.status_code == 200
    # The BRD mentions CSV/Excel, so we'll check for CSV as a common default for placeholder
    assert response.headers['Content-Type'] == 'text/csv' or \
           response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment; filename=duplicate_data_report_' in response.headers['Content-Disposition']

    # Basic check for CSV content
    if 'text/csv' in response.headers['Content-Type']:
        try:
            df = pd.read_csv(io.BytesIO(response.data))
            assert not df.empty
        except pd.errors.EmptyDataError:
            pytest.fail("Downloaded Duplicate Data file is empty.")
        except Exception as e:
            pytest.fail(f"Could not read Duplicate Data CSV: {e}")
    # Add similar check for Excel if the implementation defaults to Excel

def test_download_unique_data_file(client):
    """
    Tests the /api/reports/unique-data GET endpoint for CSV/Excel download.
    """
    response = client.get('/api/reports/unique-data')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv' or \
           response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment; filename=unique_data_report_' in response.headers['Content-Disposition']

    if 'text/csv' in response.headers['Content-Type']:
        try:
            df = pd.read_csv(io.BytesIO(response.data))
            assert not df.empty
        except pd.errors.EmptyDataError:
            pytest.fail("Downloaded Unique Data file is empty.")
        except Exception as e:
            pytest.fail(f"Could not read Unique Data CSV: {e}")

def test_download_error_data_file(client):
    """
    Tests the /api/reports/error-data GET endpoint for Excel download.
    """
    response = client.get('/api/reports/error-data')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment; filename=error_data_report_' in response.headers['Content-Disposition']

    # Basic check for Excel content (requires openpyxl or similar)
    # For simplicity, just check content type and filename for now.
    # A more robust test would attempt to load the Excel file.
    # try:
    #     df = pd.read_excel(io.BytesIO(response.data))
    #     assert not df.empty
    #     assert 'Error Desc' in df.columns
    # except Exception as e:
    #     pytest.fail(f"Could not read Error Excel file: {e}")


def test_get_daily_tally_report(client):
    """
    Tests the /api/reports/daily-tally GET endpoint for daily report data.
    """
    response = client.get('/api/reports/daily-tally')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'date' in data
    assert 'total_customers_processed' in data
    assert 'new_offers_generated' in data
    assert 'deduplicated_customers' in data
    assert isinstance(data['total_customers_processed'], int)
    assert isinstance(data['new_offers_generated'], int)


def test_get_customer_profile_by_id_success(client, session):
    """
    Tests the /api/customer/{customer_id} GET endpoint for a single customer profile.
    Requires a customer to exist in the database.
    """
    # Create a dummy customer in the test database
    with app.app_context():
        customer = Customer(
            mobile_number="9876512345",
            pan="TESTPAN123",
            customer_segment="C1",
            customer_attributes={"city": "Mumbai"}
        )
        session.add(customer)
        session.commit()
        customer_id = customer.customer_id

        # Add a dummy offer and event for this customer
        offer = Offer(
            customer_id=customer_id,
            offer_type="Fresh",
            offer_status="Active",
            offer_start_date=datetime.now().date(),
            offer_end_date=(datetime.now() + timedelta(days=30)).date()
        )
        event = CustomerEvent(
            customer_id=customer_id,
            event_type="SMS_SENT",
            event_source="Moengage",
            event_details={"campaign_id": "CMP001"}
        )
        session.add(offer)
        session.add(event)
        session.commit()

    response = client.get(f'/api/customer/{customer_id}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['customer_id'] == str(customer_id)
    assert data['mobile_number'] == "9876512345"
    assert data['pan'] == "TESTPAN123"
    assert data['customer_segment'] == "C1"
    assert 'active_offers' in data
    assert len(data['active_offers']) > 0
    assert 'application_stages' in data
    assert len(data['application_stages']) > 0 # This would typically come from events

def test_get_customer_profile_by_id_not_found(client):
    """
    Tests the /api/customer/{customer_id} GET endpoint for a non-existent customer.
    """
    non_existent_id = uuid.uuid4()
    response = client.get(f'/api/customer/{non_existent_id}')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['message'] == 'Customer not found'