import pytest
import json
import base64
import uuid
from datetime import datetime

# Assuming your Flask app instance is named 'app' and is located in 'src/app.py'
# You might need to adjust this import path based on your actual project structure.
from src.app import app
# Assuming db and models are accessible from the main app instance or a dedicated extensions module
from app import db
from app.models import DataIngestionLog, Customer, Offer, CustomerEvent, Campaign # Import all models for potential future assertions

@pytest.fixture(scope='function')
def client():
    """
    Configures the Flask app for testing and provides a test client.
    Uses an in-memory SQLite database for isolated testing.
    """
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.app_context():
        db.create_all()  # Create tables for the in-memory SQLite DB
        yield app.test_client()  # Provide the test client
        db.session.remove()  # Clean up the session
        db.drop_all()  # Drop tables to ensure a clean state for the next test function

def generate_mock_csv_content(file_type: str) -> str:
    """Generates mock CSV content for different file types, base64 encoded."""
    if file_type == "Prospect":
        csv_data = (
            "mobile_number,pan,aadhaar_ref_number,name,email\n"
            "9876543210,ABCDE1234F,123456789012,John Doe,john.doe@example.com\n"
            "9876543211,FGHIJ5678K,234567890123,Jane Smith,jane.smith@example.com"
        )
    elif file_type in ["TW Loyalty", "Topup", "Employee loans"]:
        csv_data = (
            "mobile_number,loan_type,offer_amount,expiry_date\n"
            "9876543212,TW Loyalty,100000,2024-12-31\n"
            "9876543213,Topup,50000,2024-11-30"
        )
    else:
        csv_data = "header1,header2\nvalue1,value2"  # Generic fallback for unsupported types
    return base64.b64encode(csv_data.encode('utf-8')).decode('utf-8')

def test_upload_customer_details_success(client):
    """
    Test successful upload of customer details file via the admin API.
    Corresponds to FR29, FR30, FR31.
    """
    file_type = "Prospect"
    file_content_base64 = generate_mock_csv_content(file_type)
    uploaded_by = "test_admin_user"

    data = {
        "file_type": file_type,
        "file_content_base64": file_content_base64,
        "uploaded_by": uploaded_by
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 200
    response_data = json.loads(response.data)
    assert response_data['status'] == 'success'
    assert 'File uploaded, processing initiated' in response_data['message']
    assert 'log_id' in response_data
    # Validate that log_id is a valid UUID
    assert isinstance(uuid.UUID(response_data['log_id']), uuid.UUID)

    # Optional: Verify database entry for DataIngestionLog
    with app.app_context():
        log_entry = DataIngestionLog.query.filter_by(log_id=response_data['log_id']).first()
        assert log_entry is not None
        # The filename format is an assumption based on common practices.
        # Adjust if the actual implementation uses a different format.
        assert log_entry.file_name.startswith(f"{file_type}_upload_")
        assert log_entry.file_name.endswith(".csv")
        assert log_entry.status == 'SUCCESS'  # Or 'PENDING' if processing is asynchronous
        assert log_entry.uploaded_by == uploaded_by

        # Verify customer records were created (assuming synchronous processing for test simplicity)
        # This part depends on the actual implementation of the file processing logic.
        # For the mock CSV, 2 customers should be created.
        customers_count = Customer.query.count()
        assert customers_count == 2

def test_upload_customer_details_missing_file_content(client):
    """
    Test upload with missing 'file_content_base64' in the request body.
    """
    file_type = "Prospect"
    uploaded_by = "test_admin_user"

    data = {
        "file_type": file_type,
        "uploaded_by": uploaded_by
        # 'file_content_base64' is intentionally missing
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'file_content_base64' in response_data['message']
    assert 'is required' in response_data['message']

def test_upload_customer_details_missing_file_type(client):
    """
    Test upload with missing 'file_type' in the request body.
    """
    file_content_base64 = generate_mock_csv_content("Prospect")
    uploaded_by = "test_admin_user"

    data = {
        "file_content_base64": file_content_base64,
        "uploaded_by": uploaded_by
        # 'file_type' is intentionally missing
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'file_type' in response_data['message']
    assert 'is required' in response_data['message']

def test_upload_customer_details_invalid_file_type(client):
    """
    Test upload with an unsupported 'file_type'.
    """
    file_type = "UnsupportedLoanType"
    file_content_base64 = generate_mock_csv_content(file_type)
    uploaded_by = "test_admin_user"

    data = {
        "file_type": file_type,
        "file_content_base64": file_content_base64,
        "uploaded_by": uploaded_by
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'Invalid file_type' in response_data['message']

def test_upload_customer_details_empty_file_content(client):
    """
    Test upload with empty base64 encoded file content.
    """
    file_type = "Prospect"
    file_content_base64 = base64.b64encode("".encode('utf-8')).decode('utf-8')  # Empty content
    uploaded_by = "test_admin_user"

    data = {
        "file_type": file_type,
        "file_content_base64": file_content_base64,
        "uploaded_by": uploaded_by
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'File content cannot be empty' in response_data['message']

def test_upload_customer_details_invalid_base64_encoding(client):
    """
    Test upload with malformed base64 encoded content.
    """
    file_type = "Prospect"
    file_content_base64 = "not-a-valid-base64-string!"  # Invalid base64
    uploaded_by = "test_admin_user"

    data = {
        "file_type": file_type,
        "file_content_base64": file_content_base64,
        "uploaded_by": uploaded_by
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'Invalid base64 encoding' in response_data['message']

def test_upload_customer_details_missing_uploaded_by(client):
    """
    Test upload with missing 'uploaded_by' field.
    """
    file_type = "Prospect"
    file_content_base64 = generate_mock_csv_content(file_type)

    data = {
        "file_type": file_type,
        "file_content_base64": file_content_base64
        # 'uploaded_by' is intentionally missing
    }

    response = client.post(
        '/api/admin/upload/customer-details',
        data=json.dumps(data),
        content_type='application/json'
    )

    assert response.status_code == 400
    response_data = json.loads(response.data)
    assert response_data['status'] == 'error'
    assert 'uploaded_by' in response_data['message']
    assert 'is required' in response_data['message']