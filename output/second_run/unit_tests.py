import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .main import app, get_db  # Import your FastAPI app
from .models import Base, Task, User
from .schemas import TaskCreate, TaskUpdate
from .config import settings
from jose import jwt

# Create a separate test database
TEST_DATABASE_URL = "sqlite:///./test.db"
test_engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override the database dependency for testing
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Create tables in the test database
Base.metadata.create_all(bind=test_engine)

# Create a test client
client = TestClient(app)

# Helper function to create a user and get a token
def create_test_user(db, username="testuser", password="testpassword"):
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(password)
    user = User(username=username, hashed_password=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_token(username="testuser", password="testpassword"):
    user = create_test_user(TestingSessionLocal(), username, password)
    payload = {"sub": username}
    access_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return access_token

@pytest.fixture(scope="module")
def test_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def test_user(test_db):
    return create_test_user(test_db)

@pytest.fixture(scope="module")
def test_token():
    return get_token()

def test_create_task(test_token):
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Test Task", "description": "Test Description"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["description"] == "Test Description"

def test_read_task(test_token):
    # Create a task first
    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Test Task Read", "description": "Test Description Read"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    response = client.get(f"/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {test_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task Read"

def test_update_task(test_token):
    # Create a task first
    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Test Task Update", "description": "Test Description Update"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    response = client.put(
        f"/api/v1/tasks/{task_id}",
        json={"title": "Updated Task", "description": "Updated Description", "completed": True},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["description"] == "Updated Description"
    assert data["completed"] is True

def test_delete_task(test_token):
    # Create a task first
    create_response = client.post(
        "/api/v1/tasks",
        json={"title": "Test Task Delete", "description": "Test Description Delete"},
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["id"]

    response = client.delete(f"/api/v1/tasks/{task_id}", headers={"Authorization": f"Bearer {test_token}"})
    assert response.status_code == 200
    assert response.json() == {"message": "Task deleted"}

def test_read_tasks(test_token):
    response = client.get("/api/v1/tasks", headers={"Authorization": f"Bearer {test_token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_create_user():
    response = client.post(
        "/api/v1/users",
        json={"username": "testuser2", "password": "testpassword"},
    )
    assert response.status_code == 201

def test_login_and_get_token():
    response = client.post(
        "/api/v1/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data

def test_protected_route(test_token):
    response = client.get("/api/v1/protected", headers={"Authorization": f"Bearer {test_token}"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data