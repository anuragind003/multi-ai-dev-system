import pytest
from backend import create_app, db
from backend.models import Customer, Offer, OfferHistory, Event, Campaign
import uuid
from datetime import datetime, timezone

@pytest.fixture(scope='session')
def app():
    """
    Fixture to create and configure the Flask app for testing.
    Uses a dedicated test database.
    """
    app = create_app()
    app.config['TESTING'] = True
    # Use a separate database for testing to avoid interfering with development data.
    # Ensure this database exists and is accessible, e.g., via Docker or a local PostgreSQL instance.
    # For a real integration test, this should point to a clean PostgreSQL test database.
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://test_user:test_password@localhost:5433/cdp_test_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        # Create all tables in the test database
        db.create_all()
        yield app
        # Drop all tables after the session tests are complete
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """
    Fixture to provide a test client for each test function.
    Cleans up data before each test to ensure isolation.
    """
    with app.test_client() as client:
        with app.app_context():
            # Clean up data before each test to ensure isolation
            # Order matters for foreign key constraints
            db.session.query(Event).delete()
            db.session.query(OfferHistory).delete()
            db.session.query(Offer).delete()
            db.session.query(Customer).delete()
            db.session.query(Campaign).delete()
            db.session.commit()
        yield client

# --- Integration Test Placeholders ---

def test_ingest_e_aggregator_data(client):
    """
    Test POST /ingest/e-aggregator-data endpoint.
    Placeholder for actual test logic.
    """
    payload = {
        "source_system": "E-aggregator-Test",
        "data_type": "lead",
        "payload": {
            "mobile_number": "9876543210",
            "pan_number": "ABCDE1234F",
            "offer_amount": 50000,
            "offer_validity_days": 30,
            "product_type": "Consumer Loan"
        }
    }
    response = client.post('/ingest/e-aggregator-data', json=payload)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    assert 'customer_id' in response.json
    # Further assertions would involve querying the database to verify data insertion
    # and deduplication logic.

def test_events_moengage(client):
    """
    Test POST /events/moengage endpoint.
    Placeholder for actual test logic.
    """
    # First, ensure a customer exists to link the event to
    customer_id = str(uuid.uuid4())
    with client.application.app_context():
        customer = Customer(customer_id=customer_id, mobile_number="9988776655", pan_number="FGHIJ5678K")
        db.session.add(customer)
        db.session.commit()

    payload = {
        "customer_mobile": "9988776655",
        "event_type": "SMS_DELIVERED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_id": "campaign_moengage_test_1",
        "details": {"message_id": "msg_xyz_123", "status": "delivered"}
    }
    response = client.post('/events/moengage', json=payload)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    # Further assertions would involve checking the 'events' table in the database.

def test_events_los(client):
    """
    Test POST /events/los endpoint.
    Placeholder for actual test logic.
    """
    # First, ensure a customer and an offer exist to link the event to
    customer_id = str(uuid.uuid4())
    offer_id = str(uuid.uuid4())
    with client.application.app_context():
        customer = Customer(customer_id=customer_id, mobile_number="9999999999", pan_number="LMNOP9012Q")
        db.session.add(customer)
        db.session.commit()
        offer = Offer(
            offer_id=offer_id,
            customer_id=customer_id,
            source_offer_id="OFFER_LOS_1",
            offer_type="Fresh",
            offer_status="Active",
            valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1),
            loan_application_number="LAN_LOS_001"
        )
        db.session.add(offer)
        db.session.commit()

    payload = {
        "loan_application_number": "LAN_LOS_001",
        "event_type": "EKYC_ACHIEVED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "customer_id": customer_id,
        "details": {"stage": "eKYC_completed", "document_verified": True}
    }
    response = client.post('/events/los', json=payload)
    assert response.status_code == 200
    assert response.json['status'] == 'success'
    # Further assertions would involve checking the 'events' table and potentially
    # offer status updates in the database.

def test_get_customer_profile(client):
    """
    Test GET /customers/:customer_id endpoint.
    Placeholder for actual test logic.
    """
    # Populate database with a test customer and offer
    customer_id = str(uuid.uuid4())
    offer_id = str(uuid.uuid4())
    with client.application.app_context():
        customer = Customer(
            customer_id=customer_id,
            mobile_number="1122334455",
            pan_number="QRSTU3456V",
            segment="C1",
            is_dnd=False
        )
        offer = Offer(
            offer_id=offer_id,
            customer_id=customer_id,
            source_offer_id="OFFER_CUST_1",
            offer_type="Preapproved",
            offer_status="Active",
            valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1),
            propensity="High"
        )
        db.session.add(customer)
        db.session.add(offer)
        db.session.commit()

    response = client.get(f'/customers/{customer_id}')
    assert response.status_code == 200
    assert response.json['customer_id'] == customer_id
    assert response.json['mobile_number'] == "1122334455"
    assert len(response.json['offers']) == 1
    assert response.json['offers'][0]['offer_id'] == offer_id

    # Test for non-existent customer
    non_existent_id = str(uuid.uuid4())
    response = client.get(f'/customers/{non_existent_id}')
    assert response.status_code == 404
    assert "Customer not found" in response.json['message']

