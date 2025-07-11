import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base
from app import models, schemas
import os

# Use a separate test database
TEST_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://testuser:testpassword@localhost:5432/testdb")

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def setup_database():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests are done
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session(setup_database):
    """
    Provides a clean database session for each test function.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Override the get_db dependency for tests
    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear() # Clear overrides after test

@pytest.fixture(scope="module")
def client():
    """
    Provides a TestClient for the FastAPI application.
    """
    with TestClient(app) as c:
        yield c

# --- Unit Tests (can be run without DB, but here we use the test client) ---

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "Application is healthy"}

# --- Integration Tests (require DB) ---

def test_create_item(client, db_session):
    item_data = {"name": "Test Item", "description": "This is a test item."}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["description"] == item_data["description"]
    assert "id" in data

    # Verify item is in DB
    db_item = db_session.query(models.Item).filter(models.Item.id == data["id"]).first()
    assert db_item is not None
    assert db_item.name == item_data["name"]

def test_read_items_empty(client, db_session):
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == []

def test_read_items_with_data(client, db_session):
    item1 = models.Item(name="Item 1", description="Desc 1")
    item2 = models.Item(name="Item 2", description="Desc 2")
    db_session.add_all([item1, item2])
    db_session.commit()
    db_session.refresh(item1)
    db_session.refresh(item2)

    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert any(item["name"] == "Item 1" for item in data)
    assert any(item["name"] == "Item 2" for item in data)

def test_read_single_item(client, db_session):
    item = models.Item(name="Single Item", description="Description for single item")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.get(f"/items/{item.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Single Item"
    assert data["id"] == item.id

def test_read_non_existent_item(client, db_session):
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

def test_update_item(client, db_session):
    item = models.Item(name="Original Item", description="Original Description")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    updated_data = {"name": "Updated Item", "description": "Updated Description"}
    response = client.put(f"/items/{item.id}", json=updated_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Item"
    assert data["description"] == "Updated Description"
    assert data["id"] == item.id

    db_item = db_session.query(models.Item).filter(models.Item.id == item.id).first()
    assert db_item.name == "Updated Item"

def test_delete_item(client, db_session):
    item = models.Item(name="Item to Delete", description="Will be deleted")
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)

    response = client.delete(f"/items/{item.id}")
    assert response.status_code == 204 # No Content

    # Verify item is deleted
    db_item = db_session.query(models.Item).filter(models.Item.id == item.id).first()
    assert db_item is None

    # Try to delete non-existent item
    response = client.delete("/items/999")
    assert response.status_code == 404