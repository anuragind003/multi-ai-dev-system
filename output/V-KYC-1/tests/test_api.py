import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app
from database import get_db, Base
from models import User, UserRole, Recording, RecordingStatus
from auth import get_password_hash
from config import settings

# Use a SQLite in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db" # Use a file-based SQLite for easier debugging of test data
# For a truly in-memory DB that clears on each run: "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Important for SQLite in-memory to keep same connection
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Fixture that provides a clean database session for each test.
    It creates tables, yields a session, and then drops tables.
    """
    Base.metadata.create_all(bind=engine) # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables after test

@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Fixture that provides a TestClient for the FastAPI app.
    It overrides the get_db dependency to use the test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {} # Clear overrides after test

@pytest.fixture(name="test_user")
def test_user_fixture(db_session):
    """Fixture to create a regular test user."""
    user = User(
        username="testuser",
        hashed_password=get_password_hash("testpassword"),
        role=UserRole.USER,
        lan_id="LAN001"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture(name="test_admin_user")
def test_admin_user_fixture(db_session):
    """Fixture to create an admin test user."""
    admin_user = User(
        username="adminuser",
        hashed_password=get_password_hash("adminpassword"),
        role=UserRole.ADMIN,
        lan_id="LANADMIN"
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)
    return admin_user

@pytest.fixture(name="test_auditor_user")
def test_auditor_user_fixture(db_session):
    """Fixture to create an auditor test user."""
    auditor_user = User(
        username="auditoruser",
        hashed_password=get_password_hash("auditorpassword"),
        role=UserRole.AUDITOR,
        lan_id="LANAUDIT"
    )
    db_session.add(auditor_user)
    db_session.commit()
    db_session.refresh(auditor_user)
    return auditor_user

@pytest.fixture(name="user_token")
def user_token_fixture(client, test_user):
    """Fixture to get a JWT token for the regular test user."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(name="admin_token")
def admin_token_fixture(client, test_admin_user):
    """Fixture to get a JWT token for the admin test user."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": test_admin_user.username, "password": "adminpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(name="auditor_token")
def auditor_token_fixture(client, test_auditor_user):
    """Fixture to get a JWT token for the auditor test user."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": test_auditor_user.username, "password": "auditorpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# --- User Endpoint Tests ---
