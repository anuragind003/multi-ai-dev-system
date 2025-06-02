import pytest
from backend.app import create_app, db

@pytest.fixture(scope='session')
def app():
    """
    Fixture for the Flask application instance.

    This fixture sets up a Flask application configured for testing.
    It uses an in-memory SQLite database for speed and isolation.
    The database schema is created once for the entire test session.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Use in-memory SQLite for tests
        "WTF_CSRF_ENABLED": False,  # Disable CSRF for easier form testing
        "SECRET_KEY": "test_secret_key_for_testing",  # A dummy secret key for session management
    })

    # Establish an application context before yielding the app.
    # This is crucial for Flask-SQLAlchemy and other extensions that rely on it.
    with app.app_context():
        # Create all database tables based on the models
        db.create_all()
        yield app
        # Drop all tables after the test session is complete
        db.drop_all()

@pytest.fixture(scope='function')
def client(app):
    """
    Fixture for the Flask test client.

    This fixture provides a test client that can be used to make requests
    to the Flask application during tests. It operates within the application
    context provided by the `app` fixture. Each test function gets a fresh client.
    """
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """
    Fixture for the Flask CLI test runner.

    This fixture provides a test runner that can be used to invoke Flask CLI commands
    during tests, e.g., for testing custom commands. Each test function gets a fresh runner.
    """
    return app.test_cli_runner()

@pytest.fixture(scope='function')
def session(app):
    """
    Fixture for a database session with transaction rollback.

    This fixture provides a database session that can be used for direct
    database interactions (e.g., adding test data, querying) within tests.
    It ensures that all changes made during a test are rolled back at the end
    of the test, providing a clean database state for subsequent tests.
    """
    with app.app_context():
        # Establish a connection to the in-memory database engine
        connection = db.engine.connect()
        # Begin a transaction on this connection
        transaction = connection.begin()

        # Configure the existing Flask-SQLAlchemy session to use this specific
        # connection for the duration of the test. This ensures all database
        # operations within the test function are part of the same transaction.
        db.session.configure(bind=connection)

        yield db.session

        # Rollback the transaction to undo any changes made during the test.
        # This ensures database isolation between tests.
        transaction.rollback()
        # Close the connection
        connection.close()
        # Remove the session to clean up thread-local resources and ensure
        # a fresh session for the next test.
        db.session.remove()