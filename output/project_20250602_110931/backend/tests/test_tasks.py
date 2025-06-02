import pytest
from backend.app import create_app, db
from backend.models import User, Task
from datetime import datetime

@pytest.fixture
def app():
    """
    Pytest fixture to create and configure a Flask test application.
    Uses an in-memory SQLite database for testing to ensure isolation
    between tests.
    """
    app = create_app('testing') # Use 'testing' configuration
    with app.app_context():
        db.create_all() # Create database tables for the test
        yield app # Provide the app to the tests
        db.session.remove() # Clean up session
        db.drop_all() # Drop all tables after tests complete

@pytest.fixture
def client(app):
    """
    Pytest fixture to provide a test client for the Flask application.
    This client can be used to make requests to the application.
    """
    return app.test_client()

def register_and_login(client, email, password):
    """
    Helper function to register a user and then log them in,
    returning the access token.
    """
    # Register the user
    register_response = client.post(
        '/auth/register',
        json={'email': email, 'password': password}
    )
    assert register_response.status_code == 201

    # Log in the user
    login_response = client.post(
        '/auth/login',
        json={'email': email, 'password': password}
    )
    assert login_response.status_code == 200
    assert 'access_token' in login_response.json
    return login_response.json['access_token']

# --- Task Creation Tests ---

def test_create_task_success(client):
    """
    Test that an authenticated user can successfully create a task.
    Verifies status code, presence of ID, and correct data in response.
    """
    token = register_and_login(client, 'testuser@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    task_data = {
        'title': 'My First Task',
        'description': 'This is a detailed description for my first task.',
        'due_date': '2023-12-31'
    }
    response = client.post('/tasks', json=task_data, headers=headers)

    assert response.status_code == 201
    assert 'id' in response.json
    assert response.json['title'] == 'My First Task'
    assert response.json['description'] == 'This is a detailed description for my first task.'
    # Due date is stored as datetime and returned as ISO format (YYYY-MM-DDTHH:MM:SS)
    assert response.json['due_date'] == '2023-12-31T00:00:00'
    assert response.json['completed'] is False
    assert 'user_id' in response.json

