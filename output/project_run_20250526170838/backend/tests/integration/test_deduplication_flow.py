import pytest
import json
import base64
import csv
from io import StringIO
import uuid
from datetime import datetime

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

# --- Minimal Flask App and DB Setup for Testing Context ---
# In a real project, these would be imported from your main application files
# (e.g., from backend.app import create_app, db; from backend.models import Customer, IngestionLog)

db = SQLAlchemy()

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    mobile_number = db.Column(db.Text, unique=True)
    pan_number = db.Column(db.Text, unique=True)
    aadhaar_number = db.Column(db.Text, unique=True)
    ucid_number = db.Column(db.Text, unique=True)
    loan_application_number = db.Column(db.Text, unique=True)
    dnd_flag = db.Column(db.Boolean, default=False)
    segment = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    updated_at = db.Column(db.TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

class IngestionLog(db.Model):
    __tablename__ = 'ingestion_logs'
    log_id = db.Column(db.Text, primary_key=True, default=lambda: str(uuid.uuid4()))
    file_name = db.Column(db.Text, nullable=False)
    upload_timestamp = db.Column(db.TIMESTAMP, default=datetime.utcnow)
    status = db.Column(db.Text)
    error_description = db.Column(db.Text)

def create_app():
    app = Flask(__name__)
    app.config['TESTING'] = True
    # Use a dedicated test database for isolation
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost:5432/test_cdp_db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    # Define API endpoints directly within the test app for self-containment
    @app.route('/admin/customer-data/upload', methods=['POST'])
    def upload_customer_data():
        data = request.json
        file_content_b64 = data.get('file_content')
        file_name = data.get('file_name')
        # loan_type = data.get('loan_type') # Not directly used in deduplication logic but part of request

        if not file_content_b64 or not file_name:
            return jsonify({"status": "error", "message": "Missing file_content or file_name"}), 400

        success_count = 0
        error_count = 0
        errors = []
        log_id = str(uuid.uuid4())

        try:
            decoded_content = base64.b64decode(file_content_b64).decode('utf-8')
            csv_file = StringIO(decoded_content)
            reader = csv.DictReader(csv_file)

            for row in reader:
                mobile = row.get('mobile_number')
                pan = row.get('pan_number')
                aadhaar = row.get('aadhaar_number')
                ucid = row.get('ucid_number')
                lan = row.get('loan_application_number')

                # Basic validation: At least one primary identifier must be present
                if not (mobile or pan or aadhaar or ucid or lan):
                    error_count += 1
                    errors.append(f"Row missing all primary identifiers: {row}")
                    continue

                # Deduplication logic (FR3, FR4, FR5, FR6)
                # Check for existing customer by any of the identifiers
                existing_customer = None
                if mobile:
                    existing_customer = Customer.query.filter_by(mobile_number=mobile).first()
                if not existing_customer and pan:
                    existing_customer = Customer.query.filter_by(pan_number=pan).first()
                if not existing_customer and aadhaar:
                    existing_customer = Customer.query.filter_by(aadhaar_number=aadhaar).first()
                if not existing_customer and ucid:
                    existing_customer = Customer.query.filter_by(ucid_number=ucid).first()
                if not existing_customer and lan:
                    existing_customer = Customer.query.filter_by(loan_application_number=lan).first()

                if existing_customer:
                    # Update existing customer with new info if available
                    # This is a simplified update logic for MVP.
                    # More complex merge strategies might be needed in production.
                    if mobile and not existing_customer.mobile_number:
                        existing_customer.mobile_number = mobile
                    if pan and not existing_customer.pan_number:
                        existing_customer.pan_number = pan
                    if aadhaar and not existing_customer.aadhaar_number:
                        existing_customer.aadhaar_number = aadhaar
                    if ucid and not existing_customer.ucid_number:
                        existing_customer.ucid_number = ucid
                    if lan and not existing_customer.loan_application_number:
                        existing_customer.loan_application_number = lan

                    # Update other fields if present in CSV and not null in DB
                    if 'dnd_flag' in row and row['dnd_flag'] is not None:
                        existing_customer.dnd_flag = row['dnd_flag'].lower() == 'true'
                    if 'segment' in row and row['segment'] is not None:
                        existing_customer.segment = row['segment']

                    db.session.add(existing_customer) # Mark for update
                    success_count += 1 # Count as success because it was handled (updated or already existed)
                else:
                    # Create new customer
                    new_customer = Customer(
                        mobile_number=mobile,
                        pan_number=pan,
                        aadhaar_number=aadhaar,
                        ucid_number=ucid,
                        loan_application_number=lan,
                        dnd_flag=row.get('dnd_flag', 'false').lower() == 'true',
                        segment=row.get('segment')
                    )
                    db.session.add(new_customer)
                    success_count += 1

            db.session.commit()
            log_status = "SUCCESS" if not errors else "PARTIAL_SUCCESS"
            log_description = json.dumps(errors) if errors else None
            ingestion_log = IngestionLog(
                log_id=log_id,
                file_name=file_name,
                status=log_status,
                error_description=log_description
            )
            db.session.add(ingestion_log)
            db.session.commit()

            return jsonify({
                "status": log_status.lower(),
                "log_id": log_id,
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors
            }), 200

        except Exception as e:
            db.session.rollback()
            ingestion_log = IngestionLog(
                log_id=log_id,
                file_name=file_name,
                status="FAILED",
                error_description=str(e)
            )
            db.session.add(ingestion_log)
            db.session.commit()
            return jsonify({"status": "error", "message": str(e), "log_id": log_id}), 500

    @app.route('/api/leads', methods=['POST'])
    def receive_lead():
        data = request.json
        mobile = data.get('mobile_number')
        pan = data.get('pan_number')
        aadhaar = data.get('aadhaar_number')
        # loan_type = data.get('loan_type') # Not used in customer creation
        # source_channel = data.get('source_channel') # Not used in customer creation

        if not (mobile or pan or aadhaar):
            return jsonify({"status": "error", "message": "At least one identifier (mobile, PAN, Aadhaar) is required"}), 400

        existing_customer = None
        if mobile:
            existing_customer = Customer.query.filter_by(mobile_number=mobile).first()
        if not existing_customer and pan:
            existing_customer = Customer.query.filter_by(pan_number=pan).first()
        if not existing_customer and aadhaar:
            existing_customer = Customer.query.filter_by(aadhaar_number=aadhaar).first()

        if existing_customer:
            # If customer exists, return existing customer_id
            # For lead API, we typically don't update existing customer's core identifiers
            # but might log the lead event separately.
            return jsonify({
                "status": "success",
                "message": "Customer already exists, lead processed for existing customer.",
                "customer_id": existing_customer.customer_id
            }), 200
        else:
            # Create new customer
            new_customer = Customer(
                mobile_number=mobile,
                pan_number=pan,
                aadhaar_number=aadhaar,
                segment="Prospect" # Default segment for new leads from API
            )
            db.session.add(new_customer)
            db.session.commit()
            return jsonify({
                "status": "success",
                "customer_id": new_customer.customer_id
            }), 201

    return app

# --- Pytest Fixtures ---

@pytest.fixture(scope='session')
def app():
    """Fixture for the Flask app, creating and dropping tables once per test session."""
    app = create_app()
    with app.app_context():
        # Ensure tables are created for the test database
        db.create_all()
        yield app
        # Clean up tables after all tests in the session are done
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """Fixture for the Flask test client, providing a fresh client for each test function."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(app):
    """
    Fixture for a database session, ensuring a clean state for each test function
    by rolling back the transaction after the test.
    """
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()
        db.session.configure(bind=connection)
        yield db.session
        transaction.rollback()
        connection.close()
        db.session.remove()

# --- Helper Function ---

def create_csv_payload(data_rows):
    """
    Helper function to create a base64 encoded CSV string from a list of dictionaries.
    Assumes a fixed set of possible column names for customer data.
    """
    output = StringIO()
    fieldnames = [
        'mobile_number', 'pan_number', 'aadhaar_number', 'ucid_number',
        'loan_application_number', 'dnd_flag', 'segment'
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data_rows)
    csv_string = output.getvalue()
    return base64.b64encode(csv_string.encode('utf-8')).decode('utf-8')

# --- Integration Tests for Deduplication Flow ---

def test_upload_unique_customer_data(client, db_session):
    """
    Test uploading a CSV with unique customer data.
    Verifies FR3 (deduplication) by ensuring new unique customers are created.
    """
    data_rows = [
        {'mobile_number': '9876543210', 'pan_number': 'ABCDE1234F', 'aadhaar_number': '111122223333', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'},
        {'mobile_number': '9876543211', 'pan_number': 'ABCDE1234G', 'aadhaar_number': '111122223334', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C2'}
    ]
    payload = {
        'file_content': create_csv_payload(data_rows),
        'file_name': 'unique_customers.csv',
        'loan_type': 'Prospect'
    }

    response = client.post('/admin/customer-data/upload', json=payload)
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 2
    assert resp_data['error_count'] == 0

    # Verify customers in DB
    customers = db_session.query(Customer).all()
    assert len(customers) == 2
    assert any(c.mobile_number == '9876543210' for c in customers)
    assert any(c.mobile_number == '9876543211' for c in customers)

    # Verify log entry
    log = db_session.query(IngestionLog).filter_by(log_id=resp_data['log_id']).first()
    assert log is not None
    assert log.status == 'SUCCESS'
    assert log.file_name == 'unique_customers.csv'

def test_upload_duplicate_mobile_number(client, db_session):
    """
    Test deduplication based on mobile number.
    FR3: The system shall deduplicate customer data based on Mobile number...
    """
    # First upload: Create a customer
    initial_data = [
        {'mobile_number': '9999999999', 'pan_number': 'PAN12345A', 'aadhaar_number': 'AADHAAR1', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial.csv',
        'loan_type': 'Prospect'
    })
    initial_customer = db_session.query(Customer).filter_by(mobile_number='9999999999').first()
    assert initial_customer is not None
    assert db_session.query(Customer).count() == 1

    # Second upload: Same mobile, different PAN/Aadhaar (should deduplicate and update)
    duplicate_data = [
        {'mobile_number': '9999999999', 'pan_number': 'PAN67890B', 'aadhaar_number': 'AADHAAR2', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C3'}
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(duplicate_data),
        'file_name': 'duplicate_mobile.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 1 # It processed one row successfully (by updating/identifying existing)
    assert resp_data['error_count'] == 0

    # Verify only one customer record exists for this mobile number
    customers = db_session.query(Customer).filter_by(mobile_number='9999999999').all()
    assert len(customers) == 1
    assert db_session.query(Customer).count() == 1 # Total customers in DB should still be 1

    # Verify the existing customer record was updated with new info (dnd_flag, segment)
    updated_customer = customers[0]
    assert updated_customer.dnd_flag is True # This should be updated from 'false' to 'true'
    assert updated_customer.segment == 'C3' # This should be updated from 'C1' to 'C3'
    # PAN/Aadhaar should not be overwritten if already present
    assert updated_customer.pan_number == 'PAN12345A'
    assert updated_customer.aadhaar_number == 'AADHAAR1'

def test_upload_duplicate_pan_number(client, db_session):
    """
    Test deduplication based on PAN number.
    FR3: The system shall deduplicate customer data based on ... Pan number...
    """
    # First upload: Create a customer
    initial_data = [
        {'mobile_number': '1111111111', 'pan_number': 'PANTEST1', 'aadhaar_number': 'AADHAARX', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial_pan.csv',
        'loan_type': 'Prospect'
    })
    assert db_session.query(Customer).count() == 1

    # Second upload: Same PAN, different mobile/Aadhaar
    duplicate_data = [
        {'mobile_number': '2222222222', 'pan_number': 'PANTEST1', 'aadhaar_number': 'AADHAARY', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C4'}
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(duplicate_data),
        'file_name': 'duplicate_pan.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 1
    assert resp_data['error_count'] == 0

    # Verify only one customer record exists for this PAN number
    customers = db_session.query(Customer).filter_by(pan_number='PANTEST1').all()
    assert len(customers) == 1
    assert db_session.query(Customer).count() == 1

    updated_customer = customers[0]
    assert updated_customer.dnd_flag is True
    assert updated_customer.segment == 'C4'
    # The mobile number from the second upload should not overwrite if it was already present.
    assert updated_customer.mobile_number == '1111111111'
    assert updated_customer.aadhaar_number == 'AADHAARX'

def test_upload_duplicate_aadhaar_number(client, db_session):
    """
    Test deduplication based on Aadhaar number.
    FR3: The system shall deduplicate customer data based on ... Aadhaar reference number...
    """
    initial_data = [
        {'mobile_number': '3333333333', 'pan_number': 'PANTEST2', 'aadhaar_number': 'AADHAARZ', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial_aadhaar.csv',
        'loan_type': 'Prospect'
    })
    assert db_session.query(Customer).count() == 1

    duplicate_data = [
        {'mobile_number': '4444444444', 'pan_number': 'PANTEST3', 'aadhaar_number': 'AADHAARZ', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C5'}
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(duplicate_data),
        'file_name': 'duplicate_aadhaar.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 1
    assert resp_data['error_count'] == 0

    customers = db_session.query(Customer).filter_by(aadhaar_number='AADHAARZ').all()
    assert len(customers) == 1
    assert db_session.query(Customer).count() == 1

    updated_customer = customers[0]
    assert updated_customer.dnd_flag is True
    assert updated_customer.segment == 'C5'
    assert updated_customer.mobile_number == '3333333333'
    assert updated_customer.pan_number == 'PANTEST2'

def test_upload_duplicate_ucid_number(client, db_session):
    """
    Test deduplication based on UCID number.
    FR3: The system shall deduplicate customer data based on ... UCID number...
    """
    initial_data = [
        {'mobile_number': '5555555555', 'pan_number': 'PANTEST4', 'aadhaar_number': 'AADHAARA', 'ucid_number': 'UCID123', 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial_ucid.csv',
        'loan_type': 'Prospect'
    })
    assert db_session.query(Customer).count() == 1

    duplicate_data = [
        {'mobile_number': '6666666666', 'pan_number': 'PANTEST5', 'aadhaar_number': 'AADHAARB', 'ucid_number': 'UCID123', 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C6'}
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(duplicate_data),
        'file_name': 'duplicate_ucid.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 1
    assert resp_data['error_count'] == 0

    customers = db_session.query(Customer).filter_by(ucid_number='UCID123').all()
    assert len(customers) == 1
    assert db_session.query(Customer).count() == 1

    updated_customer = customers[0]
    assert updated_customer.dnd_flag is True
    assert updated_customer.segment == 'C6'
    assert updated_customer.mobile_number == '5555555555'
    assert updated_customer.pan_number == 'PANTEST4'
    assert updated_customer.aadhaar_number == 'AADHAARA'

def test_upload_duplicate_loan_application_number(client, db_session):
    """
    Test deduplication based on Loan Application Number.
    FR3: The system shall deduplicate customer data based on ... previous loan application number.
    """
    initial_data = [
        {'mobile_number': '7777777777', 'pan_number': 'PANTEST6', 'aadhaar_number': 'AADHAARC', 'ucid_number': None, 'loan_application_number': 'LAN001', 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial_lan.csv',
        'loan_type': 'Prospect'
    })
    assert db_session.query(Customer).count() == 1

    duplicate_data = [
        {'mobile_number': '8888888888', 'pan_number': 'PANTEST7', 'aadhaar_number': 'AADHAARD', 'ucid_number': None, 'loan_application_number': 'LAN001', 'dnd_flag': 'true', 'segment': 'C7'}
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(duplicate_data),
        'file_name': 'duplicate_lan.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 1
    assert resp_data['error_count'] == 0

    customers = db_session.query(Customer).filter_by(loan_application_number='LAN001').all()
    assert len(customers) == 1
    assert db_session.query(Customer).count() == 1

    updated_customer = customers[0]
    assert updated_customer.dnd_flag is True
    assert updated_customer.segment == 'C7'
    assert updated_customer.mobile_number == '7777777777'
    assert updated_customer.pan_number == 'PANTEST6'
    assert updated_customer.aadhaar_number == 'AADHAARC'

def test_upload_mixed_unique_and_duplicate_data(client, db_session):
    """
    Test uploading a CSV with a mix of unique and duplicate customer data.
    Ensures correct handling of both new records and updates to existing ones.
    """
    # Initial data: 1 customer
    initial_data = [
        {'mobile_number': '1000000000', 'pan_number': 'PANMIX1', 'aadhaar_number': 'AADHAARM1', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'}
    ]
    client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(initial_data),
        'file_name': 'initial_mix.csv',
        'loan_type': 'Prospect'
    })
    assert db_session.query(Customer).count() == 1

    # Mixed data:
    # 1. New unique customer (mobile: 1000000001)
    # 2. Duplicate of existing customer (by mobile: 1000000000) - should update
    # 3. New unique customer (mobile: 1000000002)
    # 4. Duplicate of existing customer (by PAN: PANMIX1) - should update
    mixed_data = [
        {'mobile_number': '1000000001', 'pan_number': 'PANMIX2', 'aadhaar_number': 'AADHAARM2', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C2'},
        {'mobile_number': '1000000000', 'pan_number': 'PANMIX3', 'aadhaar_number': 'AADHAARM3', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C8'}, # Duplicate mobile
        {'mobile_number': '1000000002', 'pan_number': 'PANMIX4', 'aadhaar_number': 'AADHAARM4', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C3'},
        {'mobile_number': '1000000003', 'pan_number': 'PANMIX1', 'aadhaar_number': 'AADHAARM5', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C9'}  # Duplicate PAN
    ]
    response = client.post('/admin/customer-data/upload', json={
        'file_content': create_csv_payload(mixed_data),
        'file_name': 'mixed_data.csv',
        'loan_type': 'Prospect'
    })
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['success_count'] == 4 # All rows processed, 2 new, 2 updated
    assert resp_data['error_count'] == 0

    # Verify total unique customers in DB
    # Initial: 1 (1000000000/PANMIX1)
    # New from mixed: 2 (1000000001, 1000000002)
    # Duplicates: 2 (1000000000, PANMIX1) refer to existing customers.
    # So, total unique customers should be 1 (initial) + 2 (new) = 3
    assert db_session.query(Customer).count() == 3

    # Verify specific customers and their updated states
    customer_1000000000 = db_session.query(Customer).filter_by(mobile_number='1000000000').first()
    assert customer_1000000000 is not None
    assert customer_1000000000.dnd_flag is True # Updated from false by row 2
    assert customer_1000000000.segment == 'C9' # Updated from C1 by row 4 (last update wins for segment in this simplified logic)
    assert customer_1000000000.pan_number == 'PANMIX1' # Should remain original PAN

    customer_1000000001 = db_session.query(Customer).filter_by(mobile_number='1000000001').first()
    assert customer_1000000001 is not None
    assert customer_1000000001.dnd_flag is False
    assert customer_1000000001.segment == 'C2'

    customer_1000000002 = db_session.query(Customer).filter_by(mobile_number='1000000002').first()
    assert customer_1000000002 is not None
    assert customer_1000000002.dnd_flag is False
    assert customer_1000000002.segment == 'C3'

def test_api_leads_unique_customer(client, db_session):
    """
    Test real-time lead ingestion for a unique customer.
    FR11: The system shall receive real-time data from Insta or E-aggregators into CDP via Open APIs (Lead Generation...).
    """
    payload = {
        "mobile_number": "9123456789",
        "pan_number": "UNIQUEPAN1",
        "aadhaar_number": "UNIQUEAADHAAR1",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator"
    }
    response = client.post('/api/leads', json=payload)
    assert response.status_code == 201 # Created
    resp_data = response.get_json()
    assert resp_data['status'] == 'success'
    assert 'customer_id' in resp_data

    customer = db_session.query(Customer).filter_by(mobile_number='9123456789').first()
    assert customer is not None
    assert customer.customer_id == resp_data['customer_id']
    assert customer.pan_number == 'UNIQUEPAN1'
    assert customer.aadhaar_number == 'UNIQUEAADHAAR1'
    assert customer.segment == 'Prospect' # Default segment for new leads

def test_api_leads_duplicate_customer_by_mobile(client, db_session):
    """
    Test real-time lead ingestion for a duplicate customer (by mobile).
    FR3: The system shall deduplicate customer data based on Mobile number...
    """
    # First, create a customer via API
    initial_payload = {
        "mobile_number": "9111111111",
        "pan_number": "INITIALPAN",
        "aadhaar_number": "INITIALAADHAAR",
        "loan_type": "Home Loan",
        "source_channel": "Insta"
    }
    response_initial = client.post('/api/leads', json=initial_payload)
    assert response_initial.status_code == 201
    initial_customer_id = response_initial.get_json()['customer_id']
    assert db_session.query(Customer).count() == 1

    # Second API call with same mobile number, different PAN/Aadhaar
    duplicate_payload = {
        "mobile_number": "9111111111", # Duplicate mobile
        "pan_number": "DUPLICATEPAN",
        "aadhaar_number": "DUPLICATEAADHAAR",
        "loan_type": "Car Loan",
        "source_channel": "E-aggregator"
    }
    response_duplicate = client.post('/api/leads', json=duplicate_payload)
    assert response_duplicate.status_code == 200 # OK, not Created (as it's an existing customer)
    resp_data = response_duplicate.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['customer_id'] == initial_customer_id # Should return the existing customer_id
    assert "Customer already exists" in resp_data['message']

    # Verify no new customer was created
    assert db_session.query(Customer).count() == 1

    # Verify the existing customer's data (PAN/Aadhaar should not be overwritten if already present)
    customer = db_session.query(Customer).filter_by(customer_id=initial_customer_id).first()
    assert customer.mobile_number == '9111111111'
    assert customer.pan_number == 'INITIALPAN' # Should retain original PAN
    assert customer.aadhaar_number == 'INITIALAADHAAR' # Should retain original Aadhaar

def test_api_leads_duplicate_customer_by_pan(client, db_session):
    """
    Test real-time lead ingestion for a duplicate customer (by PAN).
    FR3: The system shall deduplicate customer data based on ... Pan number...
    """
    initial_payload = {
        "mobile_number": "9222222222",
        "pan_number": "PANEXISTING",
        "aadhaar_number": "AADHAARORIGINAL",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator"
    }
    response_initial = client.post('/api/leads', json=initial_payload)
    assert response_initial.status_code == 201
    initial_customer_id = response_initial.get_json()['customer_id']
    assert db_session.query(Customer).count() == 1

    duplicate_payload = {
        "mobile_number": "9333333333", # Different mobile
        "pan_number": "PANEXISTING", # Duplicate PAN
        "aadhaar_number": "AADHAARNEW",
        "loan_type": "Car Loan",
        "source_channel": "E-aggregator"
    }
    response_duplicate = client.post('/api/leads', json=duplicate_payload)
    assert response_duplicate.status_code == 200
    resp_data = response_duplicate.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['customer_id'] == initial_customer_id
    assert "Customer already exists" in resp_data['message']

    assert db_session.query(Customer).count() == 1
    customer = db_session.query(Customer).filter_by(customer_id=initial_customer_id).first()
    assert customer.mobile_number == '9222222222' # Should retain original mobile
    assert customer.pan_number == 'PANEXISTING'
    assert customer.aadhaar_number == 'AADHAARORIGINAL' # Should retain original Aadhaar

def test_api_leads_duplicate_customer_by_aadhaar(client, db_session):
    """
    Test real-time lead ingestion for a duplicate customer (by Aadhaar).
    FR3: The system shall deduplicate customer data based on ... Aadhaar reference number...
    """
    initial_payload = {
        "mobile_number": "9444444444",
        "pan_number": "PANORIGINAL",
        "aadhaar_number": "AADHAAR_EXISTING",
        "loan_type": "Personal Loan",
        "source_channel": "E-aggregator"
    }
    response_initial = client.post('/api/leads', json=initial_payload)
    assert response_initial.status_code == 201
    initial_customer_id = response_initial.get_json()['customer_id']
    assert db_session.query(Customer).count() == 1

    duplicate_payload = {
        "mobile_number": "9555555555", # Different mobile
        "pan_number": "PANNEW",
        "aadhaar_number": "AADHAAR_EXISTING", # Duplicate Aadhaar
        "loan_type": "Car Loan",
        "source_channel": "E-aggregator"
    }
    response_duplicate = client.post('/api/leads', json=duplicate_payload)
    assert response_duplicate.status_code == 200
    resp_data = response_duplicate.get_json()
    assert resp_data['status'] == 'success'
    assert resp_data['customer_id'] == initial_customer_id
    assert "Customer already exists" in resp_data['message']

    assert db_session.query(Customer).count() == 1
    customer = db_session.query(Customer).filter_by(customer_id=initial_customer_id).first()
    assert customer.mobile_number == '9444444444' # Should retain original mobile
    assert customer.pan_number == 'PANORIGINAL' # Should retain original PAN
    assert customer.aadhaar_number == 'AADHAAR_EXISTING'

def test_upload_csv_missing_all_identifiers(client, db_session):
    """
    Test uploading a CSV row that is missing all primary identifiers.
    Should be counted as an error and logged.
    FR38: The Admin Portal shall generate an error file with an 'Error Desc' column upon upload failure.
    """
    data_rows = [
        {'mobile_number': '9876543210', 'pan_number': 'ABCDE1234F', 'aadhaar_number': '111122223333', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'false', 'segment': 'C1'},
        {'mobile_number': None, 'pan_number': None, 'aadhaar_number': None, 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C2'}, # This row is an error
        {'mobile_number': '9876543211', 'pan_number': 'ABCDE1234G', 'aadhaar_number': '111122223334', 'ucid_number': None, 'loan_application_number': None, 'dnd_flag': 'true', 'segment': 'C2'}
    ]
    payload = {
        'file_content': create_csv_payload(data_rows),
        'file_name': 'missing_identifiers.csv',
        'loan_type': 'Prospect'
    }

    response = client.post('/admin/customer-data/upload', json=payload)
    assert response.status_code == 200
    resp_data = response.get_json()
    assert resp_data['status'] == 'partial_success'
    assert resp_data['success_count'] == 2 # Two valid rows processed
    assert resp_data['error_count'] == 1 # One error row
    assert len(resp_data['errors']) == 1
    assert "Row missing all primary identifiers" in resp_data['errors'][0]

    # Verify customers in DB
    customers = db_session.query(Customer).all()
    assert len(customers) == 2 # Only the two valid customers should be added
    assert any(c.mobile_number == '9876543210' for c in customers)
    assert any(c.mobile_number == '9876543211' for c in customers)

    # Verify log entry
    log = db_session.query(IngestionLog).filter_by(log_id=resp_data['log_id']).first()
    assert log is not None
    assert log.status == 'PARTIAL_SUCCESS'
    assert log.file_name == 'missing_identifiers.csv'
    assert "Row missing all primary identifiers" in log.error_description