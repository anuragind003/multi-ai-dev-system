python
### FILE: tests/test_main.py
import pytest
from fastapi.testclient import TestClient
from ..main import app  # Import the FastAPI app
from ..database import Base, engine, get_db  # Import database setup
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..models import TaskCreate, TaskUpdate
from datetime import date

# Override the database for testing
TEST_DATABASE_URL = "sqlite:///./test_test.db"
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create a test client
@pytest.fixture(scope="module")
def test_app():
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Override the dependency
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield app
    # Clean up after tests
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def client(test_app):
    with TestClient(test_app) as client:
        yield client

@pytest.fixture
def api_key():
    return "test_api_key"  # Replace with your test API key

# --- Test Cases ---

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Task List API!"}

def test_create_task(client, api_key):
    task_data = TaskCreate(title="Test Task", description="Test Description", due_date=date(2024, 12, 31))
    headers = {"X-API-Key": api_key}
    response = client.post("/tasks", json=task_data.dict(), headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"
    assert data["due_date"] == "2024-12-31"
    assert "id" in data

def test_get_all_tasks(client, api_key):
    headers = {"X-API-Key": api_key}
    response = client.get("/tasks", headers=headers)
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)

def test_get_task(client, api_key):
    # First, create a task
    task_data = TaskCreate(title="Get Task Test", description="Get Task Description", due_date=date(2024, 12, 31))
    headers = {"X-API-Key": api_key}
    create_response = client.post("/tasks", json=task_data.dict(), headers=headers)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]

    # Then, get the task by ID
    get_response = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_response.status_code == 200
    retrieved_task = get_response.json()
    assert retrieved_task["id"] == task_id
    assert retrieved_task["title"] == "Get Task Test"

def test_update_task(client, api_key):
    # First, create a task
    task_data = TaskCreate(title="Update Task Test", description="Update Task Description", due_date=date(2024, 12, 31))
    headers = {"X-API-Key": api_key}
    create_response = client.post("/tasks", json=task_data.dict(), headers=headers)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]

    # Then, update the task
    update_data = TaskUpdate(title="Updated Task", completed=True)
    update_response = client.put(f"/tasks/{task_id}", json=update_data.dict(exclude_unset=True), headers=headers)
    assert update_response.status_code == 200
    updated_task = update_response.json()
    assert updated_task["title"] == "Updated Task"
    assert updated_task["completed"] is True

def test_delete_task(client, api_key):
    # First, create a task
    task_data = TaskCreate(title="Delete Task Test", description="Delete Task Description", due_date=date(2024, 12, 31))
    headers = {"X-API-Key": api_key}
    create_response = client.post("/tasks", json=task_data.dict(), headers=headers)
    assert create_response.status_code == 201
    created_task = create_response.json()
    task_id = created_task["id"]

    # Then, delete the task
    delete_response = client.delete(f"/tasks/{task_id}", headers=headers)
    assert delete_response.status_code == 204

    # Verify that the task is deleted
    get_response = client.get(f"/tasks/{task_id}", headers=headers)
    assert get_response.status_code == 404