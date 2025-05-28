import pytest
import json
import uuid
from datetime import datetime, timezone

# Assuming backend/__init__.py contains create_app and db
# And backend/models.py contains the SQLAlchemy models (Customer, Offer, Event, Campaign, OfferHistory)
from backend import create_app, db
from backend.models import Customer, Offer, Event, Campaign, OfferHistory

@pytest.fixture(scope='module')
def test_client():
    """
    Pytest fixture to set up a Flask test client with a clean in-memory SQLite database.
    This simulates the application context and database for integration tests.
    """
    app = create_app()
    app.config['TESTING'] = True
    # Use an in-memory SQLite database for testing for speed and isolation.
    # For true PostgreSQL integration tests, you would configure a separate test PostgreSQL DB
    # (e.g., using pytest-postgresql or testcontainers) to ensure full compatibility.
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        # Create all tables in the in-memory database
        db.create_all()

        # Yield the test client to the tests
        yield app.test_client()

        # Clean up: Drop all tables after tests in this module are done
        db.drop_all()

# --- Test Cases for API Endpoints ---

def test_ingest_e_aggregator_data_success(test_client):
    """
    Tests the POST /ingest/e-aggregator-data endpoint for successful ingestion.
    This assumes the endpoint handles creating/updating customer and offer data.
    """
    payload = {
        "source_system": "E-aggregator-Test",
        "data_type": "lead",
        "payload": {
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "offer_amount": 50000,
            "offer_type": "Fresh",
            "valid_until": datetime.now(timezone.utc).isoformat() # ISO 8601 format
        }
    }
    response = test_client.post('/ingest/e-aggregator-data', json=payload)

    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'customer_id' in response.json
    assert uuid.UUID(response.json['customer_id']) # Ensure it's a valid UUID

    # Optional: Verify data persistence in the test database
    with test_client.application.app_context():
        customer = Customer.query.filter_by(mobile_number="9876543210").first()
        assert customer is not None
        assert customer.pan_number == "ABCDE1234F"
        offer = Offer.query.filter_by(customer_id=customer.customer_id).first()
        assert offer is not None
        assert offer.offer_type == "Fresh"

def test_ingest_e_aggregator_data_missing_fields(test_client):
    """
    Tests the POST /ingest/e-aggregator-data endpoint with missing required fields.
    Expects a 400 Bad Request due to validation failure.
    """
    payload = {
        "source_system": "E-aggregator-Test",
        "data_type": "lead",
        "payload": {
            "mobile_number": "9876543211"
            # Missing pan_number, offer_amount, offer_type, valid_until
        }
    }
    response = test_client.post('/ingest/e-aggregator-data', json=payload)

    assert response.status_code == 400
    assert response.json['status'] == 'error'
    assert 'message' in response.json

def test_events_moengage_success(test_client):
    """
    Tests the POST /events/moengage endpoint for successful event recording.
    Requires a customer to exist to link the event.
    """
    # First, create a customer via ingestion to link the event to
    customer_payload = {
        "source_system": "E-aggregator-Moengage",
        "data_type": "lead",
        "payload": {
            "mobile_number": "9998887770",
            "pan_number": "MOENG1234E",
            "offer_amount": 60000,
            "offer_type": "New-new",
            "valid_until": datetime.now(timezone.utc).isoformat()
        }
    }
    customer_response = test_client.post('/ingest/e-aggregator-data', json=customer_payload)
    # customer_id = customer_response.json['customer_id'] # Not strictly needed for this test, as mobile is used

    payload = {
        "customer_mobile": "9998887770",
        "event_type": "SMS_SENT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_id": "campaign_moengage_test",
        "details": {"message_id": "msg_moengage_abc"}
    }
    response = test_client.post('/events/moengage', json=payload)

    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['message'] == 'Moengage event recorded'

    # Optional: Verify data persistence
    with test_client.application.app_context():
        event = Event.query.filter_by(event_type="SMS_SENT", source_system="Moengage").first()
        assert event is not None
        assert event.event_details['message_id'] == "msg_moengage_abc"

