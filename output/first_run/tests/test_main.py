import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, Base, get_db, Task

# Override database URL for testing
DATABASE_URL = "sqlite:///./test_test.db"
engine = create_engine(DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# Set API_KEY for testing
os.environ["API_KEY"] = "test_api_key"

class TestMain(unittest.TestCase):

    def setUp(self):
        # Clean up the database before each test
        with TestingSessionLocal() as db:
            for task in db.query(Task).all():
                db.delete(task)
            db.commit()

    def test_read_root(self):
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Welcome to the Task List API!"})

    def test_create_task(self):
        response = client.post(
            "/tasks",
            json={"title": "Test Task", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Test Task")
        self.assertEqual(data["description"], "Test Description")
        self.assertIsInstance(data["id"], int)
        self.assertFalse(data["completed"])

    def test_create_task_empty_title(self):
        response = client.post(
            "/tasks",
            json={"title": "", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        self.assertEqual(response.status_code, 422)  # Unprocessable Entity

    def test_read_tasks(self):
        # Create a task first
        client.post(
            "/tasks",
            json={"title": "Test Task", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        response = client.get("/tasks", headers={"Authorization": "Bearer test_api_key"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)  # Assuming at least one task exists

    def test_read_task(self):
        # Create a task first
        create_response = client.post(
            "/tasks",
            json={"title": "Test Task", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        task_id = create_response.json()["id"]
        response = client.get(f"/tasks/{task_id}", headers={"Authorization": "Bearer test_api_key"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Test Task")
        self.assertEqual(data["description"], "Test Description")
        self.assertEqual(data["id"], task_id)

    def test_update_task(self):
        # Create a task first
        create_response = client.post(
            "/tasks",
            json={"title": "Test Task", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        task_id = create_response.json()["id"]
        response = client.put(
            f"/tasks/{task_id}",
            json={"title": "Updated Task", "completed": True},
            headers={"Authorization": "Bearer test_api_key"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "Updated Task")
        self.assertTrue(data["completed"])

    def test_delete_task(self):
        # Create a task first
        create_response = client.post(
            "/tasks",
            json={"title": "Test Task", "description": "Test Description"},
            headers={"Authorization": "Bearer test_api_key"},
        )
        task_id = create_response.json()["id"]
        response = client.delete(f"/tasks/{task_id}", headers={"Authorization": "Bearer test_api_key"})
        self.assertEqual(response.status_code, 204)

    def test_unauthorized_access(self):
        response = client.post("/tasks", json={"title": "Test Task"}, headers={"Authorization": "Bearer wrong_api_key"})
        self.assertEqual(response.status_code, 401)

        response = client.get("/tasks", headers={"Authorization": "Bearer wrong_api_key"})
        self.assertEqual(response.status_code, 401)

        response = client.get("/tasks/1", headers={"Authorization": "Bearer wrong_api_key"})
        self.assertEqual(response.status_code, 401)

        response = client.put("/tasks/1", json={"title": "Updated Task"}, headers={"Authorization": "Bearer wrong_api_key"})
        self.assertEqual(response.status_code, 401)

        response = client.delete("/tasks/1", headers={"Authorization": "Bearer wrong_api_key"})
        self.assertEqual(response.status_code, 401)

    def test_invalid_auth_scheme(self):
        response = client.post("/tasks", json={"title": "Test Task"}, headers={"Authorization": "Basic some_key"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid authentication scheme.  Must use Bearer.")

if __name__ == "__main__":
    unittest.main()