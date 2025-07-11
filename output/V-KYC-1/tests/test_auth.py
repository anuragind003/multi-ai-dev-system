import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from main import app
from database import get_db, engine, Base, AsyncSessionLocal
from models import User, UserRole
from security import get_password_hash
from schemas import UserCreate, UserLogin

# Override the get_db dependency for testing
@pytest.fixture(name="test_db")
async def test_db_fixture():
    """
    Provides a clean, independent database session for each test.
    Uses an in-memory SQLite for speed, or a separate test PostgreSQL DB.
    """
    # Use a separate test database URL if needed, or an in-memory SQLite for unit tests
    # For a real PostgreSQL test, you'd configure a test_db_url in config.py
    # and ensure it's a fresh database for each test run.
    # For simplicity, we'll use an in-memory SQLite for these basic tests.
    # For asyncpg, we need a real DB, so we'll use the configured one but ensure cleanup.
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()
        # Clean up after tests (optional, but good for isolation)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


# Override the get_db dependency in the FastAPI app
app.dependency_overrides[get_db] = test_db_fixture

@pytest.mark.asyncio
async def test_register_user_success(test_db: AsyncSession):
    """Test successful user registration."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        user_data = UserCreate(username="testuser", password="securepassword", role=UserRole.VIEWER)
        response = await ac.post("/api/v1/auth/register", json=user_data.model_dump())

    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
    assert response.json()["role"] == "viewer"
    assert "id" in response.json()
    assert "hashed_password" not in response.json() # Ensure password is not returned

    # Verify user exists in DB
    user_in_db = await test_db.execute(text("SELECT username FROM users WHERE username = 'testuser'"))
    assert user_in_db.scalar_one_or_none() == "testuser"

@pytest.mark.asyncio
async def test_register_user_duplicate(test_db: AsyncSession):
    """Test registration with a duplicate username."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # First registration
        user_data = UserCreate(username="duplicateuser", password="password123", role=UserRole.VIEWER)
        await ac.post("/api/v1/auth/register", json=user_data.model_dump())

        # Second registration with same username
        response = await ac.post("/api/v1/auth/register", json=user_data.model_dump())

    assert response.status_code == 409
    assert response.json()["detail"] == "Conflict"
    assert "already exists" in response.json()["message"]

@pytest.mark.asyncio
async def test_login_success(test_db: AsyncSession):
    """Test successful user login and token generation."""
    # Register a user first
    hashed_password = get_password_hash("securepassword")
    new_user = User(username="loginuser", hashed_password=hashed_password, role=UserRole.AUDITOR)
    test_db.add(new_user)
    await test_db.commit()
    await test_db.refresh(new_user)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        login_data = UserLogin(username="loginuser", password="securepassword")
        response = await ac.post("/api/v1/auth/token", json=login_data.model_dump())

    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(test_db: AsyncSession):
    """Test login with incorrect password."""
    # Register a user first
    hashed_password = get_password_hash("correctpassword")
    new_user = User(username="invalidloginuser", hashed_password=hashed_password, role=UserRole.VIEWER)
    test_db.add(new_user)
    await test_db.commit()
    await test_db.refresh(new_user)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        login_data = UserLogin(username="invalidloginuser", password="wrongpassword")
        response = await ac.post("/api/v1/auth/token", json=login_data.model_dump())

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
    assert "Incorrect username or password" in response.json()["message"]

@pytest.mark.asyncio
async def test_login_user_not_found(test_db: AsyncSession):
    """Test login with a non-existent username."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        login_data = UserLogin(username="nonexistentuser", password="anypassword")
        response = await ac.post("/api/v1/auth/token", json=login_data.model_dump())

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
    assert "Incorrect username or password" in response.json()["message"]

@pytest.mark.asyncio
async def test_login_inactive_user(test_db: AsyncSession):
    """Test login with an inactive user."""
    # Register an inactive user
    hashed_password = get_password_hash("activepassword")
    inactive_user = User(username="inactiveuser", hashed_password=hashed_password, role=UserRole.VIEWER, is_active=False)
    test_db.add(inactive_user)
    await test_db.commit()
    await test_db.refresh(inactive_user)

    async with AsyncClient(app=app, base_url="http://test") as ac:
        login_data = UserLogin(username="inactiveuser", password="activepassword")
        response = await ac.post("/api/v1/auth/token", json=login_data.model_dump())

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"
    assert "Inactive user" in response.json()["message"]