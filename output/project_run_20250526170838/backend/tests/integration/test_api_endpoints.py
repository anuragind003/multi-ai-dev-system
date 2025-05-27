import pytest
import json
import io
import csv
from datetime import datetime, date
import uuid
import base64

# Assume the main Flask app and SQLAlchemy db instance are available from backend.app
# and models from backend.models.
# In a real project, you'd ensure these imports correctly point to your application's structure.
from backend.app import create_app, db
from backend.models import Customer, Offer, Event, IngestionLog, CampaignMetric

# For integration tests, it's crucial to use a dedicated test database.
# This URI should point to a PostgreSQL database specifically for testing.
# Ensure this database exists and is accessible before running tests.
# Example: "postgresql://test_user:test_password@localhost:5432/test_cdp_db"
TEST_DATABASE_URI = "postgresql://user:password@localhost:5432/test_cdp_db"


@pytest.fixture(scope="module")
def app():
    """
    Fixture to create and configure a Flask app for testing.
    Sets up a clean test database before tests and tears it down afterwards.
    """
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = TEST_DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    with app.app_context():
        # Ensure tables are created in the test database
        db.create_all()
        yield app
        # Clean up tables after all tests in the module are done
        db.drop_all()


@pytest.fixture(scope="module")
def client(app):
    """
    Fixture to provide a test client for the Flask app.
    """
    return app.test_client()


@pytest.fixture(scope="function", autouse=True)
def setup_teardown_db(app):
    """
    Fixture to clean up data in the test database before each test function.
    Ensures test isolation.
    """
    with app.app_context():
        # Delete data from tables in a specific order to respect foreign key constraints
        db.session.query(Event).delete()
        db.session.query(Offer).delete()
        db.session.query(Customer).delete()
        db.session.query(IngestionLog).delete()
        db.session.query(CampaignMetric).delete()
        db.session.commit()
        yield
        # Data is cleaned before each test, so no specific teardown needed here
        # beyond what app fixture does (drop_all).


# Helper function to create a customer for tests
def create_test_customer(
    mobile_number=None,
    pan_number=None,
    aadhaar_number=None,
    ucid_number=None,
    loan_application_number=None,
    dnd_flag=False,
    segment="C1",
):
    """Helper to create a customer record in the test database."""
    customer_id = str(uuid.uuid4())
    customer = Customer(
        customer_id=customer_id,
        mobile_number=mobile_number or f"987654321{str(uuid.uuid4())[:4]}",
        pan_number=pan_number or f"ABCDE1234{str(uuid.uuid4())[:1]}",
        aadhaar_number=aadhaar_number or f"12345678901{str(uuid.uuid4())[:1]}",
        ucid_number=ucid_number or f"UCID{str(uuid.uuid4())[:4]}",
        loan_application_number=loan_application_number
        or f"LAN{str(uuid.uuid4())[:4]}",
        dnd_flag=dnd_flag,
        segment=segment,
    )
    with db.session.no_autoflush:  # Prevent autoflush issues with unique constraints
        db.session.add(customer)
        db.session.commit()
    return customer


# Test cases for API Endpoints


def test_post_leads_success(client, app):
    """
    Test the /api/leads endpoint for successful lead creation.
    FR7, FR11, FR12
    """
    data = {
        "mobile_number": "9876543210",
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator",
    }
    response = client.post("/api/leads", json=data)
    assert response.status_code == 201
    response_data = json.loads(response.data)
    assert response_data["status"] == "success"
    assert "customer_id" in response_data

    with app.app_context():
        customer = db.session.get(Customer, response_data["customer_id"])
        assert customer is not None
        assert customer.mobile_number == data["mobile_number"]


def test_post_leads_missing_data(client):
    """
    Test the /api/leads endpoint with missing required data.
    """
    data = {
        "pan_number": "ABCDE1234F",
        "aadhaar_number": "123456789012",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator",
    }
    response = client.post("/api/leads", json=data)
    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data["status"] == "error"
    assert "message" in response_data


def test_post_eligibility_success(client, app):
    """
    Test the /api/eligibility endpoint for successful eligibility update.
    FR7, FR11, FR12
    """
    customer = create_test_customer()
    offer_id = str(uuid.uuid4())
    offer = Offer(
        offer_id=offer_id,
        customer_id=customer.customer_id,
        offer_type="Fresh",
        offer_status="Active",
        propensity="High",
        start_date=date.today(),
        end_date=date.today(),
        channel="E-aggregator",
    )
    with app.app_context():
        db.session.add(offer)
        db.session.commit()

    data = {
        "customer_id": customer.customer_id,
        "offer_id": offer_id,
        "eligibility_status": "Eligible",
        "loan_amount": 150000.0,
    }
    response = client.post("/api/eligibility", json=data)
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == "success"
    assert response_data["message"] == "Eligibility updated"

    with app.app_context():
        updated_offer = db.session.get(Offer, offer_id)
        # Assuming eligibility updates offer_status for simplicity in test
        assert updated_offer.offer_status == "Eligible"