def test_exports_moengage_campaign_file(client):
    """
    Test GET /exports/moengage-campaign-file endpoint.
    Placeholder for actual test logic.
    """
    # Populate with some test data, including DND customers to ensure exclusion
    with client.application.app_context():
        cust1_id = str(uuid.uuid4())
        cust2_id = str(uuid.uuid4())
        cust3_id = str(uuid.uuid4()) # DND customer

        db.session.add(Customer(customer_id=cust1_id, mobile_number="1111111111", pan_number="AAAAA1111A", is_dnd=False))
        db.session.add(Customer(customer_id=cust2_id, mobile_number="2222222222", pan_number="BBBBB2222B", is_dnd=False))
        db.session.add(Customer(customer_id=cust3_id, mobile_number="3333333333", pan_number="CCCCC3333C", is_dnd=True))

        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust1_id, source_offer_id="O1", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust2_id, source_offer_id="O2", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust3_id, source_offer_id="O3", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))
        db.session.commit()

    response = client.get('/exports/moengage-campaign-file')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=moengage_campaign_')
    # Check content: should contain 2 customers (excluding DND)
    content = response.data.decode('utf-8')
    lines = content.strip().split('\n')
    assert len(lines) == 3 # Header + 2 data rows
    assert "1111111111" in content
    assert "2222222222" in content
    assert "3333333333" not in content # DND customer should be excluded

def test_exports_duplicate_customers(client):
    """
    Test GET /exports/duplicate-customers endpoint.
    Placeholder for actual test logic.
    """
    # Populate with some duplicate data
    with client.application.app_context():
        cust1_id = str(uuid.uuid4())
        cust2_id = str(uuid.uuid4()) # This will be marked as duplicate of cust1

        db.session.add(Customer(customer_id=cust1_id, mobile_number="4444444444", pan_number="DDDDD4444D"))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust1_id, source_offer_id="O4", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))

        # Simulate a duplicate entry (e.g., same mobile number, new offer)
        # In a real scenario, deduplication service would set is_duplicate=True and original_offer_id
        db.session.add(Customer(customer_id=cust2_id, mobile_number="4444444444", pan_number="EEEEE5555E")) # This customer is a duplicate by mobile
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust2_id, source_offer_id="O5", offer_status="Active", offer_type="Enrich", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1), is_duplicate=True, original_offer_id=db.session.query(Offer).filter_by(source_offer_id="O4").first().offer_id))
        db.session.commit()

    response = client.get('/exports/duplicate-customers')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=duplicate_customers_')
    content = response.data.decode('utf-8')
    lines = content.strip().split('\n')
    assert len(lines) == 2 # Header + 1 data row (the duplicate offer)
    assert "4444444444" in content
    assert "EEEEE5555E" in content
    assert "is_duplicate" in content # Ensure the flag is present

def test_exports_unique_customers(client):
    """
    Test GET /exports/unique-customers endpoint.
    Placeholder for actual test logic.
    """
    # Populate with unique and duplicate data to ensure only unique are exported
    with client.application.app_context():
        cust1_id = str(uuid.uuid4())
        cust2_id = str(uuid.uuid4())
        cust3_id = str(uuid.uuid4()) # Duplicate

        db.session.add(Customer(customer_id=cust1_id, mobile_number="6666666666", pan_number="FFFFF6666F"))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust1_id, source_offer_id="O6", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))

        db.session.add(Customer(customer_id=cust2_id, mobile_number="7777777777", pan_number="GGGGG7777G"))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust2_id, source_offer_id="O7", offer_status="Active", offer_type="Fresh", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1)))

        # Duplicate customer (same mobile as cust1, different PAN)
        db.session.add(Customer(customer_id=cust3_id, mobile_number="6666666666", pan_number="HHHHH8888H"))
        db.session.add(Offer(offer_id=str(uuid.uuid4()), customer_id=cust3_id, source_offer_id="O8", offer_status="Active", offer_type="Enrich", valid_until=datetime.now(timezone.utc).replace(year=datetime.now().year + 1), is_duplicate=True, original_offer_id=db.session.query(Offer).filter_by(source_offer_id="O6").first().offer_id))
        db.session.commit()

    response = client.get('/exports/unique-customers')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=unique_customers_')
    content = response.data.decode('utf-8')
    lines = content.strip().split('\n')
    assert len(lines) == 3 # Header + 2 unique customer rows
    assert "6666666666" in content # The primary unique entry for this mobile
    assert "7777777777" in content
    assert "HHHHH8888H" not in content # The PAN of the duplicate entry should not be in the unique file

def test_exports_data_errors(client):
    """
    Test GET /exports/data-errors endpoint.
    Placeholder for actual test logic.
    """
    # This test would depend on how error data is stored.
    # Assuming a simple in-memory list or a dedicated error log table for MVP.
    # For now, just check the endpoint exists and returns a file.
    response = client.get('/exports/data-errors')
    assert response.status_code == 200
    assert response.headers['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert response.headers['Content-Disposition'].startswith('attachment; filename=data_errors_')
    # Further assertions would involve parsing the Excel file content if possible,
    # or checking for specific error messages if the backend populates it.