import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import or_
from datetime import datetime, timedelta, timezone

from services.auth_service import AuthService
from schemas import UserCreate, UserLogin, Token
from models import User, UserRole
from core.exceptions import CustomHTTPException
from security.dependencies import get_password_hash, verify_password
from config import settings

# Mock the database session
@pytest.fixture
def mock_db_session():
    """Provides a mock AsyncSession for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalars.return_value = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = None
    session.execute.return_value.scalar_one.return_value = 0
    return session

@pytest.fixture
def auth_service(mock_db_session):
    """Provides an AuthService instance with a mocked database session."""
    return AuthService(mock_db_session)

# Test data
TEST_USERNAME = "testuser"
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "securepassword123"
TEST_HASHED_PASSWORD = get_password_hash(TEST_PASSWORD)

@pytest.mark.asyncio
async def test_register_user_success(auth_service, mock_db_session):
    """Test successful user registration."""
    user_create = UserCreate(
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        password=TEST_PASSWORD,
        role=UserRole.VIEWER
    )

    # Mock the refresh method to populate the user object after commit
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', 1) or setattr(obj, 'created_at', datetime.now()) or setattr(obj, 'updated_at', None)

    registered_user = await auth_service.register_user(user_create)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

    assert registered_user.username == TEST_USERNAME
    assert registered_user.email == TEST_EMAIL
    assert registered_user.role == UserRole.VIEWER
    assert registered_user.id == 1
    assert verify_password(TEST_PASSWORD, auth_service.db.add.call_args[0][0].hashed_password)

@pytest.mark.asyncio
async def test_register_user_duplicate_username(auth_service, mock_db_session):
    """Test registration with a duplicate username."""
    user_create = UserCreate(
        username=TEST_USERNAME,
        email="another@example.com",
        password=TEST_PASSWORD
    )
    # Mock that a user with the same username already exists
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = User(
        username=TEST_USERNAME, email="existing@example.com", hashed_password="abc"
    )

    with pytest.raises(CustomHTTPException) as exc_info:
        await auth_service.register_user(user_create)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Username or email already registered."
    assert exc_info.value.code == "USER_ALREADY_EXISTS"
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service, mock_db_session):
    """Test successful user authentication."""
    user_login = UserLogin(username=TEST_USERNAME, password=TEST_PASSWORD)
    
    # Mock that the user exists and password is correct
    mock_user = User(
        id=1,
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        hashed_password=TEST_HASHED_PASSWORD,
        role=UserRole.VIEWER,
        is_active=True
    )
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user

    authenticated_user = await auth_service.authenticate_user(user_login)

    assert authenticated_user.username == TEST_USERNAME
    assert authenticated_user.email == TEST_EMAIL

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(auth_service, mock_db_session):
    """Test authentication with an invalid password."""
    user_login = UserLogin(username=TEST_USERNAME, password="wrongpassword")
    
    mock_user = User(
        id=1,
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        hashed_password=TEST_HASHED_PASSWORD,
        role=UserRole.VIEWER,
        is_active=True
    )
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user

    with pytest.raises(CustomHTTPException) as exc_info:
        await auth_service.authenticate_user(user_login)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect username or password."
    assert exc_info.value.code == "INVALID_CREDENTIALS"

@pytest.mark.asyncio
async def test_authenticate_user_not_found(auth_service, mock_db_session):
    """Test authentication for a non-existent user."""
    user_login = UserLogin(username="nonexistent", password=TEST_PASSWORD)
    
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None

    with pytest.raises(CustomHTTPException) as exc_info:
        await auth_service.authenticate_user(user_login)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Incorrect username or password."
    assert exc_info.value.code == "INVALID_CREDENTIALS"

@pytest.mark.asyncio
async def test_authenticate_user_inactive(auth_service, mock_db_session):
    """Test authentication for an inactive user."""
    user_login = UserLogin(username=TEST_USERNAME, password=TEST_PASSWORD)
    
    mock_user = User(
        id=1,
        username=TEST_USERNAME,
        email=TEST_EMAIL,
        hashed_password=TEST_HASHED_PASSWORD,
        role=UserRole.VIEWER,
        is_active=False # User is inactive
    )
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = mock_user

    with pytest.raises(CustomHTTPException) as exc_info:
        await auth_service.authenticate_user(user_login)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "User account is inactive."
    assert exc_info.value.code == "USER_INACTIVE"

def test_create_access_token(auth_service):
    """Test JWT token creation."""
    data = {"sub": TEST_USERNAME, "roles": [UserRole.ADMIN.value]}
    token_obj = auth_service.create_access_token(data)

    assert isinstance(token_obj, Token)
    assert token_obj.token_type == "bearer"
    assert token_obj.access_token is not None

    # Decode and verify the token
    decoded_payload = jwt.decode(token_obj.access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded_payload["sub"] == TEST_USERNAME
    assert decoded_payload["roles"] == [UserRole.ADMIN.value]
    assert "exp" in decoded_payload
    
    # Check expiration time (should be roughly ACCESS_TOKEN_EXPIRE_MINUTES from now)
    expiration_time = datetime.fromtimestamp(decoded_payload["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert now < expiration_time
    assert (expiration_time - now) <= timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) + timedelta(seconds=1) # Allow for slight time difference