def test_post_eligibility_customer_or_offer_not_found(client):
    """
    Test /api/eligibility with a non-existent customer or offer.
    """
    data = {
        "customer_id": str(uuid.uuid4()),  # Non-existent customer
        "offer_id": str(uuid.uuid4()),
        "eligibility_status": "Eligible",
        "loan_amount": 150000.0,
    }
    response = client.post("/api/eligibility", json=data)
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data["status"] == "error"
    assert "Customer or Offer not found" in response_data["message"]


def test_post_status_updates_success(client, app):
    """
    Test the /api/status-updates endpoint for successful status update.
    FR11, FR12, FR26
    """
    customer = create_test_customer()
    loan_app_num = f"LAN{str(uuid.uuid4())[:8]}"
    with app.app_context():
        customer.loan_application_number = loan_app_num
        db.session.add(customer)
        db.session.commit()

    data = {
        "loan_application_number": loan_app_num,
        "customer_id": customer.customer_id,
        "current_stage": "EKYC_ACHIEVED",
        "status_timestamp": datetime.now().isoformat(),
    }
    response = client.post("/api/status-updates", json=data)
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == "success"
    assert response_data["message"] == "Status updated"

    with app.app_context():
        event = (
            db.session.query(Event)
            .filter_by(customer_id=customer.customer_id, event_type="EKYC_ACHIEVED")
            .first()
        )
        assert event is not None
        assert event.event_source == "LOS"  # Assuming LOS for application stages


def test_post_status_updates_invalid_customer(client):
    """
    Test /api/status-updates with an invalid customer ID.
    """
    data = {
        "loan_application_number": "LAN12345",
        "customer_id": str(uuid.uuid4()),  # Non-existent
        "current_stage": "LOGIN",
        "status_timestamp": datetime.now().isoformat(),
    }
    response = client.post("/api/status-updates", json=data)
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data["status"] == "error"
    assert "Customer not found" in response_data["message"]


