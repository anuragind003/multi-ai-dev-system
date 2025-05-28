import pytest
from src.app import create_app
from src.database import db as _db  # Assuming src/database.py exports the SQLAlchemy db instance
from sqlalchemy import event

@pytest.fixture(scope='session')
def app():
    """
    Fixture for creating and configuring a Flask application instance for testing.
    Uses a dedicated test database.
    """
    app = create_app(testing=True)
    app.config.update({
        "TESTING": True,
        # Use a dedicated test PostgreSQL database.
        # For CI/CD, this might point to a Dockerized PostgreSQL instance.
        # For local development, ensure this DB exists and is accessible.
        "SQLALCHEMY_DATABASE_URI": "postgresql://testuser:testpassword@localhost:5432/test_cdp_db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    # Establish an application context before yielding the app
    with app.app_context():
        yield app

@pytest.fixture(scope='session')
def db(app):
    """
    Fixture to set up and tear down the database for the test session.
    Creates all tables before tests and drops them after.
    """
    _db.create_all()
    yield _db
    _db.drop_all()

@pytest.fixture(scope='function')
def session(db):
    """
    Provides a clean database session for each test function.
    Uses a transaction that is rolled back after each test to ensure isolation.
    """
    connection = db.engine.connect()
    transaction = connection.begin()

    # Bind the session to the connection
    options = dict(bind=connection, binds={})
    # Create a new session bound to the connection for the test
    test_session = db.create_scoped_session(options=options)

    # Replace the default session with our test session for the duration of the test
    # This ensures that `db.session` within test code refers to `test_session`
    db.session = test_session

    # This listener is crucial for tests that might implicitly commit or use nested transactions
    # It ensures the session is refreshed and a new savepoint is created if needed
    @event.listens_for(test_session, 'after_transaction_end')
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction.parent.in_progress:
            session.expire_all()
            session.begin_nested()

    yield test_session

    # Rollback the transaction and close the connection after each test
    transaction.rollback()
    connection.close()
    test_session.remove() # Removes the session from the registry

@pytest.fixture(scope='function')
def client(app, session): # Depend on session to ensure DB is ready and session is active
    """
    Fixture for a test client.
    """
    return app.test_client()

@pytest.fixture(scope='function')
def runner(app):
    """
    Fixture for a test CLI runner.
    """
    return app.test_cli_runner()