import pytest
from src.app import create_app, init_db

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app({
        'TESTING': True,
        'DATABASE': ':memory:',  # Use in-memory SQLite for tests
    })

    with app.app_context():
        # Initialize the database schema for the test database.
        # This calls the init_db function from src/app.py,
        # which should execute the schema creation SQL.
        init_db()

    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()