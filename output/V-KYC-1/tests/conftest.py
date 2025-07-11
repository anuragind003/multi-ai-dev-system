import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from main import app
from database import Base, get_db
from config import settings
from models import User, UserRole
from auth.security import get_password_hash
from services.user_service import UserService

# Override DATABASE_URL for tests to use an in-memory SQLite database
# This ensures tests are isolated and don't affect the development database.
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
async def test_engine():
    """Fixture for a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture(scope="function")
async def test_db(test_engine):
    """Fixture for a test database session, yielding a fresh session for each test."""
    AsyncSessionLocal = async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    async with AsyncSessionLocal() as session:
        yield session
        # Rollback all changes after each test to ensure isolation
        await session.rollback()

@pytest.fixture(scope="function")
async def client(test_db):
    """Fixture for an asynchronous test client, overriding the database dependency."""
    async def override_get_db():
        yield test_db
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear() # Clear overrides after tests

@pytest.fixture(scope="function")
async def create_test_user(test_db: AsyncSession):
    """Fixture to create a test user for authentication."""
    async def _create_user(username: str, password: str, role: UserRole = UserRole.AUDITOR):
        hashed_password = get_password_hash(password)
        user = User(
            username=username,
            hashed_password=hashed_password,
            email=f"{username}@example.com",
            role=role,
            is_active=True
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)
        return user
    return _create_user

@pytest.fixture(scope="function")
async def get_auth_token(client: AsyncClient, create_test_user):
    """Fixture to get an authentication token for a given user."""
    async def _get_token(username: str, password: str, role: UserRole = UserRole.AUDITOR):
        await create_test_user(username, password, role)
        response = await client.post(
            "/api/v1/users/login",
            json={"username": username, "password": password}
        )
        assert response.status_code == 200
        return response.json()["access_token"]
    return _get_token

@pytest.fixture(scope="function")
async def admin_token(get_auth_token):
    """Fixture for an admin user's authentication token."""
    return await get_auth_token("admin_test", "adminpass", UserRole.ADMIN)

@pytest.fixture(scope="function")
async def manager_token(get_auth_token):
    """Fixture for a manager user's authentication token."""
    return await get_auth_token("manager_test", "managerpass", UserRole.MANAGER)

@pytest.fixture(scope="function")
async def auditor_token(get_auth_token):
    """Fixture for an auditor user's authentication token."""
    return await get_auth_token("auditor_test", "auditorpass", UserRole.AUDITOR)