def test_events_los_success(test_client):
    """
    Tests the POST /events/los endpoint for successful event recording.
    Requires a customer and potentially an offer to exist.
    """
    # First, create a customer and an offer via ingestion to link the event to
    customer_payload = {
        "source_system": "E-aggregator-LOS",
        "data_type": "lead",
        "payload": {
            "mobile_number": "9998887771",
            "pan_number": "LOSAB1234C",
            "offer_amount": 75000,
            "offer_type": "Preapproved",
            "valid_until": datetime.now(timezone.utc).isoformat()
        }
    }
    customer_response = test_client.post('/ingest/e-aggregator-data', json=customer_payload)
    customer_id = customer_response.json['customer_id']

    payload = {
        "loan_application_number": "LAN_LOS_TEST_123",
        "event_type": "EKYC_ACHIEVED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,
        "details": {"status": "completed", "stage": "eKYC"}
    }
    response = test_client.post('/events/los', json=payload)

    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert response.json['message'] == 'LOS event recorded'

    # Optional: Verify data persistence
    with test_client.application.app_context():
        event = Event.query.filter_by(event_type="EKYC_ACHIEVED", source_system="LOS").first()
        assert event is not None
        assert str(event.customer_id) == customer_id
        assert event.event_details['stage'] == "eKYC"

def test_get_customer_profile_success(test_client):
    """
    Tests the GET /customers/:customer_id endpoint for successful retrieval
    of a customer's de-duplicated profile and associated active offers.
    """
    # Ingest data to create a customer and an offer for retrieval
    customer_payload = {
        "source_system": "Offermart-Test",
        "data_type": "offer",
        "payload": {
            "mobile_number": "1122334455",
            "pan_number": "LMNOP9876Q",
            "offer_amount": 100000,
            "offer_type": "Loyalty",
            "offer_status": "Active",
            "valid_until": datetime.now(timezone.utc).isoformat()
        }
    }
    ingest_response = test_client.post('/ingest/e-aggregator-data', json=customer_payload)
    customer_id = ingest_response.json['customer_id']

    response = test_client.get(f'/customers/{customer_id}')

    assert response.status_code == 200
    assert response.json['customer_id'] == customer_id
    assert response.json['mobile_number'] == "1122334455"
    assert 'offers' in response.json
    assert len(response.json['offers']) > 0
    assert response.json['offers'][0]['offer_type'] == "Loyalty"
    assert response.json['offers'][0]['offer_status'] == "Active"

def test_get_customer_profile_not_found(test_client):
    """
    Tests the GET /customers/:customer_id endpoint for a non-existent customer.
    Expects a 404 Not Found.
    """
    non_existent_id = str(uuid.uuid4()) # Generate a random, non-existent UUID
    response = test_client.get(f'/customers/{non_existent_id}')

    assert response.status_code == 404
    assert response.json['message'] == 'Customer not found'

def test_export_moengage_campaign_file_success(test_client):
    """
    Tests the GET /exports/moengage-campaign-file endpoint.
    Checks for correct content type and disposition for CSV download.
    """
    # For a comprehensive test, you would populate the DB with eligible customers
    # and verify the CSV content. For this placeholder, we check headers.
    response = test_client.get('/exports/moengage-campaign-file')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=moengage_campaign_')

def test_export_duplicate_customers_file_success(test_client):
    """
    Tests the GET /exports/duplicate-customers endpoint.
    Checks for correct content type and disposition for CSV download.
    """
    response = test_client.get('/exports/duplicate-customers')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=duplicate_customers_')

def test_export_unique_customers_file_success(test_client):
    """
    Tests the GET /exports/unique-customers endpoint.
    Checks for correct content type and disposition for CSV download.
    """
    response = test_client.get('/exports/unique-customers')

    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=unique_customers_')

def test_export_data_errors_file_success(test_client):
    """
    Tests the GET /exports/data-errors endpoint.
    Checks for correct content type and disposition for Excel (XLSX) download.
    """
    response = test_client.get('/exports/data-errors')

    assert response.status_code == 200
    # Excel file content type for .xlsx
    assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=data_errors_')