def test_admin_customer_data_upload_success(client, app):
    """
    Test the /admin/customer-data/upload endpoint for successful file upload.
    FR35, FR36, FR37
    """
    csv_content = (
        "mobile_number,pan_number,aadhaar_number,loan_type,source_channel\n"
        "9999900001,PAN00001,AADHAAR00001,Prospect,AdminUpload\n"
        "9999900002,PAN00002,AADHAAR00002,TW Loyalty,AdminUpload"
    )
    file_data = io.BytesIO(csv_content.encode("utf-8"))
    file_name = "test_customers.csv"
    loan_type = "Prospect"

    data = {
        "file": (file_data, file_name),
        "loan_type": loan_type,
    }
    response = client.post(
        "/admin/customer-data/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == "success"
    assert "log_id" in response_data
    assert response_data["success_count"] == 2
    assert response_data["error_count"] == 0

    with app.app_context():
        log = db.session.get(IngestionLog, response_data["log_id"])
        assert log is not None
        assert log.status == "SUCCESS"
        assert log.file_name == file_name

        customer1 = (
            db.session.query(Customer).filter_by(mobile_number="9999900001").first()
        )
        assert customer1 is not None
        assert customer1.pan_number == "PAN00001"

        customer2 = (
            db.session.query(Customer).filter_by(mobile_number="9999900002").first()
        )
        assert customer2 is not None
        assert customer2.pan_number == "PAN00002"


def test_admin_customer_data_upload_with_errors(client, app):
    """
    Test the /admin/customer-data/upload endpoint with invalid data in the file.
    FR38
    """
    csv_content = (
        "mobile_number,pan_number,aadhaar_number,loan_type,source_channel\n"
        "9999900003,PAN00003,AADHAAR00003,Prospect,AdminUpload\n"
        "INVALID_MOBILE,,AADHAAR00004,TW Loyalty,AdminUpload\n"  # Invalid mobile, missing PAN
        "9999900005,PAN00005,,Prospect,AdminUpload"  # Missing Aadhaar
    )
    file_data = io.BytesIO(csv_content.encode("utf-8"))
    file_name = "test_customers_with_errors.csv"
    loan_type = "Prospect"

    data = {
        "file": (file_data, file_name),
        "loan_type": loan_type,
    }
    response = client.post(
        "/admin/customer-data/upload",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data["status"] == "partial_success"
    assert "log_id" in response_data
    assert response_data["success_count"] == 1
    assert response_data["error_count"] == 2

    with app.app_context():
        log = db.session.get(IngestionLog, response_data["log_id"])
        assert log is not None
        assert log.status == "PARTIAL_SUCCESS"
        assert "Error Desc" in log.error_description  # Check for error description


def test_get_customer_profile_success(client, app):
    """
    Test the /customers/{customer_id} endpoint for successful retrieval.
    FR2, FR40
    """
    customer = create_test_customer(
        mobile_number="1111111111", pan_number="PAN11111", dnd_flag=True, segment="C2"
    )
    offer_id_1 = str(uuid.uuid4())
    offer_id_2 = str(uuid.uuid4())
    event_id_1 = str(uuid.uuid4())
    event_id_2 = str(uuid.uuid4())

    with app.app_context():
        offer1 = Offer(
            offer_id=offer_id_1,
            customer_id=customer.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            propensity="High",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31),
            channel="Web",
        )
        offer2 = Offer(
            offer_id=offer_id_2,
            customer_id=customer.customer_id,
            offer_type="Enrich",
            offer_status="Expired",
            propensity="Medium",
            start_date=date(2022, 6, 1),
            end_date=date(2022, 7, 1),
            channel="App",
        )
        event1 = Event(
            event_id=event_id_1,
            customer_id=customer.customer_id,
            event_type="SMS_SENT",
            event_source="Moengage",
            event_timestamp=datetime(2023, 1, 15, 10, 0, 0),
            event_details={"message": "Offer sent"},
        )
        event2 = Event(
            event_id=event_id_2,
            customer_id=customer.customer_id,
            event_type="LOAN_LOGIN",
            event_source="LOS",
            event_timestamp=datetime(2023, 1, 20, 11, 30, 0),
            event_details={"stage": "login"},
        )
        db.session.add_all([offer1, offer2, event1, event2])
        db.session.commit()

    response = client.get(f"/customers/{customer.customer_id}")
    assert response.status_code == 200
    response_data = json.loads(response.data)

    assert response_data["customer_id"] == customer.customer_id
    assert response_data["mobile_number"] == customer.mobile_number
    assert response_data["pan_number"] == customer.pan_number
    assert response_data["segment"] == customer.segment
    assert response_data["dnd_flag"] == customer.dnd_flag

    assert len(response_data["current_offers"]) == 2
    assert any(o["offer_id"] == offer_id_1 for o in response_data["current_offers"])
    assert any(o["offer_id"] == offer_id_2 for o in response_data["current_offers"])

    assert len(response_data["journey_stages"]) == 2
    assert any(e["event_type"] == "SMS_SENT" for e in response_data["journey_stages"])
    assert any(e["event_type"] == "LOAN_LOGIN" for e in response_data["journey_stages"])


def test_get_customer_profile_not_found(client):
    """
    Test /customers/{customer_id} with a non-existent customer ID.
    """
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/customers/{non_existent_id}")
    assert response.status_code == 404
    response_data = json.loads(response.data)
    assert response_data["status"] == "error"
    assert "Customer not found" in response_data["message"]


def test_download_moengage_export_success(client, app):
    """
    Test the /campaigns/moengage-export endpoint for successful CSV download.
    FR31, FR44
    """
    customer1 = create_test_customer(mobile_number="1111111112", dnd_flag=False)
    customer2 = create_test_customer(
        mobile_number="1111111113", dnd_flag=True
    )  # DND customer
    customer3 = create_test_customer(mobile_number="1111111114", dnd_flag=False)

    with app.app_context():
        # Create active offers for non-DND customers
        offer1 = Offer(
            offer_id=str(uuid.uuid4()),
            customer_id=customer1.customer_id,
            offer_type="Fresh",
            offer_status="Active",
            propensity="High",
            start_date=date.today(),
            end_date=date.today(),
            channel="Web",
        )
        offer2 = Offer(
            offer_id=str(uuid.uuid4()),
            customer_id=customer3.customer_id,
            offer_type="New-new",
            offer_status="Active",
            propensity="Medium",
            start_date=date.today(),
            end_date=date.today(),
            channel="Mobile",
        )
        # Create an expired offer for a non-DND customer (should not be in export)
        offer_expired = Offer(
            offer_id=str(uuid.uuid4()),
            customer_id=customer1.customer_id,
            offer_type="Fresh",
            offer_status="Expired",
            propensity="Low",
            start_date=date(2023, 1, 1),
            end_date=date(2023, 1, 2),
            channel="Web",
        )
        db.session.add_all([offer1, offer2, offer_expired])
        db.session.commit()

    response = client.get("/campaigns/moengage-export")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"
    assert "attachment; filename=moengage_export_" in response.headers["Content-Disposition"]

    csv_data = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_data))
    header = next(reader)
    rows = list(reader)

    assert "customer_id" in header
    assert "mobile_number" in header
    assert "offer_id" in header
    assert "offer_type" in header
    assert "propensity" in header
    assert "dnd_flag" in header  # Should be included to show DND status, but DND customers filtered

    # Only customer1 and customer3 (non-DND, active offers) should be in the export
    assert len(rows) == 2
    mobile_numbers_in_export = [row[header.index("mobile_number")] for row in rows]
    assert "1111111112" in mobile_numbers_in_export
    assert "1111111114" in mobile_numbers_in_export
    assert "1111111113" not in mobile_numbers_in_export  # DND customer
    # No active offer for this customer, so not in export
    assert "9876543210" not in mobile_numbers_in_export


