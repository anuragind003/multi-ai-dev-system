import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app, get_db
from app.database import Base, SQLALCHEMY_DATABASE_URL
from app.models import Item
from app.schemas import ItemCreate

# Use a separate test database
TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency for tests
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(name="client")
def client_fixture():
    # Create the database tables before each test
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    # Drop the database tables after each test
    Base.metadata.drop_all(bind=engine)

def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to FastAPI backend!"}

def test_create_item(client):
    item_data = {"name": "Test Item", "description": "This is a test item."}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == item_data["name"]
    assert data["description"] == item_data["description"]
    assert "id" in data

    # Verify item is in the database
    db = TestingSessionLocal()
    item = db.query(Item).filter(Item.name == item_data["name"]).first()
    assert item is not None
    assert item.description == item_data["description"]
    db.close()

def test_read_items(client):
    # Create a few items first
    client.post("/items/", json={"name": "Item 1", "description": "Desc 1"})
    client.post("/items/", json={"name": "Item 2", "description": "Desc 2"})

    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Item 1"
    assert data[1]["name"] == "Item 2"

def test_read_non_existent_item(client):
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}

def test_update_item(client):
    # Create an item to update
    create_response = client.post("/items/", json={"name": "Old Name", "description": "Old Desc"})
    item_id = create_response.json()["id"]

    update_data = {"name": "New Name", "description": "New Desc"}
    response = client.put(f"/items/{item_id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == update_data["name"]
    assert data["description"] == update_data["description"]

    # Verify update in DB
    db = TestingSessionLocal()
    item = db.query(Item).filter(Item.id == item_id).first()
    assert item.name == update_data["name"]
    db.close()

def test_delete_item(client):
    # Create an item to delete
    create_response = client.post("/items/", json={"name": "To Delete", "description": "Delete me"})
    item_id = create_response.json()["id"]

    response = client.delete(f"/items/{item_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Item deleted successfully"}

    # Verify item is deleted from DB
    db = TestingSessionLocal()
    item = db.query(Item).filter(Item.id == item_id).first()
    assert item is None
    db.close()