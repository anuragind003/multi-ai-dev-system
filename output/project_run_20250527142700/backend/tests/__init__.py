import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import OperationalError
import os

# This __init__.py file for the 'tests' package defines common pytest fixtures
# that can be used across various test modules within the 'backend/tests' directory.
# It does NOT define the main application's create_app() function, as that
# typically resides in the main application package (e.g., backend/app/__init__.py).

# We assume the main application's `create_app` function and `db` SQLAlchemy instance
# are available from the `backend.app` package.
# If your project structure places `create_app` directly in `backend/__init__.py`,
# adjust the import path accordingly (e.g., `from backend import create_app, db`).
try:
    # Attempt to import from the 'app' sub-package within 'backend'
    # This requires 'backend' to be on the Python path, or tests run from the project root.
    from app import create_app, db
except ImportError:
    # Fallback for development/testing if 'app' package isn't fully set up or import fails.
    # In a production-ready test suite, this fallback should ideally not be needed.
    # This provides a minimal Flask app and SQLAlchemy instance for tests to proceed.
    print("Warning: Could not import 'create_app' or 'db' from 'app'. "
          "Using a placeholder setup for testing purposes.")
    
    _test_db = SQLAlchemy()
    def create_app(test_config=None):
        app = Flask(__name__)
        if test_config:
            app.config.update(test_config)
        else:
            app.config.from_mapping(
                TESTING=True,
                SQLALCHEMY_DATABASE_URI=os.environ.get('TEST_DATABASE_URL', 'postgresql://user:password@localhost:5432/test_cdp_db'),
                SQLALCHEMY_TRACK_MODIFICATIONS=False
            )
        _test_db.init_app(app)
        return app
    db = _test_db


@pytest.fixture(scope='session')
def app():
    """
    Creates and configures a new Flask app instance for the entire test session.
    It sets up a dedicated test database and ensures it's clean before and after tests.
    """
    # Use a dedicated test database URI from environment variable or a default
    test_db_uri = os.environ.get('TEST_DATABASE_URL', 'postgresql://user:password@localhost:5432/test_cdp_db')
    
    app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': test_db_uri,
        'SQLALCHEMY_TRACK_MODIFICATIONS': False
    })

    with app.app_context():
        # Ensure the database is clean before tests run
        try:
            db.drop_all()  # Drop all tables to ensure a clean slate
            db.create_all() # Create tables based on models
        except OperationalError as e:
            pytest.fail(f"Could not connect to test database or perform schema operations: {e}. "
                        f"Please ensure PostgreSQL is running and '{test_db_uri}' is accessible.")
        
        # Optionally, add common seed data here if needed for all tests
        # Example:
        # from app.models import Customer, Offer # Assuming models are in app/models.py
        # db.session.add(Customer(mobile_number='1234567890', pan_number='ABCDE1234F'))
        # db.session.commit()

    yield app  # Provide the app instance to tests

    with app.app_context():
        # Clean up the database after all tests in the session are complete
        db.session.remove() # Close the session
        db.drop_all() # Drop all tables


@pytest.fixture(scope='function')
def client(app):
    """
    Provides a test client for the Flask app, allowing simulation of HTTP requests.
    The scope is 'function' to ensure a fresh client for each test function.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    Provides a test runner for the Flask app's command-line interface (CLI) commands.
    The scope is 'function' to ensure a fresh runner for each test function.
    """
    return app.test_cli_runner()