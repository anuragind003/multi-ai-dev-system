import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool # Use NullPool for tests to prevent connection issues

from main import app
from database import Base, get_db_session
from config import settings
from models import User, UserRole
from security import get_password_hash

# Use a separate test database URL
TEST_DATABASE_URL = settings.ASYNC_DATABASE_URL.replace("security_testing_db", "security_testing_test_db")

# Setup test database engine and session
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool # Important for tests to avoid connection issues across test functions
)
TestAsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Fixture to set up and tear down the test database for the entire test session.
    Creates tables before tests, drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Ensure clean slate
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session():
    """
    Fixture to provide a fresh database session for each test function.
    Rolls back transactions after each test to ensure isolation.
    """
    async with TestAsyncSessionLocal() as session:
        yield session
        await session.rollback() # Rollback changes after each test

@pytest.fixture(scope="function")
async def client(db_session):
    """
    Fixture to provide an AsyncClient for testing FastAPI endpoints.
    Overrides the get_db_session dependency to use the test database session.
    """
    def override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def test_user(db_session: AsyncSession):
    """Fixture to create and return a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=get_password_hash("TestPassword123!"),
        full_name="Test User",
        role=UserRole.TESTER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
async def admin_user(db_session: AsyncSession):
    """Fixture to create and return an admin user."""
    user = User(
        username="adminuser",
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
async def viewer_user(db_session: AsyncSession):
    """Fixture to create and return a viewer user."""
    user = User(
        username="vieweruser",
        email="viewer@example.com",
        hashed_password=get_password_hash("ViewerPassword123!"),
        full_name="Viewer User",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
async def test_user_token(client: AsyncClient):
    """Fixture to get an access token for the test user."""
    response = await client.post(
        "/auth/token",
        data={"username": "testuser", "password": "TestPassword123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(scope="function")
async def admin_user_token(client: AsyncClient):
    """Fixture to get an access token for the admin user."""
    response = await client.post(
        "/auth/token",
        data={"username": "adminuser", "password": "AdminPassword123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture(scope="function")
async def viewer_user_token(client: AsyncClient):
    """Fixture to get an access token for the viewer user."""
    response = await client.post(
        "/auth/token",
        data={"username": "vieweruser", "password": "ViewerPassword123!"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]