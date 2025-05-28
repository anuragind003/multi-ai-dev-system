import pytest
from backend import create_app, db
# It's crucial to import your models so SQLAlchemy knows about them
# when creating tables. Assuming models are defined in `backend/models.py`.
from backend.models import Customer, Offer, OfferHistory, Event, Campaign


@pytest.fixture(scope='session')
def app():
    """
    Fixture for creating a test Flask application instance.
    Configures the app for testing and uses a separate test database.
    """
    app = create_app()
    app.config.update({
        "TESTING": True,
        # Use a separate test database for isolation.
        # Ensure this database ('cdp_test_db') exists and is accessible
        # with the specified user/password.
        "SQLALCHEMY_DATABASE_URI": "postgresql://cdp_user:cdp_password@localhost:5432/cdp_test_db",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SECRET_KEY": "test_secret_key_for_cdp_tests"  # A simple key for tests
    })

    # Establish an application context for the session scope.
    # This is necessary for SQLAlchemy operations like create_all/drop_all.
    with app.app_context():
        # Create all tables for the test database before any tests run.
        db.create_all()
        yield app
        # Drop all tables after the session tests are done to clean up.
        db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    """
    Fixture for a test client.
    Provides a way to make requests to the Flask application in tests.
    """
    # Push an application context for the function scope to ensure
    # the client operates within the app's context.
    with app.app_context():
        yield app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    """
    Fixture for a test CLI runner.
    Provides a way to invoke Flask CLI commands in tests.
    """
    # Push an application context for the function scope.
    with app.app_context():
        yield app.test_cli_runner()


@pytest.fixture(scope='function')
def session(app):
    """
    Provides a database session for each test, ensuring a clean state
    by rolling back the transaction after each test.
    """
    with app.app_context():
        # Begin a nested transaction (savepoint) for the test.
        # This allows rolling back changes made during the test without
        # affecting the overall database state (which is managed by the
        # session-scoped app fixture's create_all/drop_all).
        transaction = db.session.begin_nested()

        yield db.session

        # Rollback the nested transaction after the test completes.
        transaction.rollback()
        # Remove the session from the registry to ensure a fresh session
        # for the next test. Flask-SQLAlchemy often handles this at the
        # end of a request context, but explicit removal is safer for tests.
        db.session.remove()