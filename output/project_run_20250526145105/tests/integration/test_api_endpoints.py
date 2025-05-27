import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import datetime
import io
import csv
import os
import sys

# Adjust import path based on typical project structure
# Assuming `app` directory is sibling to `tests`
# If `main.py` is at the project root, adjust `sys.path.insert` accordingly
try:
    # This path assumes `tests/integration/test_api_endpoints.py`
    # and `app/main.py`, `app/database.py`, `app/models.py`
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'app')))
    from main import app
    from database import get_db # The production dependency
    from models import Base, Customer, Offer, OfferHistory, CampaignEvent
except ImportError as e:
    # Fallback for different project structures or if app is not found
    print(f"Could not import app components from `app` directory: {e}")
    print("Attempting to import from current directory (if main.py is at project root)...")
    try:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        from main import app
        from database import get_db
        from models import Base, Customer, Offer, OfferHistory, CampaignEvent
    except ImportError as e2:
        print(f"Could not import app components from project root: {e2}")
        raise


# --- Test Database Setup ---
# Use an in-memory SQLite database for testing for simplicity and speed.
# For true PostgreSQL integration tests, a test PostgreSQL container/instance
# would be spun up and configured here.
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Required for SQLite in-memory with multiple threads/requests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for tests
@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Creates a new database session for each test,
    rolls back the transaction after the test, and drops all tables.
    This ensures a clean slate for every test.
    """
    Base.metadata.create_all(bind=engine) # Create tables for the test database
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    try:
        yield db
    finally:
        db.close()
        transaction.rollback() # Rollback to clean up changes made by the test
        connection.close()
        Base.metadata.drop_all(bind=engine) # Drop tables to ensure clean state for next test run


@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Provides a TestClient instance with the overridden database dependency.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear() # Clear overrides after test to restore original dependencies


# --- Test Functions ---

def test_create_lead(client: TestClient):
    """
    Test the /api/v1/leads POST endpoint.
    Verifies lead creation and data persistence.
    """
    lead_data = {
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "aadhaar_ref_number": "123456789012",
        "loan_product": "Preapproved",
        "offer_details": {"amount": 500000, "interest_rate": 10.5}
    }
    response = client.post("/api/v1/leads", json=lead_data)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "customer_id" in data
    assert uuid.UUID(data["customer_id"]) # Check if it's a valid UUID

    # Verify data in the database directly
    db = app.dependency_overrides[get_db]().__next__()
    customer = db.query(Customer).filter_by(mobile_number="9876543210").first()
    assert customer is not None
    assert str(customer.customer_id) == data["customer_id"]
    assert customer.pan_number == "ABCDE1234F"
    assert customer.aadhaar_ref_number == "123456789012"

    offer = db.query(Offer).filter_by(customer_id=customer.customer_id).first()
    assert offer is not None
    assert offer.product_type == "Preapproved"
    assert offer.offer_status == "Active"
    assert offer.offer_details == {"amount": 500000, "interest_rate": 10.5}


def test_upload_customer_offers_success(client: TestClient):
    """
    Test the /api/v1/admin/customer_offers/upload POST endpoint with a valid CSV.
    Verifies successful file upload and processing.
    """
    csv_content = (
        "mobile_number,pan_number,aadhaar_ref_number,loan_product,offer_amount\n"
        "9998887770,PANCARD1,AADHAAR1,Loyalty,100000\n"
        "9998887771,PANCARD2,AADHAAR2,Top-up,200000\n"
    )
    files = {"file": ("customers.csv", csv_content, "text/csv")}
    response = client.post("/api/v1/admin/customer_offers/upload", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "job_id" in data
    assert data["message"].startswith("File uploaded, 2 records processed")
    assert not data["errors"]

    # Verify data in the database directly
    db = app.dependency_overrides[get_db]().__next__()
    customer1 = db.query(Customer).filter_by(mobile_number="9998887770").first()
    assert customer1 is not None
    assert customer1.pan_number == "PANCARD1"
    assert customer1.aadhaar_ref_number == "AADHAAR1"

    offer1 = db.query(Offer).filter_by(customer_id=customer1.customer_id).first()
    assert offer1 is not None
    assert offer1.product_type == "Loyalty"
    assert offer1.offer_details.get("amount") == "100000" # CSV reader reads as string


def test_upload_customer_offers_invalid_file_type(client: TestClient):
    """
    Test the /api/v1/admin/customer_offers/upload POST endpoint with an invalid file type.
    """
    files = {"file": ("customers.txt", "some text content", "text/plain")}
    response = client.post("/api/v1/admin/customer_offers/upload", files=files)

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed."


def test_get_moengage_file(client: TestClient, db_session):
    """
    Test the /api/v1/admin/campaigns/moengage_file GET endpoint.
    Populate some data first to ensure the file contains expected content.
    """
    # Add some dummy data to the database
    customer_id_1 = uuid.uuid4()
    customer_1 = Customer(
        customer_id=customer_id_1,
        mobile_number="1112223334",
        pan_number="MOENG1FILE",
        aadhaar_ref_number="111122223333",
        customer_attributes={"city": "Mumbai"}
    )
    db_session.add(customer_1)
    db_session.commit()
    db_session.refresh(customer_1)

    offer_1 = Offer(
        offer_id=uuid.uuid4(),
        customer_id=customer_id_1,
        product_type="E-aggregator",
        offer_status="Active",
        offer_details={"amount": 750000, "tenure": 36},
        offer_start_date=datetime.date.today(),
        offer_end_date=datetime.date.today() + datetime.timedelta(days=90)
    )
    db_session.add(offer_1)
    db_session.commit()

    response = client.get("/api/v1/admin/campaigns/moengage_file")

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv"
    assert "attachment; filename=moengage_campaign_file.csv" in response.headers["content-disposition"]

    # Parse CSV content and verify
    csv_reader = csv.reader(io.StringIO(response.text))
    header = next(csv_reader)
    assert header == ["customer_id", "mobile_number", "pan_number", "loan_product", "offer_amount"]
    
    rows = list(csv_reader)
    assert len(rows) >= 1 # At least the one we added
    
    found_customer = False
    for row in rows:
        if row[1] == "1112223334":
            assert row[0] == str(customer_id_1)
            assert row[2] == "MOENG1FILE"
            assert row[3] == "E-aggregator"
            assert row[4] == "750000"
            found_customer = True
            break
    assert found_customer, "Customer data not found in generated Moengage file"


def test_get_customer_profile_success(client: TestClient, db_session):
    """
    Test the /api/v1/customers/{customer_id} GET endpoint for a valid customer.
    Verifies retrieval of customer profile, current offer, and offer history.
    """
    # Create a customer and an offer in the test database
    customer_id = uuid.uuid4()
    customer = Customer(
        customer_id=customer_id,
        mobile_number="5554443332",
        pan_number="PROFILEC",
        aadhaar_ref_number="987654321098",
        customer_segments=["C1", "HighValue"],
        propensity_flag="High"
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)

    offer_id = uuid.uuid4()
    offer = Offer(
        offer_id=offer_id,
        customer_id=customer_id,
        offer_type="Fresh",
        offer_status="Active",
        product_type="Prospect",
        offer_details={"loan_limit": 1000000},
        offer_start_date=datetime.date.today(),
        offer_end_date=datetime.date.today() + datetime.timedelta(days=30),
        is_journey_started=False
    )
    db_session.add(offer)
    db_session.commit()
    db_session.refresh(offer)

    # Add some offer history
    history_id = uuid.uuid4()
    offer_history_entry = OfferHistory(
        history_id=history_id,
        offer_id=offer_id,
        customer_id=customer_id,
        old_offer_status="Pending",
        new_offer_status="Active",
        change_reason="Offer activated",
        snapshot_offer_details={"loan_limit": 1000000}
    )
    db_session.add(offer_history_entry)
    db_session.commit()

    response = client.get(f"/api/v1/customers/{customer_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == str(customer_id)
    assert data["mobile_number"] == "5554443332"
    assert data["pan_number"] == "PROFILEC"
    assert data["current_offer"]["offer_id"] == str(offer_id)
    assert data["current_offer"]["product_type"] == "Prospect"
    assert data["current_offer"]["offer_status"] == "Active"
    assert data["journey_status"] == "Not Started"
    assert "C1" in data["segments"]
    assert "HighValue" in data["segments"]
    assert len(data["offer_history_summary"]) >= 1
    assert data["offer_history_summary"][0]["new_status"] == "Active"


def test_get_customer_profile_not_found(client: TestClient):
    """
    Test the /api/v1/customers/{customer_id} GET endpoint for a non-existent customer.
    """
    non_existent_customer_id = uuid.uuid4()
    response = client.get(f"/api/v1/customers/{non_existent_customer_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Customer not found"


def test_get_daily_tally_report(client: TestClient, db_session):
    """
    Test the /api/v1/reports/daily_tally GET endpoint.
    Populate some data for the report and verify counts.
    """
    today = datetime.date.today()
    
    # Add customers
    customer1_id = uuid.uuid4()
    customer2_id = uuid.uuid4()
    customer1 = Customer(customer_id=customer1_id, mobile_number="1111111111", pan_number="TALLY1", created_at=datetime.datetime.now())
    customer2 = Customer(customer_id=customer2_id, mobile_number="2222222222", pan_number="TALLY2", created_at=datetime.datetime.now())
    db_session.add_all([customer1, customer2])
    db_session.commit()

    # Add active offers
    offer1 = Offer(offer_id=uuid.uuid4(), customer_id=customer1_id, offer_status="Active", product_type="Loyalty")
    offer2 = Offer(offer_id=uuid.uuid4(), customer_id=customer2_id, offer_status="Active", product_type="Preapproved")
    db_session.add_all([offer1, offer2])
    db_session.commit()

    # Add a conversion event for today
    conversion_event = CampaignEvent(
        event_id=uuid.uuid4(),
        customer_id=customer1_id,
        event_source="LOS",
        event_type="CONVERSION",
        event_timestamp=datetime.datetime.now()
    )
    db_session.add(conversion_event)
    db_session.commit()

    response = client.get("/api/v1/reports/daily_tally")

    assert response.status_code == 200
    data = response.json()
    assert data["report_date"] == today.isoformat()
    assert data["total_customers"] == 2
    assert data["active_offers"] == 2
    assert data["new_leads_today"] == 2
    assert data["conversions_today"] == 1