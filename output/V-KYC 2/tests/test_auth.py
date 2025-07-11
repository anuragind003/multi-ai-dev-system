import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
from models import User, Role, UserRole
from security import get_password_hash
from config import settings

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for tests
@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Fixture that provides a clean database session for each test.
    """
    Base.metadata.create_all(bind=engine)  # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)  # Drop tables after test

@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Fixture that provides a TestClient with the overridden database dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear() # Clear overrides after test

@pytest.fixture
def setup_roles_and_users(db_session):
    """
    Fixture to set up roles and initial users for testing.
    """
    # Create roles
    team_lead_role = Role(name=UserRole.TEAM_LEAD)
    process_manager_role = Role(name=UserRole.PROCESS_MANAGER)
    db_session.add_all([team_lead_role, process_manager_role])
    db_session.commit()
    db_session.refresh(team_lead_role)
    db_session.refresh(process_manager_role)

    # Create users
    team_lead_user = User(
        username="teamlead1",
        hashed_password=get_password_hash("password123"),
        role_id=team_lead_role.id
    )
    process_manager_user = User(
        username="procman1",
        hashed_password=get_password_hash("password123"),
        role_id=process_manager_role.id
    )
    db_session.add_all([team_lead_user, process_manager_user])
    db_session.commit()
    db_session.refresh(team_lead_user)
    db_session.refresh(process_manager_user)

    return {
        "team_lead_user": team_lead_user,
        "process_manager_user": process_manager_user,
        "team_lead_role": team_lead_role,
        "process_manager_role": process_manager_role
    }

def get_auth_token(client: TestClient, username, password):
    """Helper function to get an authentication token."""
    response = client.post(
        "/api/v1/users/token",
        data={"username": username, "password": password}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

# --- Tests ---

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database_status"] == "ok"

def test_register_user(client: TestClient):
    response = client.post(
        "/api/v1/users/register",
        json={"username": "newuser", "password": "securepassword", "role": "Team Lead"}
    )
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["role"] == "Team Lead"

def test_register_existing_user(client: TestClient):
    client.post(
        "/api/v1/users/register",
        json={"username": "existinguser", "password": "securepassword", "role": "Team Lead"}
    )
    response = client.post(
        "/api/v1/users/register",
        json={"username": "existinguser", "password": "anotherpassword", "role": "Process Manager"}
    )
    assert response.status_code == 409
    assert "Username already registered" in response.json()["detail"]

def test_login_success(client: TestClient, setup_roles_and_users):
    response = client.post(
        "/api/v1/users/token",
        data={"username": "teamlead1", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/api/v1/users/token",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

def test_read_users_me_authenticated(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "teamlead1", "password123")
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["username"] == "teamlead1"
    assert response.json()["role"] == "Team Lead"

def test_read_users_me_unauthenticated(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

# --- RBAC Tests ---

def test_team_lead_access_team_lead_dashboard(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "teamlead1", "password123")
    response = client.get(
        "/api/v1/data/team_lead_dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "Welcome, Team Lead teamlead1!" in response.json()["message"]

def test_process_manager_access_team_lead_dashboard_forbidden(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "procman1", "password123")
    response = client.get(
        "/api/v1/data/team_lead_dashboard",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

def test_process_manager_access_process_manager_reports(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "procman1", "password123")
    response = client.get(
        "/api/v1/data/process_manager_reports",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "Hello, Process Manager procman1!" in response.json()["message"]

def test_team_lead_access_process_manager_reports_forbidden(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "teamlead1", "password123")
    response = client.get(
        "/api/v1/data/process_manager_reports",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

def test_any_vkyc_role_access_vkyc_recordings_list_team_lead(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "teamlead1", "password123")
    response = client.get(
        "/api/v1/data/vkyc_recordings_list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "recordings" in response.json()

def test_any_vkyc_role_access_vkyc_recordings_list_process_manager(client: TestClient, setup_roles_and_users):
    token = get_auth_token(client, "procman1", "password123")
    response = client.get(
        "/api/v1/data/vkyc_recordings_list",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "recordings" in response.json()

def test_public_info_access(client: TestClient):
    response = client.get("/api/v1/data/public_info")
    assert response.status_code == 200
    assert response.json()["message"] == "This is publicly accessible information."