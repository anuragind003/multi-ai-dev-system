import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.user import User
from app.core.security import get_password_hash

# Override database settings for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Setup a test database engine and session
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False # Set to True to see SQL queries in tests
)
TestingSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession,
)

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Fixture to set up and tear down the test database.
    Creates tables before tests, drops them after.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def override_get_db():
    """
    Fixture to override the get_db dependency for tests.
    Provides a fresh session for each test function.
    """
    async with TestingSessionLocal() as session:
        yield session
        # Clean up data after each test
        await session.rollback() # Rollback any changes made during the test
        # Or, if you want to clear specific tables:
        # await session.execute(delete(User))
        # await session.commit()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
async def client():
    """
    Fixture to provide an asynchronous test client for FastAPI.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.mark.asyncio
async def test_create_user(client: AsyncClient):
    """
    Test user creation endpoint.
    """
    user_data = {"email": "test@example.com", "password": "password123"}
    response = await client.post(f"{settings.API_V1_STR}/users", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert data["is_active"] is True
    assert "created_at" in data

@pytest.mark.asyncio
async def test_create_existing_user(client: AsyncClient):
    """
    Test creating a user with an email that already exists.
    """
    user_data = {"email": "existing@example.com", "password": "password123"}
    await client.post(f"{settings.API_V1_STR}/users", json=user_data) # Create first user

    response = await client.post(f"{settings.API_V1_STR}/users", json=user_data) # Try to create again
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient):
    """
    Test user login and token generation.
    """
    user_data = {"email": "login@example.com", "password": "securepassword"}
    await client.post(f"{settings.API_V1_STR}/users", json=user_data) # Create user first

    form_data = {"username": "login@example.com", "password": "securepassword"}
    response = await client.post(f"{settings.API_V1_STR}/token", data=form_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """
    Test login with incorrect password.
    """
    user_data = {"email": "invalidlogin@example.com", "password": "correctpassword"}
    await client.post(f"{settings.API_V1_STR}/users", json=user_data)

    form_data = {"username": "invalidlogin@example.com", "password": "wrongpassword"}
    response = await client.post(f"{settings.API_V1_STR}/token", data=form_data)

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient):
    """
    Test getting current user's profile.
    """
    user_data = {"email": "me@example.com", "password": "mypassword"}
    await client.post(f"{settings.API_V1_STR}/users", json=user_data)

    form_data = {"username": "me@example.com", "password": "mypassword"}
    token_response = await client.post(f"{settings.API_V1_STR}/token", data=form_data)
    token = token_response.json()["access_token"]

    response = await client.get(
        f"{settings.API_V1_STR}/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "id" in data

@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    """
    Test getting current user's profile without token.
    """
    response = await client.get(f"{settings.API_V1_STR}/users/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"

@pytest.mark.asyncio
async def test_read_all_users(client: AsyncClient):
    """
    Test getting all users (assuming any authenticated user can do this for now).
    """
    user1_data = {"email": "user1@example.com", "password": "password1"}
    user2_data = {"email": "user2@example.com", "password": "password2"}
    await client.post(f"{settings.API_V1_STR}/users", json=user1_data)
    await client.post(f"{settings.API_V1_STR}/users", json=user2_data)

    form_data = {"username": "user1@example.com", "password": "password1"}
    token_response = await client.post(f"{settings.API_V1_STR}/token", data=form_data)
    token = token_response.json()["access_token"]

    response = await client.get(
        f"{settings.API_V1_STR}/users",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2 # At least the two users we created, plus any from other tests
    assert any(u["email"] == "user1@example.com" for u in data)
    assert any(u["email"] == "user2@example.com" for u in data)

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """
    Test the health check endpoint.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data