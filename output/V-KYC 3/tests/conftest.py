import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models import User, Role, Permission, RolePermission
from app.security import get_password_hash
from app.logger import logger

# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite:///./test.db" # Use a file-based SQLite for persistence during test run
# For a truly in-memory, non-persistent DB: "sqlite:///:memory:"

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """
    Sets up a clean database for testing before all tests run
    and tears it down after all tests are complete.
    """
    logger.info("Setting up test database...")
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool, # Important for SQLite in-memory or file-based with multiple threads
        echo=False # Set to True to see SQL queries during tests
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Override the get_db dependency for tests
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Populate with initial data (roles, permissions, admin user)
    with TestingSessionLocal() as db:
        # Create default roles
        admin_role = Role(name="admin", description="Full administrative access")
        auditor_role = Role(name="auditor", description="Can view and download recordings")
        uploader_role = Role(name="uploader", description="Can upload and manage their own recordings")
        db.add_all([admin_role, auditor_role, uploader_role])
        db.commit()
        db.refresh(admin_role)
        db.refresh(auditor_role)
        db.refresh(uploader_role)

        # Create default permissions
        permissions_data = {
            "user:read": "View user details",
            "user:write": "Create/update user details",
            "user:delete": "Delete users",
            "role:read": "View role details",
            "role:write": "Create/update role details",
            "recording:read": "View recording metadata",
            "recording:download": "Download recording files",
            "recording:upload": "Upload new recordings",
            "recording:delete": "Delete recordings",
            "bulk_request:read": "View bulk request details",
            "bulk_request:write": "Create/update bulk requests",
        }
        permissions = {}
        for name, desc in permissions_data.items():
            perm = Permission(name=name, description=desc)
            db.add(perm)
            permissions[name] = perm
        db.commit()
        for perm in permissions.values():
            db.refresh(perm)

        # Assign permissions to roles
        role_permissions_map = {
            admin_role: [
                "user:read", "user:write", "user:delete",
                "role:read", "role:write",
                "recording:read", "recording:download", "recording:upload", "recording:delete",
                "bulk_request:read", "bulk_request:write"
            ],
            auditor_role: [
                "user:read",
                "recording:read", "recording:download",
                "bulk_request:read"
            ],
            uploader_role: [
                "recording:read", "recording:upload",
                "bulk_request:read", "bulk_request:write"
            ]
        }
        for role, perm_names in role_permissions_map.items():
            for perm_name in perm_names:
                rp = RolePermission(role_id=role.id, permission_id=permissions[perm_name].id)
                db.add(rp)
        db.commit()

        # Create test users
        admin_user = User(
            email="test_admin@example.com",
            hashed_password=get_password_hash("testpassword"),
            first_name="Test", last_name="Admin", is_active=True, role_id=admin_role.id
        )
        auditor_user = User(
            email="test_auditor@example.com",
            hashed_password=get_password_hash("testpassword"),
            first_name="Test", last_name="Auditor", is_active=True, role_id=auditor_role.id
        )
        uploader_user = User(
            email="test_uploader@example.com",
            hashed_password=get_password_hash("testpassword"),
            first_name="Test", last_name="Uploader", is_active=True, role_id=uploader_role.id
        )
        inactive_user = User(
            email="inactive@example.com",
            hashed_password=get_password_hash("testpassword"),
            first_name="Inactive", last_name="User", is_active=False, role_id=auditor_role.id
        )
        db.add_all([admin_user, auditor_user, uploader_user, inactive_user])
        db.commit()
        db.refresh(admin_user)
        db.refresh(auditor_user)
        db.refresh(uploader_user)
        db.refresh(inactive_user)
        logger.info("Test users created.")

    yield # Run the tests

    # Teardown: Drop all tables after tests are done
    logger.info("Tearing down test database...")
    Base.metadata.drop_all(bind=test_engine)
    # Clean up the test.db file if it's not in-memory
    import os
    if os.path.exists("./test.db"):
        os.remove("./test.db")
    logger.info("Test database torn down.")


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient for making requests to the FastAPI app."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def admin_token(client):
    """Provides an access token for the test admin user."""
    response = client.post(
        "/api/v1/token",
        data={"username": "test_admin@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def auditor_token(client):
    """Provides an access token for the test auditor user."""
    response = client.post(
        "/api/v1/token",
        data={"username": "test_auditor@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def uploader_token(client):
    """Provides an access token for the test uploader user."""
    response = client.post(
        "/api/v1/token",
        data={"username": "test_uploader@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def inactive_token(client):
    """Provides an access token for the test inactive user."""
    response = client.post(
        "/api/v1/token",
        data={"username": "inactive@example.com", "password": "testpassword"}
    )
    # Inactive user should not be able to get a token
    assert response.status_code == 401
    return None # Or raise an exception if you want to explicitly test this failure