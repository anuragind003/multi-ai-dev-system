import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models import VKYCRecording, VKYCRecordingStatus
from schemas import VKYCRecordingCreate, VKYCRecordingUpdate
from datetime import date, datetime
from io import StringIO

# Assuming conftest.py sets up the test client and db_session fixtures

def test_create_recording(client: TestClient, db_session: Session, sample_recording_data: dict):
    """Test creating a single VKYC recording."""
    response = client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    assert response.status_code == 200
    data = response.json()
    assert data["lan_id"] == sample_recording_data["lan_id"]
    assert data["status"] == VKYCRecordingStatus.PENDING.value
    assert "id" in data
    assert db_session.query(VKYCRecording).filter_by(lan_id=sample_recording_data["lan_id"]).first() is not None

def test_create_duplicate_recording(client: TestClient, db_session: Session, sample_recording_data: dict):
    """Test creating a duplicate VKYC recording."""
    # First creation
    client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    # Second creation attempt
    response = client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    assert response.status_code == 409 # Conflict
    assert "already exists" in response.json()["detail"]

def test_get_recording_by_lan_id(client: TestClient, db_session: Session, sample_recording_data: dict):
    """Test retrieving a VKYC recording by LAN ID."""
    client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    response = client.get(f"/api/v1/vkyc-recordings/{sample_recording_data['lan_id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["lan_id"] == sample_recording_data["lan_id"]

def test_get_non_existent_recording(client: TestClient):
    """Test retrieving a non-existent VKYC recording."""
    response = client.get("/api/v1/vkyc-recordings/NONEXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_list_recordings(client: TestClient, db_session: Session):
    """Test listing VKYC recordings with pagination and filtering."""
    rec1 = VKYCRecordingCreate(lan_id="LAN001", recording_date=date(2023, 1, 1), file_path="/path/rec1.mp4")
    rec2 = VKYCRecordingCreate(lan_id="LAN002", recording_date=date(2023, 1, 2), file_path="/path/rec2.mp4")
    rec3 = VKYCRecordingCreate(lan_id="LAN003", recording_date=date(2023, 1, 3), file_path="/path/rec3.mp4")

    # Manually add to DB for controlled test data
    db_session.add(VKYCRecording(**rec1.model_dump(), status=VKYCRecordingStatus.INGESTED))
    db_session.add(VKYCRecording(**rec2.model_dump(), status=VKYCRecordingStatus.PENDING))
    db_session.add(VKYCRecording(**rec3.model_dump(), status=VKYCRecordingStatus.INGESTED))
    db_session.commit()

    response = client.get("/api/v1/vkyc-recordings/")
    assert response.status_code == 200
    assert len(response.json()) >= 3 # May include data from other tests if not properly isolated

    response = client.get("/api/v1/vkyc-recordings/?limit=1")
    assert len(response.json()) == 1

    response = client.get(f"/api/v1/vkyc-recordings/?status={VKYCRecordingStatus.INGESTED.value}")
    assert response.status_code == 200
    assert len(response.json()) >= 2 # At least LAN001, LAN003
    for rec in response.json():
        assert rec["status"] == VKYCRecordingStatus.INGESTED.value

def test_update_recording_status(client: TestClient, db_session: Session, sample_recording_data: dict):
    """Test updating a VKYC recording's status."""
    client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    update_data = {"status": VKYCRecordingStatus.INGESTED.value}
    response = client.put(f"/api/v1/vkyc-recordings/{sample_recording_data['lan_id']}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["lan_id"] == sample_recording_data["lan_id"]
    assert data["status"] == VKYCRecordingStatus.INGESTED.value

    db_rec = db_session.query(VKYCRecording).filter_by(lan_id=sample_recording_data["lan_id"]).first()
    assert db_rec.status == VKYCRecordingStatus.INGESTED

def test_update_non_existent_recording(client: TestClient):
    """Test updating a non-existent VKYC recording."""
    update_data = {"status": VKYCRecordingStatus.INGESTED.value}
    response = client.put("/api/v1/vkyc-recordings/NONEXISTENT", json=update_data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_delete_recording(client: TestClient, db_session: Session, sample_recording_data: dict):
    """Test deleting a VKYC recording."""
    client.post("/api/v1/vkyc-recordings/", json=sample_recording_data)
    response = client.delete(f"/api/v1/vkyc-recordings/{sample_recording_data['lan_id']}")
    assert response.status_code == 204
    assert db_session.query(VKYCRecording).filter_by(lan_id=sample_recording_data["lan_id"]).first() is None

def test_delete_non_existent_recording(client: TestClient):
    """Test deleting a non-existent VKYC recording."""
    response = client.delete("/api/v1/vkyc-recordings/NONEXISTENT")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

def test_upload_csv_success(client: TestClient, db_session: Session, sample_csv_content: str):
    """Test successful CSV upload and bulk ingestion."""
    files = {"file": ("metadata.csv", StringIO(sample_csv_content), "text/csv")}
    response = client.post("/api/v1/vkyc-recordings/upload-csv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 4
    assert data["successfully_ingested"] == 4
    assert data["failed_to_ingest"] == 0
    assert not data["errors"]

    # Verify records in DB
    assert db_session.query(VKYCRecording).filter_by(lan_id="LAN00001").first() is not None
    assert db_session.query(VKYCRecording).filter_by(lan_id="LAN00002").first() is not None

def test_upload_csv_with_duplicates(client: TestClient, db_session: Session):
    """Test CSV upload with duplicate LAN IDs."""
    csv_content = """lan_id,recording_date,file_path
LAN_DUP,2023-01-01,/path/dup1.mp4
LAN_DUP,2023-01-02,/path/dup2.mp4
LAN_UNIQUE,2023-01-03,/path/unique.mp4
"""
    files = {"file": ("duplicate.csv", StringIO(csv_content), "text/csv")}
    response = client.post("/api/v1/vkyc-recordings/upload-csv", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    assert data["successfully_ingested"] == 2 # LAN_DUP (first one), LAN_UNIQUE
    assert data["failed_to_ingest"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["lan_id"] == "LAN_DUP"
    assert "Duplicate LAN ID" in data["errors"][0]["reason"]

    # Verify only one LAN_DUP exists in DB
    assert db_session.query(VKYCRecording).filter_by(lan_id="LAN_DUP").count() == 1
    assert db_session.query(VKYCRecording).filter_by(lan_id="LAN_UNIQUE").count() == 1

def test_upload_csv_invalid_format(client: TestClient, invalid_csv_content: str):
    """Test CSV upload with invalid format (missing required columns, bad date)."""
    files = {"file": ("invalid.csv", StringIO(invalid_csv_content), "text/csv")}
    response = client.post("/api/v1/vkyc-recordings/upload-csv", files=files)
    assert response.status_code == 200 # Still 200, but with errors reported
    data = response.json()
    assert data["total_records"] == 2
    assert data["successfully_ingested"] == 0
    assert data["failed_to_ingest"] == 2
    assert len(data["errors"]) == 2
    assert "file_path" in data["errors"][0]["reason"] # Missing file_path column
    assert "Invalid recording_date format" in data["errors"][1]["reason"]

def test_upload_non_csv_file(client: TestClient):
    """Test uploading a non-CSV file."""
    files = {"file": ("test.txt", StringIO("some text"), "text/plain")}
    response = client.post("/api/v1/vkyc-recordings/upload-csv", files=files)
    assert response.status_code == 400
    assert "Only CSV files are allowed" in response.json()["detail"]

def test_health_check(client: TestClient):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data

def test_api_key_authentication(client: TestClient, sample_recording_data: dict):
    """Test API key authentication."""
    # No API key
    response = client.post("/api/v1/vkyc-recordings/", json=sample_recording_data, headers={})
    assert response.status_code == 401
    assert "API Key missing" in response.json()["detail"]

    # Invalid API key
    response = client.post("/api/v1/vkyc-recordings/", json=sample_recording_data, headers={"X-API-Key": "wrong_key"})
    assert response.status_code == 401
    assert "Invalid API Key" in response.json()["detail"]

    # Valid API key (client fixture already sets it up, but testing explicitly)
    response = client.post("/api/v1/vkyc-recordings/", json=sample_recording_data, headers={"X-API-Key": "your_super_secret_api_key_here"})
    assert response.status_code == 200