def test_download_duplicate_data_success(client):
    """
    Test the /data/duplicates endpoint for successful CSV download.
    FR32
    """
    # Create some customers with duplicate identifiers
    # Mobile number duplicate
    create_test_customer(mobile_number="2222222222", pan_number="PAN22222")
    create_test_customer(mobile_number="2222222222", pan_number="PAN22223")

    # PAN number duplicate
    create_test_customer(mobile_number="3333333331", pan_number="PAN33333")
    create_test_customer(mobile_number="3333333332", pan_number="PAN33333")

    # Unique customer
    create_test_customer(mobile_number="4444444444", pan_number="PAN44444")

    response = client.get("/data/duplicates")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"
    assert "attachment; filename=duplicate_data_" in response.headers["Content-Disposition"]

    csv_data = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_data))
    header = next(reader)
    rows = list(reader)

    assert "customer_id" in header
    assert "mobile_number" in header
    assert "pan_number" in header
    assert "duplicate_reason" in header

    # Expect 4 rows (2 for mobile duplicate, 2 for PAN duplicate)
    assert len(rows) == 4

    mobile_numbers = [row[header.index("mobile_number")] for row in rows]
    pan_numbers = [row[header.index("pan_number")] for row in rows]
    duplicate_reasons = [row[header.index("duplicate_reason")] for row in rows]

    assert mobile_numbers.count("2222222222") == 2
    assert pan_numbers.count("PAN33333") == 2
    assert "Duplicate Mobile" in duplicate_reasons
    assert "Duplicate PAN" in duplicate_reasons


def test_download_unique_data_success(client):
    """
    Test the /data/unique endpoint for successful CSV download.
    FR33
    """
    # Create some customers, some of which might be considered unique after deduplication
    # (assuming deduplication logic runs before this export, or this export shows what *would* be unique)
    # For this test, I'll just create distinct customers.
    create_test_customer(mobile_number="5555555551", pan_number="PAN55551")
    create_test_customer(mobile_number="5555555552", pan_number="PAN55552")
    create_test_customer(mobile_number="5555555553", pan_number="PAN55553")

    response = client.get("/data/unique")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "text/csv"
    assert "attachment; filename=unique_data_" in response.headers["Content-Disposition"]

    csv_data = response.data.decode("utf-8")
    reader = csv.reader(io.StringIO(csv_data))
    header = next(reader)
    rows = list(reader)

    assert "customer_id" in header
    assert "mobile_number" in header
    assert "pan_number" in header

    # Expect 3 rows for the 3 unique customers created
    assert len(rows) == 3
    mobile_numbers_in_export = [row[header.index("mobile_number")] for row in rows]
    assert "5555555551" in mobile_numbers_in_export
    assert "5555555552" in mobile_numbers_in_export
    assert "5555555553" in mobile_numbers_in_export


def test_download_error_data_success(client, app):
    """
    Test the /data/errors endpoint for successful Excel download.
    FR34
    """
    log_id_1 = str(uuid.uuid4())
    log_id_2 = str(uuid.uuid4())

    with app.app_context():
        log1 = IngestionLog(
            log_id=log_id_1,
            file_name="upload_file_1.csv",
            upload_timestamp=datetime.now(),
            status="FAILED",
            error_description="Row 2: Invalid mobile number; Row 5: Missing PAN",
        )
        log2 = IngestionLog(
            log_id=log_id_2,
            file_name="upload_file_2.csv",
            upload_timestamp=datetime.now(),
            status="PARTIAL_SUCCESS",
            error_description="Row 3: Aadhaar format error",
        )
        db.session.add_all([log1, log2])
        db.session.commit()

    response = client.get("/data/errors")
    assert response.status_code == 200
    # Excel files typically have 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    assert (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        in response.headers["Content-Type"]
    )
    assert "attachment; filename=error_log_" in response.headers["Content-Disposition"]

    # For Excel files, parsing content in tests is complex.
    # We primarily check status code and content type.
    assert len(response.data) > 0  # Ensure some data is returned