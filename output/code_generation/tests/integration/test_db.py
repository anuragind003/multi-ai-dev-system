import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, engine, SessionLocal
from app.main import app, get_db
from app import models, crud, schemas
from fastapi.testclient import TestClient

# Use the actual PostgreSQL database for integration tests
# Ensure your .env or environment variables are set for this to connect to a test DB
# For CI/CD, this would connect to a temporary DB instance or a test schema.
# For local, ensure your docker-compose `db` service is running.
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/mydatabase")

# Create a dedicated engine for integration tests
integration_engine = create_engine(DATABASE_URL)
IntegrationTestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=integration_engine)

# Override the get_db dependency for integration tests
def override_get_db_integration():
    try:
        db = IntegrationTestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db_integration

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_and_teardown_db():
    """
    Fixture to set up and tear down the database for integration tests.
    This ensures a clean state for each test run.
    """
    print(f"\nConnecting to database for integration tests: {DATABASE_URL}")
    try:
        # Drop all tables if they exist
        Base.metadata.drop_all(bind=integration_engine)
        # Create all tables
        Base.metadata.create_all(bind=integration_engine)
        print("Database tables created for integration tests.")
        yield
    except Exception as e:
        print(f"Error during database setup/teardown: {e}")
        pytest.fail(f"Could not connect to or set up integration database: {e}")
    finally:
        # Clean up: drop all tables after tests
        Base.metadata.drop_all(bind=integration_engine)
        print("Database tables dropped after integration tests.")

def test_db_connection():
    """Test direct database connection."""
    try:
        with integration_engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("Direct database connection successful.")
    except Exception as e:
        pytest.fail(f"Failed to connect to the database: {e}")

def test_health_check_with_real_db():
    """Test the health check endpoint with the real database."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}

def test_create_and_read_user_integration():
    """Test creating and reading a user end-to-end with the real database."""
    # Create a user
    user_data = {"email": "integration_test@example.com", "password": "securepassword"}
    response = client.post("/users/", json=user_data)
    assert response.status_code == 200
    created_user = response.json()
    assert created_user["email"] == user_data["email"]
    assert "id" in created_user

    # Read the user back
    response = client.get(f"/users/{created_user['id']}")
    assert response.status_code == 200
    read_user = response.json()
    assert read_user["email"] == user_data["email"]
    assert read_user["id"] == created_user["id"]

    # Verify user exists in the database directly
    db = IntegrationTestingSessionLocal()
    db_user = crud.get_user_by_email(db, email=user_data["email"])
    db.close()
    assert db_user is not None
    assert db_user.email == user_data["email"]
    assert db_user.id == created_user["id"]

def test_duplicate_user_creation_integration():
    """Test that creating a duplicate user fails with the real database."""
    user_data = {"email": "duplicate_integration@example.com", "password": "pass"}
    client.post("/users/", json=user_data) # First creation
    response = client.post("/users/", json=user_data) # Second creation
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"