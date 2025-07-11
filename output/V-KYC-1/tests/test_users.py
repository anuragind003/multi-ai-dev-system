import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from main import app
from database import Base, get_db
from models import User, UserRole
from schemas import UserCreate, UserUpdate, LoginRequest, Token
from middleware.security import get_password_hash, create_access_token
from config import settings
from datetime import timedelta

# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(name="test_engine", scope="session")
def test_engine_fixture():
    """Fixture for the test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    return engine

@pytest.fixture(name="test_session_maker", scope="session")
def test_session_maker_fixture(test_engine):
    """Fixture for the test database session maker."""
    return async_sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

@pytest.fixture(name="setup_db", scope="function", autouse=True)
async def setup_db_fixture(test_engine, test_session_maker):
    """
    Fixture to set up and tear down the database for each test function.
    Creates tables before each test and drops them afterwards.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Override the app's get_db dependency to use the test database
    async def override_get_db():
        async with test_session_maker() as session:
            yield session
    app.dependency_overrides[get_db] = override_get_db
    
    yield # Run the test
    
    # Clean up after the test
    app.dependency_overrides = {} # Clear overrides
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(name="client")
async def client_fixture(setup_db):
    """Fixture for the FastAPI test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# --- Helper Fixtures for Users and Tokens ---

@pytest.fixture
async def create_test_user(test_session_maker):
    """Helper fixture to create a user in the test database."""
    async def _create_user(username: str, email: str, password: str, role: UserRole = UserRole.USER, is_active: bool = True):
        async with test_session_maker() as session:
            hashed_password = get_password_hash(password)
            user = User(
                username=username,
                email=email,
                hashed_password=hashed_password,
                role=role,
                is_active=is_active
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user
    return _create_user

@pytest.fixture
async def admin_user(create_test_user):
    """Fixture for an admin user."""
    return await create_test_user("admin_user", "admin@example.com", "adminpass", UserRole.ADMIN)

@pytest.fixture
async def manager_user(create_test_user):
    """Fixture for a manager user."""
    return await create_test_user("manager_user", "manager@example.com", "managerpass", UserRole.MANAGER)

@pytest.fixture
async def regular_user(create_test_user):
    """Fixture for a regular user."""
    return await create_test_user("regular_user", "user@example.com", "userpass", UserRole.USER)

@pytest.fixture
def get_auth_headers():
    """Helper fixture to generate authorization headers for a given user."""
    def _get_auth_headers(user: User):
        token = create_access_token(
            data={"sub": user.username, "roles": [user.role.value]},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        return {"Authorization": f"Bearer {token}"}
    return _get_auth_headers

# --- Test Cases ---

@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_user: User, get_auth_headers):
    """Test creating a new user as an admin."""
    headers = get_auth_headers(admin_user)
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "securepassword",
        "role": "user",
        "is_active": True
    }
    response = await client.post("/api/v1/users/", json=user_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
    assert response.json()["email"] == "newuser@example.com"
    assert response.json()["role"] == "user"

@pytest.mark.asyncio
async def test_create_manager_as_admin(client: AsyncClient, admin_user: User, get_auth_headers):
    """Test creating a manager user as an admin."""
    headers = get_auth_headers(admin_user)
    user_data = {
        "username": "newmanager",
        "email": "newmanager@example.com",
        "password": "securepassword",
        "role": "manager",
        "is_active": True
    }
    response = await client.post("/api/v1/users/", json=user_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["username"] == "newmanager"
    assert response.json()["role"] == "manager"

@pytest.mark.asyncio
async def test_create_user_as_manager(client: AsyncClient, manager_user: User, get_auth_headers):
    """Test creating a new user as a manager (should be allowed for 'user' role)."""
    headers = get_auth_headers(manager_user)
    user_data = {
        "username": "managercreateduser",
        "email": "mcu@example.com",
        "password": "securepassword",
        "role": "user",
        "is_active": True
    }
    response = await client.post("/api/v1/users/", json=user_data, headers=headers)
    assert response.status_code == 201
    assert response.json()["username"] == "managercreateduser"
    assert response.json()["role"] == "user"

@pytest.mark.asyncio
async def test_create_manager_as_manager_forbidden(client: AsyncClient, manager_user: User, get_auth_headers):
    """Test creating a manager user as a manager (should be forbidden)."""
    headers = get_auth_headers(manager_user)
    user_data = {
        "username": "forbiddenmanager",
        "email": "fm@example.com",
        "password": "securepassword",
        "role": "manager",
        "is_active": True
    }
    response = await client.post("/api/v1/users/", json=user_data, headers=headers)
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

@pytest.mark.asyncio
async def test_create_user_as_regular_user_forbidden(client: AsyncClient, regular_user: User, get_auth_headers):
    """Test creating a new user as a regular user (should be forbidden)."""
    headers = get_auth_headers(regular_user)
    user_data = {
        "username": "regularcreateduser",
        "email": "rcu@example.com",
        "password": "securepassword",
        "role": "user",
        "is_active": True
    }
    response = await client.post("/api/v1/users/", json=user_data, headers=headers)
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, regular_user: User):
    """Test successful user login."""
    login_data = {"username": regular_user.username, "password": "userpass"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    token = Token(**response.json())
    assert token.access_token is not None
    assert token.token_type == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient, regular_user: User):
    """Test login with invalid password."""
    login_data = {"username": regular_user.username, "password": "wrongpass"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, create_test_user):
    """Test login with an inactive user."""
    inactive_user = await create_test_user("inactive_user", "inactive@example.com", "inactivepass", is_active=False)
    login_data = {"username": inactive_user.username, "password": "inactivepass"}
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"] # Service returns generic message for security

@pytest.mark.asyncio
async def test_get_all_users_as_admin(client: AsyncClient, admin_user: User, regular_user: User, get_auth_headers):
    """Test getting all users as an admin."""
    headers = get_auth_headers(admin_user)
    response = await client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 200
    users = response.json()
    assert len(users) >= 2 # admin_user and regular_user
    assert any(u["username"] == admin_user.username for u in users)
    assert any(u["username"] == regular_user.username for u in users)

@pytest.mark.asyncio
async def test_get_all_users_as_regular_user_forbidden(client: AsyncClient, regular_user: User, get_auth_headers):
    """Test getting all users as a regular user (should be forbidden)."""
    headers = get_auth_headers(regular_user)
    response = await client.get("/api/v1/users/", headers=headers)
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_user_by_id_as_admin(client: AsyncClient, admin_user: User, regular_user: User, get_auth_headers):
    """Test getting a specific user by ID as an admin."""
    headers = get_auth_headers(admin_user)
    response = await client.get(f"/api/v1/users/{regular_user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == regular_user.username

@pytest.mark.asyncio
async def test_get_user_by_id_self(client: AsyncClient, regular_user: User, get_auth_headers):
    """Test getting own user profile."""
    headers = get_auth_headers(regular_user)
    response = await client.get(f"/api/v1/users/{regular_user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == regular_user.username

@pytest.mark.asyncio
async def test_get_user_by_id_other_as_regular_user_forbidden(client: AsyncClient, regular_user: User, admin_user: User, get_auth_headers):
    """Test getting another user's profile as a regular user (should be forbidden)."""
    headers = get_auth_headers(regular_user)
    response = await client.get(f"/api/v1/users/{admin_user.id}", headers=headers)
    assert response.status_code == 403
    assert "not authorized" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_user_as_admin(client: AsyncClient, admin_user: User, regular_user: User, get_auth_headers):
    """Test updating a user as an admin."""
    headers = get_auth_headers(admin_user)
    update_data = {"email": "updated_user@example.com", "is_active": False}
    response = await client.put(f"/api/v1/users/{regular_user.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "updated_user@example.com"
    assert response.json()["is_active"] is False

@pytest.mark.asyncio
async def test_update_user_self(client: AsyncClient, regular_user: User, get_auth_headers):
    """Test updating own user profile."""
    headers = get_auth_headers(regular_user)
    update_data = {"username": "updated_self_user", "password": "newsecurepass"}
    response = await client.put(f"/api/v1/users/{regular_user.id}", json=update_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "updated_self_user"
    # Verify password change by trying to log in with new password
    login_data = {"username": "updated_self_user", "password": "newsecurepass"}
    login_response = await client.post("/api/v1/auth/login", json=login_data)
    assert login_response.status_code == 200

@pytest.mark.asyncio
async def test_update_user_role_as_regular_user_forbidden(client: AsyncClient, regular_user: User, get_auth_headers):
    """Test updating own role as a regular user (should be forbidden)."""
    headers = get_auth_headers(regular_user)
    update_data = {"role": "admin"}
    response = await client.put(f"/api/v1/users/{regular_user.id}", json=update_data, headers=headers)
    assert response.status_code == 403
    assert "cannot change your own role" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_user_as_admin(client: AsyncClient, admin_user: User, regular_user: User, get_auth_headers):
    """Test deleting a user as an admin."""
    headers = get_auth_headers(admin_user)
    response = await client.delete(f"/api/v1/users/{regular_user.id}", headers=headers)
    assert response.status_code == 204
    # Verify user is deleted
    get_response = await client.get(f"/api/v1/users/{regular_user.id}", headers=headers)
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_user_self_forbidden(client: AsyncClient, admin_user: User, get_auth_headers):
    """Test deleting own account as an admin (should be forbidden)."""
    headers = get_auth_headers(admin_user)
    response = await client.delete(f"/api/v1/users/{admin_user.id}", headers=headers)
    assert response.status_code == 403
    assert "cannot delete your own account" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_user_as_regular_user_forbidden(client: AsyncClient, regular_user: User, admin_user: User, get_auth_headers):
    """Test deleting a user as a regular user (should be forbidden)."""
    headers = get_auth_headers(regular_user)
    response = await client.delete(f"/api/v1/users/{admin_user.id}", headers=headers)
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "Database connection OK" in response.json()["message"]