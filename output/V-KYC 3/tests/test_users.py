import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import User, Role
from app.security import get_password_hash
from app.config import settings

# Override the database URL for testing to use an in-memory SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Use StaticPool for SQLite in-memory to keep the same connection
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency for tests
@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Fixture that provides a clean database session for each test.
    Tables are created before each test and dropped after.
    """
    Base.metadata.create_all(bind=engine) # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables

@pytest.fixture(name="client")
def client_fixture(db_session):
    """
    Fixture that provides a FastAPI TestClient with the overridden database dependency.
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides = {} # Clear overrides after test

# Helper function to create a user directly in the DB for testing
def create_test_user(db_session, email, password, role_name, first_name=None, last_name=None, is_active=True):
    role = db_session.query(Role).filter(Role.name == role_name).first()
    if not role:
        role = Role(name=role_name)
        db_session.add(role)
        db_session.commit()
        db_session.refresh(role)

    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
        role_id=role.id
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

# --- Tests for User Registration ---
def test_register_user_success(client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "test@example.com",
            "password": "Password@123",
            "first_name": "Test",
            "last_name": "User",
            "role_name": "Team Lead"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["first_name"] == "Test"
    assert data["role"]["name"] == "Team Lead"
    assert "id" in data

def test_register_user_duplicate_email(client, db_session):
    create_test_user(db_session, "existing@example.com", "Password@123", "Team Lead")
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "existing@example.com",
            "password": "NewPassword@123",
            "first_name": "Another",
            "last_name": "User",
            "role_name": "Process Manager"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "User with this email already exists."

def test_register_user_invalid_password(client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "email": "weakpass@example.com",
            "password": "weak", # Too short, no special char, no digit, no uppercase
            "first_name": "Weak",
            "last_name": "Pass",
            "role_name": "Team Lead"
        }
    )
    assert response.status_code == 422 # Unprocessable Entity due to Pydantic validation
    assert "password" in response.json()["detail"][0]["loc"]
    assert "Password must contain at least one uppercase letter" in response.json()["detail"][0]["msg"]

# --- Tests for User Login ---
def test_login_success(client, db_session):
    create_test_user(db_session, "login@example.com", "LoginPass@123", "Team Lead")
    response = client.post(
        "/api/v1/users/login",
        json={"email": "login@example.com", "password": "LoginPass@123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/v1/users/login",
        json={"email": "nonexistent@example.com", "password": "WrongPassword@123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password."

def test_login_inactive_user(client, db_session):
    create_test_user(db_session, "inactive@example.com", "ActivePass@123", "Team Lead", is_active=False)
    response = client.post(
        "/api/v1/users/login",
        json={"email": "inactive@example.com", "password": "ActivePass@123"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User account is inactive."

# --- Tests for /me endpoint ---
def test_read_users_me_success(client, db_session):
    user = create_test_user(db_session, "me@example.com", "MyPassword@123", "Process Manager")
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "me@example.com", "password": "MyPassword@123"}
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["role"]["name"] == "Process Manager"
    assert data["id"] == user.id

def test_read_users_me_unauthorized(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."

def test_read_users_me_inactive_user(client, db_session):
    create_test_user(db_session, "inactive_me@example.com", "InactivePass@123", "Team Lead", is_active=False)
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "inactive_me@example.com", "password": "InactivePass@123"}
    )
    token = login_response.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user."

# --- Tests for Seed Initial Users Endpoint ---
def test_seed_initial_users_success_as_admin(client, db_session):
    # Create an admin user to trigger the seeding
    admin_user = create_test_user(db_session, "admin@test.com", "AdminPass@123", "Admin")
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "admin@test.com", "password": "AdminPass@123"}
    )
    token = login_response.json()["access_token"]

    # Ensure initial users from settings are not already present
    assert db_session.query(User).filter(User.email == settings.INITIAL_TEAM_LEAD_EMAIL).first() is None
    assert db_session.query(User).filter(User.email == settings.INITIAL_PROCESS_MANAGER_EMAIL).first() is None

    response = client.post(
        "/api/v1/users/seed-initial-users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["message"].startswith("Initial users and roles seeding process initiated.")

    # Verify users are created
    team_lead_user = db_session.query(User).filter(User.email == settings.INITIAL_TEAM_LEAD_EMAIL).first()
    process_manager_user = db_session.query(User).filter(User.email == settings.INITIAL_PROCESS_MANAGER_EMAIL).first()

    assert team_lead_user is not None
    assert team_lead_user.email == settings.INITIAL_TEAM_LEAD_EMAIL
    assert team_lead_user.role.name == "Team Lead"

    assert process_manager_user is not None
    assert process_manager_user.email == settings.INITIAL_PROCESS_MANAGER_EMAIL
    assert process_manager_user.role.name == "Process Manager"

def test_seed_initial_users_forbidden_for_non_admin(client, db_session):
    # Create a non-admin user
    non_admin_user = create_test_user(db_session, "nonadmin@test.com", "UserPass@123", "Team Lead")
    login_response = client.post(
        "/api/v1/users/login",
        json={"email": "nonadmin@test.com", "password": "UserPass@123"}
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/users/seed-initial-users",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "User does not have the required role. Required: Admin"

def test_seed_initial_users_unauthorized(client):
    response = client.post("/api/v1/users/seed-initial-users")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated."