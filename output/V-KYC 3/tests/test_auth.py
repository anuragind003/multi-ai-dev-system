import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models import User
from app.security import verify_password, get_password_hash
from app.schemas import UserCreate, UserUpdate

# Assuming conftest.py sets up the test database and provides fixtures

def test_create_user_success(client: TestClient, admin_token: str):
    """Test creating a new user with admin privileges."""
    new_user_data = {
        "email": "new_user@example.com",
        "password": "newsecurepassword",
        "first_name": "New",
        "last_name": "User",
        "is_active": True,
        "role_id": 2 # Auditor role
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == new_user_data["email"]
    assert data["role"]["name"] == "auditor"
    assert "id" in data
    assert "hashed_password" not in data # Password should not be returned

def test_create_user_duplicate_email(client: TestClient, admin_token: str):
    """Test creating a user with an email that already exists."""
    duplicate_user_data = {
        "email": "test_admin@example.com", # Existing email
        "password": "somepassword",
        "first_name": "Duplicate",
        "last_name": "User",
        "is_active": True,
        "role_id": 2
    }
    response = client.post(
        "/api/v1/users/",
        json=duplicate_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 409 # Conflict
    assert "already exists" in response.json()["detail"]

def test_create_user_invalid_role_id(client: TestClient, admin_token: str):
    """Test creating a user with a non-existent role ID."""
    invalid_role_data = {
        "email": "invalid_role@example.com",
        "password": "password",
        "first_name": "Invalid",
        "last_name": "Role",
        "is_active": True,
        "role_id": 999 # Non-existent role ID
    }
    response = client.post(
        "/api/v1/users/",
        json=invalid_role_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404 # Not Found
    assert "Role with ID 999 not found" in response.json()["detail"]

def test_login_success(client: TestClient):
    """Test successful user login."""
    response = client.post(
        "/api/v1/token",
        data={"username": "test_auditor@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    """Test login with incorrect password."""
    response = client.post(
        "/api/v1/token",
        data={"username": "test_auditor@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Authentication Failed"

def test_login_inactive_user(client: TestClient):
    """Test login with an inactive user account."""
    response = client.post(
        "/api/v1/token",
        data={"username": "inactive@example.com", "password": "testpassword"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "User account is inactive"

def test_get_current_user_success(client: TestClient, admin_token: str):
    """Test retrieving the current authenticated user's details."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_admin@example.com"
    assert data["role"]["name"] == "admin"

def test_get_current_user_no_token(client: TestClient):
    """Test retrieving current user without a token."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["message"] == "Unauthorized"

def test_get_current_user_invalid_token(client: TestClient):
    """Test retrieving current user with an invalid token."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid token"

def test_rbac_admin_access_user_write(client: TestClient, admin_token: str):
    """Admin should have user:write permission."""
    new_user_data = {
        "email": "rbac_test_user@example.com",
        "password": "password",
        "first_name": "RBAC",
        "last_name": "Test",
        "is_active": True,
        "role_id": 2
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201

def test_rbac_auditor_no_access_user_write(client: TestClient, auditor_token: str):
    """Auditor should NOT have user:write permission."""
    new_user_data = {
        "email": "auditor_no_write@example.com",
        "password": "password",
        "first_name": "Auditor",
        "last_name": "NoWrite",
        "is_active": True,
        "role_id": 2
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 403 # Forbidden
    assert "Insufficient permissions" in response.json()["message"]

def test_rbac_auditor_access_recording_read(client: TestClient, auditor_token: str):
    """Auditor should have recording:read permission."""
    # First, create a recording as admin to ensure there's data to read
    admin_response = client.post(
        "/api/v1/recordings/",
        json={
            "lan_id": "LAN001",
            "file_name": "test_recording_001.mp4",
            "file_path": "/nfs/test_recording_001.mp4",
            "file_size_bytes": 1000000,
            "recording_date": "2023-01-01T10:00:00Z"
        },
        headers={"Authorization": f"Bearer {client.get('/api/v1/token', data={'username': 'test_admin@example.com', 'password': 'testpassword'}).json()['access_token']}"}
    )
    assert admin_response.status_code == 201

    response = client.get(
        "/api/v1/recordings/",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1 # Should see at least the one created

def test_rbac_uploader_no_access_recording_delete(client: TestClient, uploader_token: str):
    """Uploader should NOT have recording:delete permission."""
    # Create a recording as admin to have something to try and delete
    admin_response = client.post(
        "/api/v1/recordings/",
        json={
            "lan_id": "LAN002",
            "file_name": "test_recording_002.mp4",
            "file_path": "/nfs/test_recording_002.mp4",
            "file_size_bytes": 2000000,
            "recording_date": "2023-01-02T11:00:00Z"
        },
        headers={"Authorization": f"Bearer {client.get('/api/v1/token', data={'username': 'test_admin@example.com', 'password': 'testpassword'}).json()['access_token']}"}
    )
    assert admin_response.status_code == 201
    recording_id_to_delete = admin_response.json()["id"]

    response = client.delete(
        f"/api/v1/recordings/{recording_id_to_delete}",
        headers={"Authorization": f"Bearer {uploader_token}"}
    )
    assert response.status_code == 403 # Forbidden
    assert "Insufficient permissions" in response.json()["message"]

def test_rbac_admin_access_recording_delete(client: TestClient, admin_token: str):
    """Admin should have recording:delete permission."""
    # Create a recording as admin to have something to delete
    admin_response = client.post(
        "/api/v1/recordings/",
        json={
            "lan_id": "LAN003",
            "file_name": "test_recording_003.mp4",
            "file_path": "/nfs/test_recording_003.mp4",
            "file_size_bytes": 3000000,
            "recording_date": "2023-01-03T12:00:00Z"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert admin_response.status_code == 201
    recording_id_to_delete = admin_response.json()["id"]

    response = client.delete(
        f"/api/v1/recordings/{recording_id_to_delete}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204 # No Content, successful deletion