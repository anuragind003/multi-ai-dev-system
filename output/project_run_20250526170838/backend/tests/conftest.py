import pytest
from flask import Flask
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import uuid

# Define the database connection parameters for the test environment
# These should ideally come from environment variables or a test-specific config.
# For local testing, assuming a default 'postgres' user with no password.
TEST_DB_USER = os.getenv("POSTGRES_USER", "postgres")
TEST_DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
TEST_DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
TEST_DB_PORT = os.getenv("POSTGRES_PORT", "5432")
BASE_DB_NAME = "postgres" # Default database to connect to for creating/dropping test dbs

# Database schema DDL from project context
# Note: Primary keys and foreign keys are TEXT for UUIDs as per design notes.
DB_SCHEMA_DDL = """
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    mobile_number TEXT UNIQUE,
    pan_number TEXT UNIQUE,
    aadhaar_number TEXT UNIQUE,
    ucid_number TEXT UNIQUE,
    loan_application_number TEXT UNIQUE,
    dnd_flag BOOLEAN DEFAULT FALSE,
    segment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE offers (
    offer_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    offer_type TEXT, -- 'Fresh', 'Enrich', 'New-old', 'New-new'
    offer_status TEXT, -- 'Active', 'Inactive', 'Expired'
    propensity TEXT,
    start_date DATE,
    end_date DATE,
    channel TEXT, -- For attribution logic
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(customer_id),
    event_type TEXT, -- 'SMS_SENT', 'SMS_DELIVERED', 'EKYC_ACHIEVED', 'LOAN_LOGIN', etc.
    event_source TEXT, -- 'Moengage', 'LOS', 'E-aggregator'
    event_timestamp TIMESTAMP,
    event_details JSONB, -- Flexible storage for event-specific data
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE campaign_metrics (
    metric_id TEXT PRIMARY KEY,
    campaign_unique_id TEXT UNIQUE NOT NULL,
    campaign_name TEXT,
    campaign_date DATE,
    attempted_count INTEGER,
    sent_success_count INTEGER,
    failed_count INTEGER,
    conversion_rate NUMERIC(5,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ingestion_logs (
    log_id TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    upload_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT, -- 'SUCCESS', 'FAILED'
    error_description TEXT
);
"""


@pytest.fixture(scope="session")
def db_engine():
    """
    Fixture for creating a SQLAlchemy engine connected to a temporary test database.
    This database is created once per test session and dropped afterwards.
    """
    test_db_name = f"test_cdp_db_{uuid.uuid4().hex}"
    base_db_uri = (
        f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:"
        f"{TEST_DB_PORT}/{BASE_DB_NAME}"
    )
    test_db_uri = (
        f"postgresql://{TEST_DB_USER}:{TEST_DB_PASSWORD}@{TEST_DB_HOST}:"
        f"{TEST_DB_PORT}/{test_db_name}"
    )

    # Connect to the base database to create the new test database
    # Use AUTOCOMMIT isolation level for DDL operations like CREATE/DROP DATABASE
    engine_base = create_engine(base_db_uri, isolation_level="AUTOCOMMIT")
    with engine_base.connect() as conn:
        # Terminate existing connections to the test database if it somehow exists
        # This is a safety measure, especially if a previous test run crashed
        conn.execute(
            text(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity WHERE pg_stat_activity.datname = "
                f"'{test_db_name}';"
            )
        )
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name};"))
        conn.execute(text(f"CREATE DATABASE {test_db_name};"))
    engine_base.dispose() # Close the connection to the base database

    # Connect to the newly created test database and create tables
    engine = create_engine(test_db_uri)
    with engine.connect() as conn:
        # Execute DDL statements
        for statement in DB_SCHEMA_DDL.split(';'):
            stripped_statement = statement.strip()
            if stripped_statement:
                conn.execute(text(stripped_statement))
        conn.commit() # Commit DDL changes
    
    yield engine

    # Teardown: Drop the test database
    engine.dispose() # Ensure all connections to the test database are closed
    engine_base = create_engine(base_db_uri, isolation_level="AUTOCOMMIT")
    with engine_base.connect() as conn:
        # Terminate any remaining connections to the test database before dropping
        conn.execute(
            text(
                f"SELECT pg_terminate_backend(pg_stat_activity.pid) "
                f"FROM pg_stat_activity WHERE pg_stat_activity.datname = "
                f"'{test_db_name}';"
            )
        )
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name};"))
    engine_base.dispose()


@pytest.fixture(scope="session")
def app(db_engine):
    """
    Fixture for creating and configuring a Flask app instance for testing.
    Scoped to 'session' so it's created once per test session.
    It configures the app to use the test database provided by `db_engine`.
    """
    app = Flask(__name__)
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": str(db_engine.url), # Set the test DB URI
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    # If your main application uses a global SQLAlchemy 'db' object
    # (e.g., from Flask-SQLAlchemy or a custom setup), you might need to
    # initialize or re-bind it here for the test app instance.
    # Example:
    # from backend.app import db as main_app_db_object
    # main_app_db_object.init_app(app)
    # app.app_context().push() # Push an application context if needed for setup

    yield app


@pytest.fixture(scope="function")
def db_session(app, db_engine):
    """
    Fixture for providing a database session for each test function.
    Each test runs within a transaction, which is rolled back at the end
    to ensure a clean state for the next test.
    """
    # Use the engine from the session-scoped fixture
    connection = db_engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to the connection
    Session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=connection))
    session = Session()

    # Make the session available to the Flask app context for the duration of the test
    # This assumes your Flask routes/services will access the session via `current_app.db_session`
    # or a similar mechanism.
    with app.app_context():
        app.db_session = session
        yield session

    # Teardown: Rollback the transaction and close the session
    session.close()
    transaction.rollback() # Rollback all changes made during the test
    connection.close()
    
    # Clean up the session from the app context
    with app.app_context():
        if hasattr(app, 'db_session'):
            del app.db_session


@pytest.fixture(scope="function")
def client(app, db_session):
    """
    Fixture for providing a Flask test client.
    It ensures an application context is active and the test database session
    is available for the app during the test.
    """
    with app.test_client() as client:
        yield client