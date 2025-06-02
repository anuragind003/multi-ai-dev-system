import pytest
import os
from werkzeug.security import generate_password_hash
from typing import Generator, Any
from flask import Flask
from flask.testing import FlaskClient, FlaskCliRunner
from sqlalchemy.engine import Connection

# Attempt to import from the 'task_tracker' package structure.
# This assumes app.py, config.py, and models.py are within a 'task_tracker' directory
# relative to the project root (e.g., project_root/task_tracker/).
try:
    from task_tracker.app import create_app, db
    from task_tracker.config import TestConfig
    from task_tracker.models import User, Task
except ImportError:
    # Fallback for simpler project structures where app.py, config.py, and models.py
    # might be directly at the project root (parent of the 'tests' directory).
    # This adjusts the Python path to allow direct imports from the project root.
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sys.path.append(project_root)
    from app import create_app, db
    from config import TestConfig
    from models import User, Task


@pytest.fixture(scope='session')
def app() -> Generator[Flask, None, None]:
    """
    Fixture for creating and configuring a Flask application instance for testing.

    This fixture sets up a Flask application with a test configuration,
    typically using an in-memory SQLite database (`sqlite:///:memory:`).
    It ensures that the database tables are created once at the beginning
    of the test session and dropped at the end, providing a clean slate
    for all tests within that session.

    Yields:
        Flask: The configured Flask application instance.
    """
    # Use TestConfig which sets SQLALCHEMY_DATABASE_URI to 'sqlite:///:memory:'.
    # This ensures a fresh, isolated database for the entire test session,
    # which is faster and simpler than managing temporary files for each session.
    app_instance: Flask = create_app(config_class=TestConfig)

    # Establish an application context for the duration of the session.
    # This is necessary for SQLAlchemy operations like db.create_all()
    # and for accessing app-specific configurations.
    with app_instance.app_context():
        # Create all database tables defined in models.
        # This happens once per test session.
        db.create_all()

        yield app_instance  # Provide the app instance to tests.

        # Teardown: Drop all tables and remove the session after all tests in the
        # session are completed. This cleans up the in-memory database.
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(app: Flask) -> FlaskClient:
    """
    Fixture for a Flask test client.

    This client can be used to make HTTP requests to the Flask application
    within a test function. It operates within the context of the `app` fixture,
    meaning it uses the same application instance and database setup.

    Args:
        app (Flask): The Flask application instance provided by the `app` fixture.

    Returns:
        FlaskClient: The test client instance.
    """
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app: Flask) -> FlaskCliRunner:
    """
    Fixture for a Flask CLI test runner.

    This runner can be used to invoke Flask CLI commands (e.g., custom commands
    defined with `@app.cli.command()`) in tests. It provides a way to test
    command-line functionalities of the application.

    Args:
        app (Flask): The Flask application instance provided by the `app` fixture.

    Returns:
        FlaskCliRunner: The CLI test runner instance.
    """
    return app.test_cli_runner()


@pytest.fixture(scope='function')
def db_session(app: Flask) -> Generator[Any, None, None]:
    """
    Fixture for a clean database session for each test function.

    This fixture ensures that each test function starts with a fresh database
    state by wrapping the test's database operations in a transaction that is
    rolled back after the test completes. This prevents test side-effects
    (e.g., data created by one test) from affecting subsequent tests,
    ensuring test isolation.

    Args:
        app (Flask): The Flask application instance provided by the `app` fixture.

    Yields:
        SQLAlchemy: The SQLAlchemy database instance (`db`) with a transactional session.
    """
    with app.app_context():
        # Begin a new transaction for the test function.
        # This ensures that changes made by the test are rolled back
        # and do not affect other tests.
        connection: Connection = db.engine.connect()
        transaction = connection.begin()
        db.session.configure(bind=connection)

        yield db  # Provide the SQLAlchemy db object to the test.

        # Teardown: Rollback the transaction and clean up the session.
        # This discards all changes made by the test function.
        transaction.rollback()
        connection.close()
        db.session.remove()  # Ensure the session is removed for the next test.


@pytest.fixture(scope='function')
def test_user(db_session: Any) -> User:
    """
    Fixture to create and return a test user for authenticated tests.

    This user is added to the database within the transactional scope
    of `db_session` and will be rolled back after the test, ensuring
    no permanent changes to the database.

    Args:
        db_session (SQLAlchemy): The transactional database instance (`db`).

    Returns:
        User: The created test user object.
    """
    # Create a user with a hashed password.
    user = User(email='test@example.com', password_hash=generate_password_hash('password123'))
    db_session.session.add(user)
    db_session.session.commit()  # Commit to make the user available in the current transaction.
    return user


@pytest.fixture(scope='function')
def auth_client(client: FlaskClient, test_user: User) -> FlaskClient:
    """
    Fixture for a Flask test client that is logged in as `test_user`.

    This fixture simulates a user login by making a POST request to the
    login endpoint and then returns the client with the established session.
    This allows subsequent requests by the client to be authenticated.

    Args:
        client (FlaskClient): The base Flask test client.
        test_user (User): The test user to log in as.

    Returns:
        FlaskClient: The test client with an authenticated session.
    """
    # Assuming a login endpoint at '/auth/login' that accepts JSON
    # and sets a session cookie upon successful login.
    login_data = {
        'email': test_user.email,
        'password': 'password123'  # Use the raw password for login.
    }
    response = client.post('/auth/login', json=login_data)

    # Assert that login was successful. The exact status code depends on your
    # login implementation (e.g., 200 OK for API, 302 Redirect for web forms).
    # Assuming an API-style login that returns 200 OK on success.
    assert response.status_code == 200, \
        f"Login failed for {test_user.email} with status {response.status_code}: {response.data.decode()}"

    return client