def test_create_task_missing_title(client):
    """
    Test that creating a task without a title fails with a 400 error.
    """
    token = register_and_login(client, 'user2@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    task_data = {'description': 'No title here'}
    response = client.post('/tasks', json=task_data, headers=headers)

    assert response.status_code == 400
    assert 'message' in response.json
    assert response.json['message'] == 'Title is required'

def test_create_task_unauthorized(client):
    """
    Test that creating a task without an authentication token fails with a 401 error.
    """
    task_data = {'title': 'Unauthorized Task'}
    response = client.post('/tasks', json=task_data)
    assert response.status_code == 401
    assert 'msg' in response.json # Flask-JWT-Extended unauthorized message

def test_create_task_invalid_due_date_format(client):
    """
    Test that creating a task with an invalid due date format fails.
    """
    token = register_and_login(client, 'user_date@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    task_data = {
        'title': 'Task with bad date',
        'due_date': '31-12-2023' # Invalid format
    }
    response = client.post('/tasks', json=task_data, headers=headers)
    assert response.status_code == 400
    assert response.json['message'] == 'Invalid due date format. Use YYYY-MM-DD'

# --- Task Retrieval Tests ---

def test_get_tasks_success(client):
    """
    Test that an authenticated user can retrieve their tasks.
    Verifies that only tasks belonging to the current user are returned.
    """
    token1 = register_and_login(client, 'user_a@example.com', 'password123')
    token2 = register_and_login(client, 'user_b@example.com', 'password123')

    # User A creates tasks
    client.post('/tasks', json={'title': 'User A Task 1'}, headers={'Authorization': f'Bearer {token1}'})
    client.post('/tasks', json={'title': 'User A Task 2'}, headers={'Authorization': f'Bearer {token1}'})

    # User B creates a task
    client.post('/tasks', json={'title': 'User B Task 1'}, headers={'Authorization': f'Bearer {token2}'})

    # User A retrieves tasks
    response_a = client.get('/tasks', headers={'Authorization': f'Bearer {token1}'})
    assert response_a.status_code == 200
    assert len(response_a.json) == 2
    assert response_a.json[0]['title'] == 'User A Task 1'
    assert response_a.json[1]['title'] == 'User A Task 2'

    # User B retrieves tasks
    response_b = client.get('/tasks', headers={'Authorization': f'Bearer {token2}'})
    assert response_b.status_code == 200
    assert len(response_b.json) == 1
    assert response_b.json[0]['title'] == 'User B Task 1'

def test_get_tasks_unauthorized(client):
    """
    Test that retrieving tasks without authentication fails.
    """
    response = client.get('/tasks')
    assert response.status_code == 401

def test_get_single_task_success(client):
    """
    Test that an authenticated user can retrieve a specific task by ID.
    """
    token = register_and_login(client, 'single_task_user@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}

    # Create a task
    create_response = client.post('/tasks', json={'title': 'Specific Task'}, headers=headers)
    task_id = create_response.json['id']

    # Retrieve the task
    get_response = client.get(f'/tasks/{task_id}', headers=headers)
    assert get_response.status_code == 200
    assert get_response.json['id'] == task_id
    assert get_response.json['title'] == 'Specific Task'

def test_get_single_task_not_found(client):
    """
    Test that retrieving a non-existent task returns a 404 error.
    """
    token = register_and_login(client, 'not_found_user@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/tasks/99999', headers=headers) # Assuming this ID does not exist
    assert response.status_code == 404
    assert response.json['message'] == 'Task not found'

def test_get_single_task_other_user(client):
    """
    Test that a user cannot retrieve a task belonging to another user.
    The API should return 404 as if the task doesn't exist for the current user.
    """
    token1 = register_and_login(client, 'owner@example.com', 'password123')
    token2 = register_and_login(client, 'intruder@example.com', 'password123')

    # Owner creates a task
    create_response = client.post('/tasks', json={'title': 'Owners Secret Task'}, headers={'Authorization': f'Bearer {token1}'})
    task_id = create_response.json['id']

    # Intruder tries to retrieve the task
    response = client.get(f'/tasks/{task_id}', headers={'Authorization': f'Bearer {token2}'})
    assert response.status_code == 404 # Should return 404 as if not found for user2

# --- Task Update Tests ---

def test_update_task_success(client):
    """
    Test that an authenticated user can successfully update their task.
    Verifies partial updates and changes to 'completed' status.
    """
    token = register_and_login(client, 'update_user@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}

    # Create an initial task
    create_response = client.post(
        '/tasks',
        json={'title': 'Old Title', 'description': 'Old Description', 'completed': False, 'due_date': '2023-01-01'},
        headers=headers
    )
    task_id = create_response.json['id']

    # Update the task
    update_data = {
        'title': 'New Title',
        'description': 'New Description',
        'completed': True,
        'due_date': '2024-01-01'
    }
    update_response = client.put(f'/tasks/{task_id}', json=update_data, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json['id'] == task_id
    assert update_response.json['title'] == 'New Title'
    assert update_response.json['description'] == 'New Description'
    assert update_response.json['completed'] is True
    assert update_response.json['due_date'] == '2024-01-01T00:00:00'

    # Verify by fetching again
    get_response = client.get(f'/tasks/{task_id}', headers=headers)
    assert get_response.status_code == 200
    assert get_response.json['title'] == 'New Title'
    assert get_response.json['completed'] is True

def test_update_task_partial_update(client):
    """
    Test that a user can perform a partial update on a task (e.g., only change title).
    """
    token = register_and_login(client, 'partial_user@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}

    create_response = client.post(
        '/tasks',
        json={'title': 'Initial Title', 'description': 'Initial Description', 'completed': False},
        headers=headers
    )
    task_id = create_response.json['id']

    update_data = {'title': 'Only Title Changed'}
    update_response = client.put(f'/tasks/{task_id}', json=update_data, headers=headers)
    assert update_response.status_code == 200
    assert update_response.json['title'] == 'Only Title Changed'
    assert update_response.json['description'] == 'Initial Description' # Should remain unchanged
    assert update_response.json['completed'] is False # Should remain unchanged

def test_update_task_not_found(client):
    """
    Test that updating a non-existent task returns a 404 error.
    """
    token = register_and_login(client, 'update_not_found@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    update_data = {'title': 'Attempt to update non-existent'}
    response = client.put('/tasks/99999', json=update_data, headers=headers)
    assert response.status_code == 404
    assert response.json['message'] == 'Task not found'

def test_update_task_other_user(client):
    """
    Test that a user cannot update a task belonging to another user.
    The API should return 404 as if the task doesn't exist for the current user.
    """
    token1 = register_and_login(client, 'owner_update@example.com', 'password123')
    token2 = register_and_login(client, 'intruder_update@example.com', 'password123')

    # Owner creates a task
    create_response = client.post('/tasks', json={'title': 'Owners Task'}, headers={'Authorization': f'Bearer {token1}'})
    task_id = create_response.json['id']

    # Intruder tries to update the task
    update_data = {'title': 'Malicious Update'}
    response = client.put(f'/tasks/{task_id}', json=update_data, headers={'Authorization': f'Bearer {token2}'})
    assert response.status_code == 404 # Should return 404 as if not found for user2

def test_update_task_invalid_due_date_format(client):
    """
    Test that updating a task with an invalid due date format fails.
    """
    token = register_and_login(client, 'user_update_date@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    create_response = client.post(
        '/tasks',
        json={'title': 'Task to update date'},
        headers=headers
    )
    task_id = create_response.json['id']

    update_data = {'due_date': '2023/12/31'} # Invalid format
    response = client.put(f'/tasks/{task_id}', json=update_data, headers=headers)
    assert response.status_code == 400
    assert response.json['message'] == 'Invalid due date format. Use YYYY-MM-DD'

# --- Task Deletion Tests ---

def test_delete_task_success(client):
    """
    Test that an authenticated user can successfully delete their task.
    Verifies status code and that the task is no longer retrievable.
    """
    token = register_and_login(client, 'delete_user@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}

    # Create a task to delete
    create_response = client.post('/tasks', json={'title': 'Task to be deleted'}, headers=headers)
    task_id = create_response.json['id']

    # Delete the task
    delete_response = client.delete(f'/tasks/{task_id}', headers=headers)
    assert delete_response.status_code == 204 # No Content for successful deletion

    # Verify deletion by trying to retrieve the task
    get_response = client.get(f'/tasks/{task_id}', headers=headers)
    assert get_response.status_code == 404
    assert get_response.json['message'] == 'Task not found'

def test_delete_task_not_found(client):
    """
    Test that deleting a non-existent task returns a 404 error.
    """
    token = register_and_login(client, 'delete_not_found@example.com', 'password123')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.delete('/tasks/99999', headers=headers)
    assert response.status_code == 404
    assert response.json['message'] == 'Task not found'

def test_delete_task_other_user(client):
    """
    Test that a user cannot delete a task belonging to another user.
    The API should return 404 as if the task doesn't exist for the current user.
    """
    token1 = register_and_login(client, 'owner_delete@example.com', 'password123')
    token2 = register_and_login(client, 'intruder_delete@example.com', 'password123')

    # Owner creates a task
    create_response = client.post('/tasks', json={'title': 'Owners Delete Task'}, headers={'Authorization': f'Bearer {token1}'})
    task_id = create_response.json['id']

    # Intruder tries to delete the task
    response = client.delete(f'/tasks/{task_id}', headers={'Authorization': f'Bearer {token2}'})
    assert response.status_code == 404 # Should return 404 as if not found for user2

def test_delete_task_unauthorized(client):
    """
    Test that deleting a task without authentication fails.
    """
    # Create a task (it won't be deleted in this test, just exists for the ID)
    token = register_and_login(client, 'temp_user@example.com', 'password123')
    create_response = client.post('/tasks', json={'title': 'Temp Task'}, headers={'Authorization': f'Bearer {token}'})
    task_id = create_response.json['id']

    # Attempt to delete without token
    response = client.delete(f'/tasks/{task_id}')
    assert response.status_code == 401