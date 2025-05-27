import pytest
import asyncio
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from alembic.config import Config
from alembic import command
import os

# Import the FastAPI app and database components from your application
# Assuming your main FastAPI app instance is in `app/main.py`
# and your database engine/session/get_db function are in `app/database.py`
from app.main import app
from app.database import get_db

# --- Test Database Configuration ---
# Use a separate test database URL.
# It's crucial that this points to a database that can be safely dropped and recreated.
# For local development, ensure a PostgreSQL server is running and you have appropriate permissions.
# It's highly recommended to use environment variables for these credentials in a real project.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/test_cdp_db")
# For synchronous operations (like creating/dropping DB and Alembic migrations), use a sync URL
TEST_DATABASE_SYNC_URL = os.getenv("TEST_DATABASE_SYNC_URL", "postgresql://postgres:postgres@localhost:5432/test_cdp_db")
# URL for connecting to the default 'postgres' database to manage test_cdp_db
POSTGRES_ROOT_URL = os.getenv("POSTGRES_ROOT_URL", "postgresql://postgres:postgres@localhost:5432/postgres")

# --- Alembic Configuration for Tests ---
# Point Alembic to the correct alembic.ini and script location
ALEMBIC_CONFIG_PATH = "alembic.ini"  # Path to your alembic.ini file
ALEMBIC_SCRIPT_LOCATION = "alembic"  # Path to your alembic versions directory

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db_and_migrations():
    """
    Fixture to set up and tear down the test database, including running Alembic migrations.
    This runs once per test session.
    """
    # Use a synchronous engine for creating/dropping databases
    sync_engine = create_engine(POSTGRES_ROOT_URL)
    test_db_name = TEST_DATABASE_URL.split('/')[-1].split('?')[0] # Extract db name from URL

    # 1. Drop and Create Test Database
    with sync_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        # Terminate all connections to the test database before dropping
        # This is crucial to avoid "database is being accessed by other users" errors
        connection.execute(text(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{test_db_name}' AND pid <> pg_backend_pid();"))
        connection.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        connection.execute(text(f"CREATE DATABASE {test_db_name}"))
        connection.commit() # Ensure changes are committed

    # 2. Run Alembic Migrations
    alembic_cfg = Config(ALEMBIC_CONFIG_PATH)
    # Set the target database for Alembic to the test database
    alembic_cfg.set_main_option("sqlalchemy.url", TEST_DATABASE_SYNC_URL)
    alembic_cfg.set_main_option("script_location", ALEMBIC_SCRIPT_LOCATION)

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        print(f"Alembic migration failed during setup: {e}")
        raise

    yield # All tests run here

    # 3. Teardown: Drop the test database after all tests are done
    with sync_engine.connect() as connection:
        connection.execution_options(isolation_level="AUTOCOMMIT")
        connection.execute(text(f"SELECT pg_terminate_backend(pg_stat_activity.pid) FROM pg_stat_activity WHERE pg_stat_activity.datname = '{test_db_name}' AND pid <> pg_backend_pid();"))
        connection.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        connection.commit()
    sync_engine.dispose()


@pytest.fixture(scope="function")
async def db_session(setup_test_db_and_migrations):
    """
    Fixture that provides a clean database session for each test function.
    It uses the test database and rolls back transactions after each test
    to ensure a clean state for the next test.
    """
    # Create a new async engine for the test database for each function
    # Using NullPool to ensure connections are not reused across tests in a way that might cause issues
    test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    TestAsyncSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestAsyncSessionLocal() as session:
        # Begin a transaction for the test. All operations within the test
        # will be part of this transaction.
        await session.begin()
        yield session
        # Rollback the transaction after the test. This discards all changes
        # made by the test, ensuring a clean state for the next test function.
        await session.rollback()
    # Dispose of the engine after the session is closed to clean up connections
    await test_engine.dispose()


@pytest.fixture(scope="function")
async def test_app(db_session):
    """
    Fixture that provides a FastAPI test app instance with overridden database dependency.
    The app will use the `db_session` fixture for its database interactions.
    """
    # Override the get_db dependency to use the test database session provided by db_session fixture
    app.dependency_overrides[get_db] = lambda: db_session
    yield app
    # Clear overrides after the test function completes to restore original dependencies
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def client(test_app):
    """
    Fixture that provides an httpx test client for making requests to the FastAPI app.
    This client allows making asynchronous HTTP requests directly to the FastAPI application
    without needing a running server.
    """
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as ac:
        yield ac