import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from datetime import datetime, timedelta, timezone

from main import app
from app.core.database import Base, get_db
from app.models.recording import Recording
from app.models.user import User
from app.core.security import create_access_token, get_password_hash
from app.core.config import settings

# --- Setup for Test Database ---
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db" # Use SQLite for testing

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Important for SQLite in-memory/file testing
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Provides a clean database session for each test.
    Creates tables before tests, drops them after.
    """
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Provides a FastAPI test client with mocked database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear() # Clear overrides after tests

@pytest.fixture
def admin_user(db_session):
    """Fixture to create and return an admin user."""
    hashed_password = get_password_hash("testadminpass")
    user = User(username="testadmin", hashed_password=hashed_password, role="admin")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def team_lead_user(db_session):
    """Fixture to create and return a team_lead user."""
    hashed_password = get_password_hash("testtlpass")
    user = User(username="testteamlead", hashed_password=hashed_password, role="team_lead")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def regular_user(db_session):
    """Fixture to create and return a regular user."""
    hashed_password = get_password_hash("testuserpass")
    user = User(username="testuser", hashed_password=hashed_password, role="user")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_token(admin_user):
    """Fixture to generate an access token for the admin user."""
    return create_access_token(data={"sub": admin_user.username})

@pytest.fixture
def team_lead_token(team_lead_user):
    """Fixture to generate an access token for the team_lead user."""
    return create_access_token(data={"sub": team_lead_user.username})

@pytest.fixture
def regular_user_token(regular_user):
    """Fixture to generate an access token for the regular user."""
    return create_access_token(data={"sub": regular_user.username})

@pytest.fixture
def sample_recordings(db_session):
    """Fixture to populate the database with sample recording data."""
    recordings_data = [
        Recording(
            lan_id="LAN001",
            file_path="/nfs/rec/LAN001.mp4",
            recording_date=datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            status="completed"
        ),
        Recording(
            lan_id="LAN002",
            file_path="/nfs/rec/LAN002.mp4",
            recording_date=datetime(2023, 1, 5, 11, 30, 0, tzinfo=timezone.utc),
            status="failed"
        ),
        Recording(
            lan_id="LAN003",
            file_path="/nfs/rec/LAN003.mp4",
            recording_date=datetime(2023, 2, 10, 14, 0, 0, tzinfo=timezone.utc),
            status="completed"
        ),
        Recording(
            lan_id="LAN004",
            file_path="/nfs/rec/LAN004.mp4",
            recording_date=datetime(2023, 2, 15, 9, 0, 0, tzinfo=timezone.utc),
            status="completed"
        ),
        Recording(
            lan_id="LAN005",
            file_path="/nfs/rec/LAN005.mp4",
            recording_date=datetime(2023, 3, 1, 16, 0, 0, tzinfo=timezone.utc),
            status="processing"
        ),
        Recording(
            lan_id="LAN006",
            file_path="/nfs/rec/LAN006.mp4",
            recording_date=datetime(2023, 3, 10, 12, 0, 0, tzinfo=timezone.utc),
            status="completed"
        ),
    ]
    db_session.add_all(recordings_data)
    db_session.commit()
    for rec in recordings_data:
        db_session.refresh(rec)
    return recordings_data

# --- Tests for RecordingService ---

def test_create_recording(db_session):
    from app.services.recording_service import RecordingService
    service = RecordingService(db_session)
    recording_data = {
        "lan_id": "LAN007",
        "file_path": "/nfs/rec/LAN007.mp4",
        "recording_date": datetime.now(timezone.utc),
        "status": "completed"
    }
    recording = service.create_recording(recording_data)
    assert recording.id is not None
    assert recording.lan_id == "LAN007"
    assert db_session.query(Recording).count() == 1

def test_create_recording_duplicate_lan_id(db_session):
    from app.services.recording_service import RecordingService
    from app.core.exceptions import BadRequestException
    service = RecordingService(db_session)
    recording_data = {
        "lan_id": "LAN008",
        "file_path": "/nfs/rec/LAN008.mp4",
        "recording_date": datetime.now(timezone.utc),
        "status": "completed"
    }
    service.create_recording(recording_data)
    with pytest.raises(BadRequestException, match="Recording with LAN ID 'LAN008' already exists."):
        service.create_recording(recording_data)

def test_get_all_recordings_pagination(db_session, sample_recordings):
    from app.services.recording_service import RecordingService
    from app.schemas.recordings import RecordingFilterParams
    service = RecordingService(db_session)

    total, records = service.get_all_recordings(page=1, size=2, filters=RecordingFilterParams())
    assert total == 6
    assert len(records) == 2
    assert records[0].lan_id == "LAN001"
    assert records[1].lan_id == "LAN002"

    total, records = service.get_all_recordings(page=2, size=2, filters=RecordingFilterParams())
    assert total == 6
    assert len(records) == 2
    assert records[0].lan_id == "LAN003"
    assert records[1].lan_id == "LAN004"

    total, records = service.get_all_recordings(page=3, size=2, filters=RecordingFilterParams())
    assert total == 6
    assert len(records) == 2
    assert records[0].lan_id == "LAN005"
    assert records[1].lan_id == "LAN006"

    total, records = service.get_all_recordings(page=4, size=2, filters=RecordingFilterParams())
    assert total == 6
    assert len(records) == 0 # No more records

def test_get_all_recordings_filter_lan_id(db_session, sample_recordings):
    from app.services.recording_service import RecordingService
    from app.schemas.recordings import RecordingFilterParams
    service = RecordingService(db_session)

    filters = RecordingFilterParams(lan_id="001")
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 1
    assert records[0].lan_id == "LAN001"

    filters = RecordingFilterParams(lan_id="LAN")
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 6
    assert len(records) == 6

def test_get_all_recordings_filter_status(db_session, sample_recordings):
    from app.services.recording_service import RecordingService
    from app.schemas.recordings import RecordingFilterParams
    service = RecordingService(db_session)

    filters = RecordingFilterParams(status="completed")
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 4
    assert all(r.status == "completed" for r in records)

    filters = RecordingFilterParams(status="failed")
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 1
    assert records[0].lan_id == "LAN002"

def test_get_all_recordings_filter_date_range(db_session, sample_recordings):
    from app.services.recording_service import RecordingService
    from app.schemas.recordings import RecordingFilterParams
    service = RecordingService(db_session)

    # Recordings from 2023-02-01 onwards
    filters = RecordingFilterParams(start_date=datetime(2023, 2, 1, tzinfo=timezone.utc))
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 4 # LAN003, LAN004, LAN005, LAN006
    assert all(r.recording_date >= datetime(2023, 2, 1, tzinfo=timezone.utc) for r in records)

    # Recordings up to 2023-01-31
    filters = RecordingFilterParams(end_date=datetime(2023, 1, 31, tzinfo=timezone.utc))
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 2 # LAN001, LAN002
    assert all(r.recording_date < datetime(2023, 2, 1, tzinfo=timezone.utc) for r in records)

    # Recordings in February 2023
    filters = RecordingFilterParams(
        start_date=datetime(2023, 2, 1, tzinfo=timezone.utc),
        end_date=datetime(2023, 2, 28, tzinfo=timezone.utc)
    )
    total, records = service.get_all_recordings(page=1, size=10, filters=filters)
    assert total == 2 # LAN003, LAN004
    assert all(datetime(2023, 2, 1, tzinfo=timezone.utc) <= r.recording_date < datetime(2023, 3, 1, tzinfo=timezone.utc) for r in records)


# --- Tests for API Endpoints ---

def test_list_recordings_unauthorized(client):
    response = client.get(f"{settings.API_V1_STR}/recordings")
    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"

def test_list_recordings_forbidden(client, regular_user_token):
    headers = {"Authorization": f"Bearer {regular_user_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings", headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"

def test_list_recordings_success_admin(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6
    assert len(data["items"]) == settings.DEFAULT_PAGE_SIZE # Default size is 10, so all 6 items
    assert data["page"] == 1
    assert data["size"] == settings.DEFAULT_PAGE_SIZE
    assert data["total_pages"] == 1
    assert data["items"][0]["lan_id"] == "LAN001"

def test_list_recordings_success_team_lead(client, team_lead_token, sample_recordings):
    headers = {"Authorization": f"Bearer {team_lead_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6
    assert len(data["items"]) == settings.DEFAULT_PAGE_SIZE
    assert data["items"][0]["lan_id"] == "LAN001"

def test_list_recordings_pagination_api(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings?page=2&size=2", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 6
    assert len(data["items"]) == 2
    assert data["page"] == 2
    assert data["size"] == 2
    assert data["total_pages"] == 3
    assert data["items"][0]["lan_id"] == "LAN003"
    assert data["items"][1]["lan_id"] == "LAN004"

def test_list_recordings_filter_lan_id_api(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings?lan_id=002", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["lan_id"] == "LAN002"

def test_list_recordings_filter_status_api(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings?status=completed", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4
    assert all(item["status"] == "completed" for item in data["items"])

def test_list_recordings_filter_date_range_api(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Filter for February 2023
    response = client.get(f"{settings.API_V1_STR}/recordings?start_date=2023-02-01T00:00:00Z&end_date=2023-02-28T23:59:59Z", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["lan_id"] == "LAN003"
    assert data["items"][1]["lan_id"] == "LAN004"

def test_get_recording_by_id_success(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Assuming LAN001 has ID 1
    response = client.get(f"{settings.API_V1_STR}/recordings/1", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["lan_id"] == "LAN001"
    assert data["id"] == 1

def test_get_recording_by_id_not_found(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.get(f"{settings.API_V1_STR}/recordings/999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Recording with ID 999 not found."

def test_create_recording_api_success(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    new_recording_data = {
        "lan_id": "NEW001",
        "file_path": "/nfs/new/NEW001.mp4",
        "recording_date": "2024-05-20T10:00:00Z",
        "status": "completed",
        "notes": "Test creation"
    }
    response = client.post(f"{settings.API_V1_STR}/recordings", json=new_recording_data, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["lan_id"] == "NEW001"
    assert data["id"] is not None

def test_create_recording_api_duplicate_lan_id(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    new_recording_data = {
        "lan_id": "DUP001",
        "file_path": "/nfs/dup/DUP001.mp4",
        "recording_date": "2024-05-20T10:00:00Z",
        "status": "completed"
    }
    client.post(f"{settings.API_V1_STR}/recordings", json=new_recording_data, headers=headers) # First creation
    response = client.post(f"{settings.API_V1_STR}/recordings", json=new_recording_data, headers=headers) # Second creation
    assert response.status_code == 400
    assert response.json()["detail"] == "Recording with LAN ID 'DUP001' already exists."

def test_create_recording_api_forbidden(client, team_lead_token):
    headers = {"Authorization": f"Bearer {team_lead_token}"}
    new_recording_data = {
        "lan_id": "FORBIDDEN001",
        "file_path": "/nfs/forbidden/FORBIDDEN001.mp4",
        "recording_date": "2024-05-20T10:00:00Z",
        "status": "completed"
    }
    response = client.post(f"{settings.API_V1_STR}/recordings", json=new_recording_data, headers=headers)
    assert response.status_code == 403
    assert response.json()["detail"] == "Not enough permissions"

def test_update_recording_api_success(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Assuming LAN001 has ID 1
    update_data = {
        "lan_id": "LAN001", # LAN ID must be provided, even if not changing
        "file_path": "/nfs/rec/LAN001_updated.mp4",
        "recording_date": "2023-01-01T10:00:00Z",
        "status": "archived",
        "notes": "Updated test"
    }
    response = client.put(f"{settings.API_V1_STR}/recordings/1", json=update_data, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["file_path"] == "/nfs/rec/LAN001_updated.mp4"
    assert data["status"] == "archived"
    assert data["notes"] == "Updated test"

def test_update_recording_api_not_found(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    update_data = {
        "lan_id": "NONEXISTENT",
        "file_path": "/nfs/nonexistent.mp4",
        "recording_date": "2024-01-01T00:00:00Z",
        "status": "completed"
    }
    response = client.put(f"{settings.API_V1_STR}/recordings/999", json=update_data, headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Recording with ID 999 not found."

def test_delete_recording_api_success(client, admin_token, sample_recordings):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Assuming LAN001 has ID 1
    response = client.delete(f"{settings.API_V1_STR}/recordings/1", headers=headers)
    assert response.status_code == 204
    # Verify it's deleted
    response = client.get(f"{settings.API_V1_STR}/recordings/1", headers=headers)
    assert response.status_code == 404

def test_delete_recording_api_not_found(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.delete(f"{settings.API_V1_STR}/recordings/999", headers=headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Recording with ID 999 not found."

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["database"] == "ok"
    assert "version" in response.json()

def test_rate_limit_status_endpoint(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    # Assuming default rate limit is 50/minute, this test might be slow or need adjustment
    # For testing, we can temporarily set a very low rate limit in config or mock FastAPILimiter
    # For now, just test one successful call
    response = client.get(f"{settings.API_V1_STR}/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "Application is running smoothly!"

    # To properly test rate limiting, you'd need to make multiple requests rapidly
    # and verify the 429 status code. This often requires mocking the limiter's backend.
    # For example:
    # for _ in range(51): # Assuming 50/minute limit
    #     response = client.get(f"{settings.API_V1_STR}/status", headers=headers)
    # assert response.status_code == 429 # Too Many Requests