### FILE: tests/test_api_endpoints.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from models import BulkRequest, LanIdStatus, BulkRequestStatus, LanIdProcessingStatus
import io

@pytest.mark.asyncio
async def test_upload_bulk_request_success(client: TestClient, admin_token: str):
    """Test successful bulk request upload."""
    file_content = "LAN001\nLAN002\nLAN003"
    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("lan_ids.txt", io.BytesIO(file_content.encode("utf-8")), "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 202
    data = response.json()
    assert data["filename"] == "lan_ids.txt"
    assert data["status"] == "PROCESSING"
    assert data["total_lan_ids"] == 3
    assert data["user_id"] == "admin"

    # Verify the request is in the DB
    db: Session = client.app.dependency_overrides.get(lambda: None)() # Access the overridden DB session
    bulk_req = db.query(BulkRequest).filter(BulkRequest.id == data["id"]).first()
    assert bulk_req is not None
    assert bulk_req.filename == "lan_ids.txt"
    assert len(bulk_req.lan_id_statuses) == 3


def test_upload_bulk_request_invalid_file_type(client: TestClient, admin_token: str):
    """Test bulk request upload with an unsupported file type."""
    file_content = "LAN001"
    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("image.jpg", io.BytesIO(file_content.encode("utf-8")), "image/jpeg")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_bulk_request_empty_file(client: TestClient, admin_token: str):
    """Test bulk request upload with an empty file."""
    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Uploaded file is empty." in response.json()["detail"]

def test_upload_bulk_request_no_lan_ids_in_file(client: TestClient, admin_token: str):
    """Test bulk request upload with a file containing no valid LAN IDs."""
    file_content = "\n\n  \n" # Only whitespace/empty lines
    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("empty_lines.txt", io.BytesIO(file_content.encode("utf-8")), "text/plain")},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "No valid LAN IDs found in the uploaded file." in response.json()["detail"]


def test_get_bulk_request_details_success(client: TestClient, sample_bulk_request: BulkRequest, admin_token: str):
    """Test retrieving details of a specific bulk request."""
    response = client.get(
        f"/api/v1/bulk-requests/{sample_bulk_request.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_bulk_request.id
    assert data["filename"] == sample_bulk_request.filename
    assert data["status"] == sample_bulk_request.status
    assert len(data["lan_id_statuses"]) == 3
    assert any(s["lan_id"] == "LAN123" and s["status"] == "SUCCESS" for s in data["lan_id_statuses"])
    assert any(s["lan_id"] == "LAN456" and s["status"] == "FAILED" for s in data["lan_id_statuses"])


def test_get_bulk_request_details_not_found(client: TestClient, admin_token: str):
    """Test retrieving details for a non-existent bulk request."""
    response = client.get(
        "/api/v1/bulk-requests/999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert "Bulk request with ID 999 not found." in response.json()["detail"]


def test_list_bulk_requests_success(client: TestClient, sample_bulk_request: BulkRequest, admin_token: str):
    """Test listing all bulk requests."""
    response = client.get(
        "/api/v1/bulk-requests/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1 # Could be more if other tests left data
    assert any(req["id"] == sample_bulk_request.id for req in data)


def test_list_bulk_requests_team_lead_filter(client: TestClient, test_db: Session, tl_token: str):
    """Test that a Team Lead only sees their own requests."""
    # Create a request for the TL user
    tl_bulk_req = BulkRequest(
        filename="tl_file.txt",
        user_id="tl_user",
        status=BulkRequestStatus.COMPLETED,
        total_lan_ids=1
    )
    test_db.add(tl_bulk_req)
    test_db.commit()
    test_db.refresh(tl_bulk_req)

    # Create a request for another user (e.g., admin)
    admin_bulk_req = BulkRequest(
        filename="admin_file.txt",
        user_id="admin",
        status=BulkRequestStatus.COMPLETED,
        total_lan_ids=1
    )
    test_db.add(admin_bulk_req)
    test_db.commit()
    test_db.refresh(admin_bulk_req)

    response = client.get(
        "/api/v1/bulk-requests/",
        headers={"Authorization": f"Bearer {tl_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == tl_bulk_req.id
    assert data[0]["user_id"] == "tl_user"


def test_authorization_failure(client: TestClient):
    """Test API access without authentication."""
    response = client.get("/api/v1/bulk-requests/")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("test.txt", io.BytesIO(b"LAN123"), "text/plain")}
    )
    assert response.status_code == 401

def test_forbidden_role(client: TestClient, tl_token: str):
    """Test API access with insufficient role (e.g., TL trying to access admin-only)."""
    # Assuming there's an endpoint that only 'admin' can access.
    # For this example, we'll test the upload endpoint with a user that doesn't have the required role.
    # The `require_role` dependency in `bulk_requests.py` is set to `["team_lead", "process_manager", "admin"]`.
    # So, a TL *can* upload. Let's modify the test to simulate a role that *cannot* upload.
    # For now, this test will pass if the TL can upload, which is intended.
    # To test forbidden, we'd need an endpoint with a stricter role requirement or a user with no roles.

    # Let's create a dummy user with no roles for this test
    from security import DUMMY_USERS_DB, get_password_hash
    DUMMY_USERS_DB["no_role_user"] = {
        "username": "no_role_user",
        "email": "no@example.com",
        "full_name": "No Role User",
        "hashed_password": get_password_hash("password"),
        "roles": []
    }
    no_role_token = create_access_token({"sub": "no_role_user", "roles": []})

    response = client.post(
        "/api/v1/bulk-requests/upload",
        files={"file": ("test.txt", io.BytesIO(b"LAN123"), "text/plain")},
        headers={"Authorization": f"Bearer {no_role_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]