def test_create_user_as_admin(client, admin_token):
    """Test creating a new user as an admin."""
    new_user_data = {
        "username": "newuser",
        "password": "newpassword123",
        "role": "user",
        "lan_id": "LAN002"
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["role"] == "user"

def test_create_user_duplicate_username(client, admin_token, test_user):
    """Test creating a user with a duplicate username."""
    new_user_data = {
        "username": test_user.username, # Duplicate
        "password": "newpassword123",
        "role": "user",
        "lan_id": "LAN003"
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

def test_create_user_unauthorized(client, user_token):
    """Test creating a user without admin privileges."""
    new_user_data = {
        "username": "unauthuser",
        "password": "password",
        "role": "user",
        "lan_id": "LAN004"
    }
    response = client.post(
        "/api/v1/users/",
        json=new_user_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

def test_login_success(client, test_user):
    """Test successful user login."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": test_user.username, "password": "testpassword"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_read_users_me(client, user_token, test_user):
    """Test getting current user details."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == test_user.username
    assert response.json()["id"] == test_user.id

def test_list_users_as_admin(client, admin_token, test_user, test_admin_user):
    """Test listing all users as an admin."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2 # At least test_user and test_admin_user
    assert any(u["username"] == test_user.username for u in users)
    assert any(u["username"] == test_admin_user.username for u in users)

def test_list_users_unauthorized(client, user_token):
    """Test listing users without admin privileges."""
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

# --- Recording Endpoint Tests ---
def test_upload_recording_file(client, user_token, test_user, mocker):
    """Test uploading a recording file."""
    # Mock os.makedirs and open to prevent actual file system interaction during test
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True) # For subsequent checks

    test_file_content = b"This is a dummy video recording content."
    test_file_name = "test_recording.mp4"
    test_lan_id = "LAN005"

    response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": (test_file_name, test_file_content, "video/mp4")},
        data={"lan_id": test_lan_id}
    )
    assert response.status_code == 201
    assert response.json()["lan_id"] == test_lan_id
    assert response.json()["status"] == "pending"
    assert response.json()["uploader_id"] == test_user.id
    assert test_file_name in response.json()["file_path"] # Check if filename is part of path

    # Verify file was "written"
    mock_open.return_value.write.assert_called_once_with(test_file_content)

def test_get_recording_by_id(client, user_token, test_user, mocker):
    """Test getting recording metadata by ID."""
    # First, upload a recording to ensure it exists
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True)

    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("temp.mp4", b"content", "video/mp4")},
        data={"lan_id": "LAN006"}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]

    # Now, retrieve it
    get_response = client.get(
        f"/api/v1/recordings/{recording_id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert get_response.status_code == 200
    assert get_response.json()["id"] == recording_id
    assert get_response.json()["lan_id"] == "LAN006"

def test_list_recordings_with_filter(client, user_token, test_user, mocker):
    """Test listing recordings with filters."""
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True)

    # Upload a few recordings
    client.post("/api/v1/recordings/upload", headers={"Authorization": f"Bearer {user_token}"}, files={"file": ("rec1.mp4", b"c1", "video/mp4")}, data={"lan_id": "LAN007"})
    client.post("/api/v1/recordings/upload", headers={"Authorization": f"Bearer {user_token}"}, files={"file": ("rec2.mp4", b"c2", "video/mp4")}, data={"lan_id": "LAN008"})
    client.post("/api/v1/recordings/upload", headers={"Authorization": f"Bearer {user_token}"}, files={"file": ("rec3.mp4", b"c3", "video/mp4")}, data={"lan_id": "LAN007"})

    # Filter by LAN ID
    response = client.get(
        "/api/v1/recordings/?lan_id=LAN007",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    recordings = response.json()
    assert len(recordings) == 2
    assert all(r["lan_id"] == "LAN007" for r in recordings)

def test_update_recording_status_as_auditor(client, auditor_token, test_user, mocker):
    """Test updating recording status as an auditor."""
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True)

    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {client.post('/api/v1/users/token', data={'username': test_user.username, 'password': 'testpassword'}).json()['access_token']}"},
        files={"file": ("update_test.mp4", b"content", "video/mp4")},
        data={"lan_id": "LAN009"}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]

    update_data = {"status": "approved", "notes": "Approved by auditor."}
    response = client.put(
        f"/api/v1/recordings/{recording_id}/status",
        json=update_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == recording_id
    assert response.json()["status"] == "approved"
    assert response.json()["notes"] == "Approved by auditor."

def test_update_recording_status_unauthorized(client, user_token, mocker):
    """Test updating recording status without auditor/admin privileges."""
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True)

    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("unauth_update.mp4", b"content", "video/mp4")},
        data={"lan_id": "LAN010"}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]

    update_data = {"status": "rejected"}
    response = client.put(
        f"/api/v1/recordings/{recording_id}/status",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

def test_download_recording_file(client, user_token, test_user, mocker):
    """Test downloading a recording file."""
    # Create a dummy file on the simulated NFS path
    test_file_content = b"This is the actual file content for download."
    test_file_name = "download_test.mp4"
    test_lan_id = "LAN011"
    
    # Ensure the directory exists for the test
    os.makedirs(settings.NFS_RECORDINGS_PATH, exist_ok=True)
    file_path_on_disk = os.path.join(settings.NFS_RECORDINGS_PATH, f"{test_lan_id}_some_timestamp_{test_file_name}")
    with open(file_path_on_disk, "wb") as f:
        f.write(test_file_content)

    # Mock os.makedirs and open for the upload part, but let download use real file
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', side_effect=lambda path: path == file_path_on_disk or os.path.exists(path))

    # Upload metadata pointing to the dummy file
    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": (test_file_name, test_file_content, "video/mp4")},
        data={"lan_id": test_lan_id}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]
    
    # Update the file_path in the DB to point to our pre-created file
    # This is a hack for testing, in real scenario, upload would create the file
    db_session = next(get_db())
    recording_in_db = db_session.query(Recording).filter(Recording.id == recording_id).first()
    recording_in_db.file_path = file_path_on_disk
    db_session.commit()
    db_session.close()

    # Now, download it
    response = client.get(
        f"/api/v1/recordings/{recording_id}/download",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["content-disposition"] == f'attachment; filename="{test_file_name}"'
    assert response.content == test_file_content

    # Clean up the dummy file
    os.remove(file_path_on_disk)

def test_delete_recording_as_admin(client, admin_token, test_user, mocker):
    """Test deleting a recording as an admin."""
    test_file_content = b"Content to be deleted."
    test_file_name = "delete_test.mp4"
    test_lan_id = "LAN012"
    
    # Create a dummy file on the simulated NFS path
    os.makedirs(settings.NFS_RECORDINGS_PATH, exist_ok=True)
    file_path_on_disk = os.path.join(settings.NFS_RECORDINGS_PATH, f"{test_lan_id}_some_timestamp_{test_file_name}")
    with open(file_path_on_disk, "wb") as f:
        f.write(test_file_content)

    # Mock os.makedirs and open for the upload part, but let delete use real file
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', side_effect=lambda path: path == file_path_on_disk or os.path.exists(path))
    mocker.patch('os.remove', side_effect=lambda path: os.remove(path) if path == file_path_on_disk else None) # Mock os.remove for the specific file

    # Upload metadata pointing to the dummy file
    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {client.post('/api/v1/users/token', data={'username': test_user.username, 'password': 'testpassword'}).json()['access_token']}"},
        files={"file": (test_file_name, test_file_content, "video/mp4")},
        data={"lan_id": test_lan_id}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]

    # Update the file_path in the DB to point to our pre-created file
    db_session = next(get_db())
    recording_in_db = db_session.query(Recording).filter(Recording.id == recording_id).first()
    recording_in_db.file_path = file_path_on_disk
    db_session.commit()
    db_session.close()

    # Now, delete it
    response = client.delete(
        f"/api/v1/recordings/{recording_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

    # Verify metadata is gone
    get_response = client.get(
        f"/api/v1/recordings/{recording_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert get_response.status_code == 404

    # Verify file is gone
    assert not os.path.exists(file_path_on_disk)

def test_delete_recording_unauthorized(client, user_token, mocker):
    """Test deleting a recording without admin privileges."""
    mocker.patch('os.makedirs')
    mock_open = mocker.mock_open()
    mocker.patch('builtins.open', mock_open)
    mocker.patch('os.path.exists', return_value=True)

    upload_response = client.post(
        "/api/v1/recordings/upload",
        headers={"Authorization": f"Bearer {user_token}"},
        files={"file": ("unauth_delete.mp4", b"content", "video/mp4")},
        data={"lan_id": "LAN013"}
    )
    assert upload_response.status_code == 201
    recording_id = upload_response.json()["id"]

    response = client.delete(
        f"/api/v1/recordings/{recording_id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

# --- Health Check Test ---
def test_health_check(client, mocker):
    """Test the health check endpoint."""
    # Mock Redis ping to ensure it doesn't fail if Redis isn't running
    mocker.patch('redis.asyncio.Redis.ping', return_value=True)
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "healthy"
    assert response.json()["redis"] == "healthy"
    assert "version" in response.json()
    assert "timestamp" in response.json()