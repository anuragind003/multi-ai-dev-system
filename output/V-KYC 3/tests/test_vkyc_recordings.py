import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from main import app
from database import Base, get_db
from models import VKYCRecording, User, UserRole
from auth import get_password_hash, create_access_token
from datetime import datetime, timedelta, timezone
from config import get_settings

settings = get_settings()

# Setup a test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db" # Use SQLite for testing
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Use StaticPool for SQLite to prevent issues with multiple connections
    echo=False # Don't log SQL queries during tests
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Provides a clean database session for each test.
    Creates tables before each test and drops them after.
    """
    Base.metadata.create_all(bind=engine) # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables to ensure clean state

@pytest.fixture(name="client")
def client_fixture(db_session: TestingSessionLocal):
    """
    Provides a TestClient for FastAPI, overriding the database dependency
    to use the test database.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear() # Clear overrides after test

@pytest.fixture(name="test_user")
def test_user_fixture(db_session: TestingSessionLocal):
    """Creates a test user (auditor) for authentication."""
    hashed_password = get_password_hash("testpassword")
    user = User(
        username="testauditor",
        email="test@example.com",
        hashed_password=hashed_password,
        full_name="Test Auditor",
        role=UserRole.AUDITOR,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(name="test_admin_user")
def test_admin_user_fixture(db_session: TestingSessionLocal):
    """Creates a test admin user for authentication."""
    hashed_password = get_password_hash("adminpassword")
    user = User(
        username="testadmin",
        email="admin@example.com",
        hashed_password=hashed_password,
        full_name="Test Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(name="test_viewer_user")
def test_viewer_user_fixture(db_session: TestingSessionLocal):
    """Creates a test viewer user for authentication."""
    hashed_password = get_password_hash("viewerpassword")
    user = User(
        username="testviewer",
        email="viewer@example.com",
        hashed_password=hashed_password,
        full_name="Test Viewer",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(name="auditor_auth_headers")
def auditor_auth_headers_fixture(test_user: User):
    """Generates auth headers for the test auditor user."""
    token = create_access_token(
        data={"sub": test_user.username, "scopes": [test_user.role.value]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(name="admin_auth_headers")
def admin_auth_headers_fixture(test_admin_user: User):
    """Generates auth headers for the test admin user."""
    token = create_access_token(
        data={"sub": test_admin_user.username, "scopes": [test_admin_user.role.value]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(name="viewer_auth_headers")
def viewer_auth_headers_fixture(test_viewer_user: User):
    """Generates auth headers for the test viewer user."""
    token = create_access_token(
        data={"sub": test_viewer_user.username, "scopes": [test_viewer_user.role.value]},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"Authorization": f"Bearer {token}"}

# --- Health Check Tests ---
def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database_status"] == "connected"
    assert "timestamp" in response.json()
    assert "version" in response.json()

# --- Authentication Tests ---
def test_create_user_success(client: TestClient, admin_auth_headers: dict):
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword",
        "full_name": "New User",
        "role": "viewer"
    }
    response = client.post("/api/v1/users", json=user_data, headers=admin_auth_headers)
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["role"] == "viewer"
    assert "id" in response.json()

def test_create_user_duplicate_username(client: TestClient, test_user: User, admin_auth_headers: dict):
    user_data = {
        "username": test_user.username, # Duplicate
        "email": "another@example.com",
        "password": "securepassword",
        "full_name": "Another User",
        "role": "viewer"
    }
    response = client.post("/api/v1/users", json=user_data, headers=admin_auth_headers)
    assert response.status_code == 409
    assert "already exists" in response.json()["message"]

def test_create_user_unauthorized(client: TestClient):
    user_data = {
        "username": "unauthuser",
        "email": "unauth@example.com",
        "password": "securepassword",
        "full_name": "Unauthorized User",
        "role": "viewer"
    }
    response = client.post("/api/v1/users", json=user_data) # No headers
    assert response.status_code == 401

def test_create_user_forbidden(client: TestClient, viewer_auth_headers: dict):
    user_data = {
        "username": "forbiddenuser",
        "email": "forbidden@example.com",
        "password": "securepassword",
        "full_name": "Forbidden User",
        "role": "viewer"
    }
    response = client.post("/api/v1/users", json=user_data, headers=viewer_auth_headers) # Viewer role
    assert response.status_code == 403

def test_login_success(client: TestClient, test_user: User):
    response = client.post(
        "/api/v1/token",
        json={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/api/v1/token",
        json={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_get_current_user(client: TestClient, auditor_auth_headers: dict, test_user: User):
    response = client.get("/api/v1/users/me", headers=auditor_auth_headers)
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username
    assert response.json()["email"] == test_user.email

# --- VKYC Recording CRUD Tests ---
def test_create_vkyc_recording_success(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN001",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN001.mp4",
        "recording_date": "2023-01-15T10:00:00Z",
        "uploaded_by": "testauditor"
    }
    response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    assert response.status_code == 201
    assert response.json()["lan_id"] == "LAN001"
    assert response.json()["status"] == "PENDING"
    assert "id" in response.json()

def test_create_vkyc_recording_duplicate_lan_id(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN002",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN002.mp4",
        "recording_date": "2023-01-15T10:00:00Z",
        "uploaded_by": "testauditor"
    }
    client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers) # Duplicate
    assert response.status_code == 409
    assert "already exists" in response.json()["message"]

def test_create_vkyc_recording_invalid_path(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN003",
        "recording_path": "/local/path/LAN003.mp4", # Invalid path
        "recording_date": "2023-01-15T10:00:00Z",
        "uploaded_by": "testauditor"
    }
    response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    assert response.status_code == 400
    assert "must be within the designated NFS mount" in response.json()["message"]

def test_get_vkyc_recording_by_id_success(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN004",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN004.mp4",
        "recording_date": "2023-01-16T11:00:00Z",
        "uploaded_by": "testauditor"
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    recording_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/vkyc-recordings/{recording_id}", headers=auditor_auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["lan_id"] == "LAN004"

def test_get_vkyc_recording_by_id_not_found(client: TestClient, auditor_auth_headers: dict):
    response = client.get("/api/v1/vkyc-recordings/99999", headers=auditor_auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["message"]

def test_list_vkyc_recordings(client: TestClient, auditor_auth_headers: dict):
    # Create a few recordings
    client.post("/api/v1/vkyc-recordings", json={"lan_id": "LAN005", "recording_path": "/mnt/vkyc_recordings/2023/LAN005.mp4", "recording_date": "2023-01-17T12:00:00Z", "uploaded_by": "testauditor"}, headers=auditor_auth_headers)
    client.post("/api/v1/vkyc-recordings", json={"lan_id": "LAN006", "recording_path": "/mnt/vkyc_recordings/2023/LAN006.mp4", "recording_date": "2023-01-17T13:00:00Z", "uploaded_by": "testauditor"}, headers=auditor_auth_headers)

    response = client.get("/api/v1/vkyc-recordings", headers=auditor_auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 2 # May include recordings from other tests
    assert len(response.json()["items"]) >= 2

def test_list_vkyc_recordings_with_filter(client: TestClient, auditor_auth_headers: dict):
    client.post("/api/v1/vkyc-recordings", json={"lan_id": "FILTERTEST1", "recording_path": "/mnt/vkyc_recordings/2023/FILTERTEST1.mp4", "recording_date": "2023-01-18T14:00:00Z", "uploaded_by": "testauditor"}, headers=auditor_auth_headers)
    client.post("/api/v1/vkyc-recordings", json={"lan_id": "FILTERTEST2", "recording_path": "/mnt/vkyc_recordings/2023/FILTERTEST2.mp4", "recording_date": "2023-01-18T15:00:00Z", "uploaded_by": "testauditor"}, headers=auditor_auth_headers)

    response = client.get("/api/v1/vkyc-recordings?lan_id=FILTERTEST1", headers=auditor_auth_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["lan_id"] == "FILTERTEST1"

def test_update_vkyc_recording_success(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN007",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN007.mp4",
        "recording_date": "2023-01-19T16:00:00Z",
        "uploaded_by": "testauditor"
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    recording_id = create_response.json()["id"]

    update_data = {"status": "COMPLETED", "review_notes": "All good."}
    update_response = client.put(f"/api/v1/vkyc-recordings/{recording_id}", json=update_data, headers=auditor_auth_headers)
    assert update_response.status_code == 200
    assert update_response.json()["id"] == recording_id
    assert update_response.json()["status"] == "COMPLETED"
    assert update_response.json()["review_notes"] == "All good."

def test_update_vkyc_recording_not_found(client: TestClient, auditor_auth_headers: dict):
    update_data = {"status": "COMPLETED"}
    response = client.put("/api/v1/vkyc-recordings/99999", json=update_data, headers=auditor_auth_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["message"]

def test_update_vkyc_recording_change_lan_id_on_completed(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN008",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN008.mp4",
        "recording_date": "2023-01-20T17:00:00Z",
        "uploaded_by": "testauditor",
        "status": "COMPLETED" # Set as completed initially
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    recording_id = create_response.json()["id"]

    update_data = {"lan_id": "NEWLAN008"}
    response = client.put(f"/api/v1/vkyc-recordings/{recording_id}", json=update_data, headers=auditor_auth_headers)
    assert response.status_code == 400
    assert "LAN ID cannot be changed for completed recordings" in response.json()["message"]

def test_delete_vkyc_recording_success(client: TestClient, admin_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN009",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN009.mp4",
        "recording_date": "2023-01-21T18:00:00Z",
        "uploaded_by": "testadmin",
        "status": "COMPLETED" # Must be completed to delete
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=admin_auth_headers)
    recording_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/vkyc-recordings/{recording_id}", headers=admin_auth_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/vkyc-recordings/{recording_id}", headers=admin_auth_headers)
    assert get_response.status_code == 404 # Should be gone

def test_delete_vkyc_recording_pending_status(client: TestClient, admin_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN010",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN010.mp4",
        "recording_date": "2023-01-22T19:00:00Z",
        "uploaded_by": "testadmin",
        "status": "PENDING" # Cannot delete if pending
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=admin_auth_headers)
    recording_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/vkyc-recordings/{recording_id}", headers=admin_auth_headers)
    assert delete_response.status_code == 400
    assert "Pending recordings cannot be deleted directly" in delete_response.json()["message"]

def test_delete_vkyc_recording_forbidden_role(client: TestClient, auditor_auth_headers: dict):
    recording_data = {
        "lan_id": "LAN011",
        "recording_path": "/mnt/vkyc_recordings/2023/LAN011.mp4",
        "recording_date": "2023-01-23T20:00:00Z",
        "uploaded_by": "testauditor",
        "status": "COMPLETED"
    }
    create_response = client.post("/api/v1/vkyc-recordings", json=recording_data, headers=auditor_auth_headers)
    recording_id = create_response.json()["id"]

    delete_response = client.delete(f"/api/v1/vkyc-recordings/{recording_id}", headers=auditor_auth_headers) # Auditor cannot delete
    assert delete_response.status_code == 403
    assert "Not enough permissions" in delete_response.json()["message"]

# --- Role-based Access Control Tests ---
@pytest.mark.parametrize("endpoint, method, data, allowed_roles, forbidden_roles", [
    ("/api/v1/vkyc-recordings", "post", {"lan_id": "LAN_RBAC_1", "recording_path": "/mnt/vkyc_recordings/2023/LAN_RBAC_1.mp4", "recording_date": "2023-01-01T00:00:00Z", "uploaded_by": "test"}, ["admin", "auditor"], ["viewer"]),
    ("/api/v1/vkyc-recordings/1", "get", None, ["admin", "auditor", "viewer"], []), # ID 1 might not exist, but testing access
    ("/api/v1/vkyc-recordings/1", "put", {"status": "COMPLETED"}, ["admin", "auditor"], ["viewer"]),
    ("/api/v1/vkyc-recordings/1", "delete", None, ["admin"], ["auditor", "viewer"]),
    ("/api/v1/users", "post", {"username": "new_rbac_user", "email": "rbac@example.com", "password": "pass", "role": "viewer"}, ["admin"], ["auditor", "viewer"]),
    ("/api/v1/users/1", "get", None, ["admin", "auditor"], ["viewer"]),
])
def test_role_based_access_control(client: TestClient, admin_auth_headers: dict, auditor_auth_headers: dict, viewer_auth_headers: dict,
                                   endpoint, method, data, allowed_roles, forbidden_roles):
    # Create a dummy recording if needed for GET/PUT/DELETE
    if "vkyc-recordings/1" in endpoint:
        create_data = {
            "lan_id": "LAN_DUMMY",
            "recording_path": "/mnt/vkyc_recordings/2023/LAN_DUMMY.mp4",
            "recording_date": "2023-01-01T00:00:00Z",
            "uploaded_by": "test",
            "status": "PENDING" if method != "delete" else "COMPLETED" # Set to completed for deletion test
        }
        create_resp = client.post("/api/v1/vkyc-recordings", json=create_data, headers=admin_auth_headers)
        if create_resp.status_code == 201:
            endpoint = endpoint.replace("/1", f"/{create_resp.json()['id']}")
        else:
            # If creation fails (e.g., duplicate LAN_DUMMY from previous test), try to get existing
            existing_rec = client.get("/api/v1/vkyc-recordings?lan_id=LAN_DUMMY", headers=admin_auth_headers).json()["items"]
            if existing_rec:
                endpoint = endpoint.replace("/1", f"/{existing_rec[0]['id']}")
                if method == "delete" and existing_rec[0]["status"] != "COMPLETED":
                    client.put(endpoint, json={"status": "COMPLETED"}, headers=admin_auth_headers)
            else:
                pytest.skip(f"Could not prepare test data for {endpoint}")

    # Test allowed roles
    for role in allowed_roles:
        headers = None
        if role == "admin": headers = admin_auth_headers
        elif role == "auditor": headers = auditor_auth_headers
        elif role == "viewer": headers = viewer_auth_headers

        if method == "post":
            response = client.post(endpoint, json=data, headers=headers)
        elif method == "get":
            response = client.get(endpoint, headers=headers)
        elif method == "put":
            response = client.put(endpoint, json=data, headers=headers)
        elif method == "delete":
            response = client.delete(endpoint, headers=headers)
        
        # Expect success (2xx) or specific business logic errors (e.g., 409 for duplicate, 400 for invalid state)
        # For simplicity, we check for 2xx or 409/400 which means access was granted but business rule failed
        assert response.status_code in [200, 201, 204, 400, 409], f"Allowed role {role} failed for {method} {endpoint} with status {response.status_code}: {response.json()}"

    # Test forbidden roles
    for role in forbidden_roles:
        headers = None
        if role == "admin": headers = admin_auth_headers
        elif role == "auditor": headers = auditor_auth_headers
        elif role == "viewer": headers = viewer_auth_headers

        if method == "post":
            response = client.post(endpoint, json=data, headers=headers)
        elif method == "get":
            response = client.get(endpoint, headers=headers)
        elif method == "put":
            response = client.put(endpoint, json=data, headers=headers)
        elif method == "delete":
            response = client.delete(endpoint, headers=headers)
        
        assert response.status_code == 403, f"Forbidden role {role} unexpectedly succeeded for {method} {endpoint} with status {response.status_code}: {response.json()}"
        assert "Not enough permissions" in response.json()["message"]