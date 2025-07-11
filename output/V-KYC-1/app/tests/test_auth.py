import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.core.security import get_password_hash
from app.core.config import settings

# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./test.db" # Use a file-based SQLite for better isolation

# Create a test engine and session
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=sessionmaker,
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

@pytest.fixture(name="db_session")
async def db_session_fixture():
    """
    Fixture to provide a clean database session for each test.
    Creates tables before tests, drops them after.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        await db.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(name="client")
async def client_fixture(db_session: AsyncSession):
    """
    Fixture to provide an AsyncClient for testing FastAPI endpoints.
    Overrides the get_db dependency to use the test database.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
    app.dependency_overrides = {} # Clear overrides after test

@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "password123"
    }
    response = await client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert data["is_active"] is True
    assert data["is_admin"] is False

@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient):
    """Test registration with a duplicate username."""
    user_data = {
        "username": "duplicateuser",
        "email": "duplicate@example.com",
        "password": "password123"
    }
    await client.post("/api/v1/auth/register", json=user_data) # First registration
    response = await client.post("/api/v1/auth/register", json=user_data) # Second registration
    assert response.status_code == 409
    assert "Username already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test registration with a duplicate email."""
    user_data_1 = {
        "username": "user1",
        "email": "duplicate_email@example.com",
        "password": "password123"
    }
    user_data_2 = {
        "username": "user2",
        "email": "duplicate_email@example.com",
        "password": "password123"
    }
    await client.post("/api/v1/auth/register", json=user_data_1)
    response = await client.post("/api/v1/auth/register", json=user_data_2)
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_for_access_token(client: AsyncClient, db_session: AsyncSession):
    """Test successful user login."""
    hashed_password = get_password_hash("securepassword")
    user = User(username="loginuser", email="login@example.com", hashed_password=hashed_password)
    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "loginuser", "password": "securepassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid password."""
    response = await client.post(
        "/api/v1/auth/token",
        data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me(client: AsyncClient, db_session: AsyncSession):
    """Test retrieving current user details with a valid token."""
    hashed_password = get_password_hash("securepassword")
    user = User(username="currentuser", email="current@example.com", hashed_password=hashed_password)
    db_session.add(user)
    await db_session.commit()

    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "currentuser", "password": "securepassword"}
    )
    token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "currentuser"
    assert data["email"] == "current@example.com"

@pytest.mark.asyncio
async def test_read_users_me_unauthorized(client: AsyncClient):
    """Test retrieving current user details without a token."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_read_users_me_invalid_token(client: AsyncClient):
    """Test retrieving current user details with an invalid token."""
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401
    assert "Could not validate credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_admin_access_denied_for_non_admin(client: AsyncClient, db_session: AsyncSession):
    """
    Test that a non-admin user cannot access an admin-only endpoint.
    (This requires an admin-only endpoint to be defined, which is not yet in the provided code.
    For demonstration, we'll simulate by trying to access a hypothetical admin endpoint.)
    """
    # Create a regular user
    hashed_password = get_password_hash("regularpass")
    user = User(username="regularuser", email="regular@example.com", hashed_password=hashed_password, is_admin=False)
    db_session.add(user)
    await db_session.commit()

    # Log in as regular user
    login_response = await client.post(
        "/api/v1/auth/token",
        data={"username": "regularuser", "password": "regularpass"}
    )
    token = login_response.json()["access_token"]

    # Simulate an admin-only endpoint by directly calling get_current_admin_user dependency
    # In a real scenario, this would be an actual API endpoint like /api/v1/admin/users
    from app.dependencies import get_current_admin_user
    from fastapi import HTTPException
    
    # Temporarily override the dependency to test the admin check logic
    async def mock_get_current_user():
        return user # Return the non-admin user

    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        # This will raise PermissionDeniedException, which FastAPI converts to HTTPException
        await get_current_admin_user(user)
        pytest.fail("Non-admin user unexpectedly granted admin access.")
    except HTTPException as e:
        assert e.status_code == 403
        assert e.detail == "Permission denied"
    finally:
        app.dependency_overrides = {} # Clean up override