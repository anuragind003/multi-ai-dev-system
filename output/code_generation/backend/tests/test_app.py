import pytest
from httpx import AsyncClient
from main import app # Assuming your FastAPI app instance is named 'app' in main.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db # Assuming these are in database.py

# Use a test database URL
TEST_DATABASE_URL = "postgresql://testuser:testpassword@localhost:5432/testdb"

# Setup test database engine and session
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(name="db_session")
def db_session_fixture():
    """
    Fixture to create a new database session for each test,
    and drop all tables after the test is complete.
    """
    Base.metadata.create_all(bind=engine) # Create tables
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables

@pytest.fixture(name="client")
async def client_fixture(db_session):
    """
    Fixture to create an AsyncClient for testing FastAPI endpoints.
    Overrides the get_db dependency to use the test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear() # Clear overrides after test

# --- Unit Tests (Example) ---

def test_read_root_unit():
    """
    Example of a simple unit test for a FastAPI endpoint.
    This doesn't hit a database.
    """
    # This is more of an integration test if it uses the actual app instance.
    # For true unit test, you'd mock dependencies.
    # But for FastAPI, testing the app instance directly is common.
    response = app.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI Backend!"}

def test_health_check_unit():
    response = app.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

# --- Integration Tests (Example) ---

@pytest.mark.asyncio
async def test_create_item_integration(client):
    """
    Example of an integration test that interacts with the database.
    """
    response = await client.post("/items/", json={"name": "Test Item", "description": "A test item"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "A test item"
    assert "id" in data

    # Verify item exists in DB
    response = await client.get(f"/items/{data['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Test Item"

@pytest.mark.asyncio
async def test_read_items_integration(client):
    # Create a few items first
    await client.post("/items/", json={"name": "Item 1", "description": "Desc 1"})
    await client.post("/items/", json={"name": "Item 2", "description": "Desc 2"})

    response = await client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(item["name"] == "Item 1" for item in data)
    assert any(item["name"] == "Item 2" for item in data)

@pytest.mark.asyncio
async def test_read_non_existent_item_integration(client):
    response = await client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

# Add more tests for other CRUD operations, edge cases, and error handling.