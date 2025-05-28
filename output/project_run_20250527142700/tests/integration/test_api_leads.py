import pytest
import json
from app.extensions import db
from app.models import Customer

# Assuming 'client' and 'app' fixtures are provided by a conftest.py file
# For example, a conftest.py might look like this:
#
# import pytest
# from app import create_app
# from app.extensions import db
#
# @pytest.fixture(scope='session')
# def app():
#     """Create and configure a new app instance for each test session."""
#     app = create_app('testing') # 'testing' config should use a test database
#     with app.app_context():
#         db.create_all()
#         yield app
#         db.drop_all()
#
# @pytest.fixture(scope='function')
# def client(app):
#     """A test client for the app."""
#     with app.test_client() as client:
#         yield client
#     # Clean up database after each test function
#     with app.app_context():
#         # This is a simple way to clear data, for more complex scenarios
#         # consider using transactions or specific data deletion strategies.
#         for table in reversed(db.metadata.sorted_tables):
#             db.session.execute(table.delete())
#         db.session.commit()


def test_create_lead_success(client, app):
    """
    Test successful lead creation via /api/leads endpoint.
    FR9: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation API).
    FR10: The system shall modify existing APIs (Lead Generation, Eligibility, Status) to insert data into the CDP database instead of the MAS database.
    """
    lead_data = {
        "mobile_number": "9876543210",
        "pan": "ABCDE1234F",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator",
        "application_id": "APP123456789"
    }

    response = client.post('/api/leads', json=lead_data)
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['status'] == 'success'
    assert 'customer_id' in data
    assert data['message'] == 'Lead processed successfully'

    # Verify data in database
    with app.app_context():
        customer = db.session.query(Customer).filter_by(mobile_number="9876543210").first()
        assert customer is not None
        assert customer.pan == "ABCDE1234F"
        assert customer.mobile_number == "9876543210"
        # The customer_id returned in the response should match the one in the database
        assert str(customer.customer_id) == data['customer_id']


def test_create_lead_missing_mobile_number(client):
    """
    Test lead creation with missing mobile_number, which is a NOT NULL field.
    """
    lead_data = {
        "pan": "ABCDE1234G",
        "loan_type": "Home Loan",
        "source_channel": "Insta",
        "application_id": "APP987654321"
    }

    response = client.post('/api/leads', json=lead_data)
    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['status'] == 'error'
    assert 'message' in data
    # Expecting an error message indicating a missing or invalid mobile number
    assert 'mobile_number' in data['message'].lower()


def test_create_lead_duplicate_mobile_number(client, app):
    """
    Test lead creation with a duplicate mobile number.
    The 'mobile_number' field is UNIQUE. This should result in an error.
    """
    lead_data_1 = {
        "mobile_number": "9998887770",
        "pan": "PQRST1234A",
        "loan_type": "Car Loan",
        "source_channel": "E-aggregator",
        "application_id": "APP000000001"
    }
    lead_data_2 = {
        "mobile_number": "9998887770",  # Duplicate mobile number
        "pan": "PQRST1234B",
        "loan_type": "Car Loan",
        "source_channel": "E-aggregator",
        "application_id": "APP000000002"
    }

    # First request should succeed
    response_1 = client.post('/api/leads', json=lead_data_1)
    assert response_1.status_code == 200
    data_1 = json.loads(response_1.data)
    assert data_1['status'] == 'success'

    # Second request with duplicate mobile number should fail
    response_2 = client.post('/api/leads', json=lead_data_2)
    data_2 = json.loads(response_2.data)

    # Depending on the exact backend implementation for IntegrityError,
    # it could be 400 (Bad Request) or 409 (Conflict).
    # Assuming 409 for a unique constraint violation is good practice.
    assert response_2.status_code in [400, 409]
    assert data_2['status'] == 'error'
    assert 'message' in data_2
    assert 'duplicate' in data_2['message'].lower() or 'exists' in data_2['message'].lower()

    # Verify only one customer record exists for this mobile number in the database
    with app.app_context():
        customers = db.session.query(Customer).filter_by(mobile_number="9998887770").all()
        assert len(customers) == 1


def test_create_lead_invalid_json_payload(client):
    """
    Test lead creation with an invalid JSON payload.
    """
    # Sending non-JSON data with application/json content-type
    response = client.post('/api/leads', data="this is not json", content_type='application/json')
    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['status'] == 'error'
    assert data['message'] == 'Request must be JSON'


def test_create_lead_empty_json_payload(client):
    """
    Test lead creation with an empty JSON payload.
    """
    response = client.post('/api/leads', json={})
    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['status'] == 'error'
    assert 'message' in data
    assert 'mobile_number' in data['message'].lower() # Expecting validation error for missing required fields