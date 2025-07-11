# tests/test_unit.py - Unit tests for FastAPI application

from fastapi.testclient import TestClient
from app.main import app, get_db_connection, Item
import pytest
from unittest.mock import patch, MagicMock

# Create a TestClient instance for the FastAPI application
client = TestClient(app)

# Mock database connection for unit tests
@pytest.fixture(autouse=True)
def mock_db_connection():
    with patch('app.main.psycopg2.connect') as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_connect.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1,) # For create_item returning ID
        yield mock_connect, mock_conn, mock_cursor

def test_read_root():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the FastAPI Monolith Application!"}

def test_health_check_success(mock_db_connection):
    """Test health check when database connection is successful."""
    mock_connect, mock_conn, mock_cursor = mock_db_connection
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "database": "connected"}
    mock_connect.assert_called_once()
    mock_cursor.execute.assert_called_once_with("SELECT 1")
    mock_cursor.close.assert_called_once()
    mock_conn.close.assert_called_once()

def test_health_check_db_failure():
    """Test health check when database connection fails."""
    with patch('app.main.psycopg2.connect', side_effect=Exception("DB connection error")):
        response = client.get("/health")
        assert response.status_code == 503
        assert "Could not connect to the database" in response.json()["detail"]

def test_create_item_success(mock_db_connection):
    """Test creating an item successfully."""
    mock_connect, mock_conn, mock_cursor = mock_db_connection
    item_data = {"name": "Test Item", "description": "A test description", "price": 10.99, "tax": 0.50}
    response = client.post("/items/", json=item_data)
    assert response.status_code == 201
    assert response.json()["name"] == item_data["name"]
    mock_cursor.execute.assert_called_once()
    mock_conn.commit.assert_called_once()

def test_create_item_invalid_data():
    """Test creating an item with invalid data."""
    invalid_item_data = {"name": "Invalid Item", "price": "not_a_number"}
    response = client.post("/items/", json=invalid_item_data)
    assert response.status_code == 422 # Unprocessable Entity for validation errors

def test_read_item_success(mock_db_connection):
    """Test reading an item successfully."""
    mock_connect, mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = ("Existing Item", "Desc", 20.00, 1.00)
    response = client.get("/items/1")
    assert response.status_code == 200
    assert response.json()["name"] == "Existing Item"
    mock_cursor.execute.assert_called_once_with("SELECT name, description, price, tax FROM items WHERE id = %s;", (1,))

def test_read_item_not_found(mock_db_connection):
    """Test reading a non-existent item."""
    mock_connect, mock_conn, mock_cursor = mock_db_connection
    mock_cursor.fetchone.return_value = None # Simulate item not found
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"

def test_read_item_db_error():
    """Test reading an item when database operation fails."""
    with patch('app.main.psycopg2.connect', side_effect=Exception("DB read error")):
        response = client.get("/items/1")
        assert response.status_code == 500
        assert "Failed to retrieve item" in response.json()["detail"]

def test_startup_event_db_init_success(mock_db_connection):
    """Test startup event ensures table creation."""
    mock_connect, mock_conn, mock_cursor = mock_db_connection
    # Call the startup event directly for testing
    with patch('app.main.get_db_connection', return_value=mock_conn):
        app.fire_event("startup")
        mock_cursor.execute.assert_called_once()
        assert "CREATE TABLE IF NOT EXISTS items" in mock_cursor.execute.call_args[0][0]
        mock_conn.commit.assert_called_once()

def test_startup_event_db_init_failure():
    """Test startup event handles database initialization failure."""
    with patch('app.main.psycopg2.connect', side_effect=Exception("Startup DB error")):
        # The startup event is called when FastAPI app starts.
        # For testing, we can simulate it or just observe the error logging.
        # FastAPI's on_event("startup") doesn't raise exceptions directly to the caller,
        # but logs them. We can check if an exception is logged.
        with patch('app.main.logger.error') as mock_logger_error:
            app.fire_event("startup")
            mock_logger_error.assert_called_once()
            assert "Error during database startup initialization" in mock_logger_error.call_args[0][0]