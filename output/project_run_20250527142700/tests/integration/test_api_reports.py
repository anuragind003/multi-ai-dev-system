import pytest
import io
import pandas as pd
from datetime import datetime, timedelta
import json

# Assuming these imports are available from the main application structure
# In a real project, 'app' would be the Flask application instance,
# 'db' would be the SQLAlchemy instance, and models would be defined in 'app/models.py'.
from app import create_app
from app.extensions import db
from app.models import Customer, Offer, DataIngestionLog, CustomerEvent, Campaign


@pytest.fixture(scope='module')
def app():
    """
    Fixture to create and configure a Flask app for testing.
    It sets up an in-memory SQLite database for isolation and cleans it up after tests.
    """
    # Use a testing configuration for the app
    _app = create_app(config_object='config.TestingConfig')

    with _app.app_context():
        # Create all database tables for the test database
        db.create_all()

        # Add some initial data for tests to ensure reports are not empty
        customer1 = Customer(mobile_number='1234567890', pan='ABCDE1234F',
                             customer_segment='C1', is_dnd=False)
        customer2 = Customer(mobile_number='0987654321', pan='FGHIJ5678K',
                             customer_segment='C2', is_dnd=False)
        customer3 = Customer(mobile_number='1112223334', pan='KLMNO9012L',
                             customer_segment='C1', is_dnd=True) # Example for DND

        db.session.add_all([customer1, customer2, customer3])
        db.session.commit()

        # Add some offers
        offer1 = Offer(customer_id=customer1.customer_id, offer_type='Fresh',
                       offer_status='Active', offer_start_date=datetime.now().date(),
                       offer_end_date=(datetime.now() + timedelta(days=30)).date())
        offer2 = Offer(customer_id=customer2.customer_id, offer_type='Enrich',
                       offer_status='Expired',
                       offer_start_date=(datetime.now() - timedelta(days=90)).date(),
                       offer_end_date=(datetime.now() - timedelta(days=60)).date())
        db.session.add_all([offer1, offer2])
        db.session.commit()

        # Add a data ingestion log entry for the error report test
        error_log = DataIngestionLog(
            file_name='test_upload_error.csv',
            upload_timestamp=datetime.now(),
            status='FAILED',
            error_details='Row 5: Invalid mobile number; Row 10: PAN already exists.',
            uploaded_by='test_user'
        )
        db.session.add(error_log)
        db.session.commit()

        # Yield the app instance to the tests
        yield _app

        # Clean up: remove the session and drop all tables after tests are done
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='module')
def client(app):
    """
    Fixture to get a test client from the Flask app.
    This client is used to make requests to the application.
    """
    return app.test_client()


def test_download_moengage_file(client):
    """
    Test the GET /api/reports/moengage-file endpoint.
    Verifies that a CSV file is returned with correct headers and non-empty content.
    """
    response = client.get('/api/reports/moengage-file')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'attachment; filename=moengage_file_' in response.headers['Content-Disposition']

    # Verify content is not empty and is a valid CSV
    try:
        df = pd.read_csv(io.BytesIO(response.data))
        assert not df.empty
        # Basic check for expected columns, assuming the report generates these
        assert all(col in df.columns for col in ['mobile_number', 'customer_name',
                                                 'offer_id', 'campaign_id'])
    except pd.errors.EmptyDataError:
        pytest.fail("Downloaded Moengage file is empty.")
    except Exception as e:
        pytest.fail(f"Could not read Moengage CSV: {e}")


def test_download_duplicate_data_file(client):
    """
    Test the GET /api/reports/duplicate-data endpoint.
    Verifies that a CSV file is returned with correct headers and non-empty content.
    """
    response = client.get('/api/reports/duplicate-data')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'attachment; filename=duplicate_data_report_' in response.headers['Content-Disposition']

    # Verify content is not empty and is a valid CSV
    try:
        df = pd.read_csv(io.BytesIO(response.data))
        assert not df.empty
        # Basic check for expected columns
        assert all(col in df.columns for col in ['mobile_number', 'pan',
                                                 'duplicate_reason', 'original_customer_id'])
    except pd.errors.EmptyDataError:
        pytest.fail("Downloaded Duplicate Data file is empty.")
    except Exception as e:
        pytest.fail(f"Could not read Duplicate Data CSV: {e}")


def test_download_unique_data_file(client):
    """
    Test the GET /api/reports/unique-data endpoint.
    Verifies that a CSV file is returned with correct headers and non-empty content.
    """
    response = client.get('/api/reports/unique-data')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv'
    assert 'attachment; filename=unique_data_report_' in response.headers['Content-Disposition']

    # Verify content is not empty and is a valid CSV
    try:
        df = pd.read_csv(io.BytesIO(response.data))
        assert not df.empty
        # Basic check for expected columns
        assert all(col in df.columns for col in ['customer_id', 'mobile_number',
                                                 'customer_segment'])
    except pd.errors.EmptyDataError:
        pytest.fail("Downloaded Unique Data file is empty.")
    except Exception as e:
        pytest.fail(f"Could not read Unique Data CSV: {e}")


def test_download_error_excel_file(client):
    """
    Test the GET /api/reports/error-data endpoint.
    Verifies that an Excel file is returned with correct headers and non-empty content.
    """
    response = client.get('/api/reports/error-data')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == \
           'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert 'attachment; filename=error_data_report_' in response.headers['Content-Disposition']

    # Verify content is not empty and is a valid Excel
    try:
        df = pd.read_excel(io.BytesIO(response.data), engine='openpyxl')
        assert not df.empty
        # Basic check for expected columns
        assert all(col in df.columns for col in ['log_id', 'file_name', 'error_desc'])
    except Exception as e:
        pytest.fail(f"Could not read Error Excel: {e}")


def test_get_daily_tally_report(client):
    """
    Test the GET /api/reports/daily-tally endpoint.
    Verifies that a JSON response is returned with expected structure and data types.
    """
    response = client.get('/api/reports/daily-tally')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/json'
    data = json.loads(response.data)

    # Check for expected keys and their data types
    assert 'date' in data
    assert isinstance(data['date'], str)
    assert 'total_customers_processed' in data
    assert isinstance(data['total_customers_processed'], int)
    assert 'new_offers_generated' in data
    assert isinstance(data['new_offers_generated'], int)
    assert 'deduplicated_customers' in data
    assert isinstance(data['deduplicated_customers'], int)
    assert 'successful_uploads' in data
    assert isinstance(data['successful_uploads'], int)
    assert 'failed_uploads' in data
    assert isinstance(data['failed_uploads'], int)

    # Test with a specific date parameter
    test_date = '2023-01-15'
    response_with_date = client.get(f'/api/reports/daily-tally?date={test_date}')
    assert response_with_date.status_code == 200
    data_with_date = json.loads(response_with_date.data)
    assert data_with_date['date'] == test_date