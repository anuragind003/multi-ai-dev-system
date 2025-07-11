import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from services.user_service import UserService
from schemas.user_schema import UserCreate
from models.user_model import User
from core.exceptions import UserAlreadyExistsException, InvalidCredentialsException
from core.security import get_password_hash, verify_password

# Mock the database session for testing
@pytest.fixture
def mock_db_session():
    """Provides a mock AsyncSession for testing."""
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalars.return_value = MagicMock()
    session.execute.return_value.scalars.return_value.first.return_value = None
    session.add.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None
    session.rollback.return_value = None
    return session

@pytest.fixture
def user_service(mock_db_session):
    """Provides a UserService instance with a mocked DB session."""
    return UserService(mock_db_session)

@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_db_session):
    """Test successful user creation."""
    user_create = UserCreate(email="test@example.com", password="password123")
    
    # Mock get_any_user_exists to return False (first user)
    user_service.get_any_user_exists = AsyncMock(return_value=False)

    # Mock the return value of the user after refresh
    mock_db_session.refresh.side_effect = lambda user: setattr(user, 'id', 1)

    user = await user_service.create_user(user_create)

    assert user.email == user_create.email
    assert user.is_active is True
    assert user.is_admin is True # First user should be admin
    assert verify_password(user_create.password, user.hashed_password)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service, mock_db_session):
    """Test user creation with a duplicate email."""
    user_create = UserCreate(email="existing@example.com", password="password123")
    
    # Mock get_user_by_email to return an existing user
    existing_user = User(email="existing@example.com", hashed_password=get_password_hash("oldpass"))
    user_service.get_user_by_email = AsyncMock(return_value=existing_user)

    with pytest.raises(UserAlreadyExistsException, match="User with email 'existing@example.com' already exists."):
        await user_service.create_user(user_create)
    
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_create_user_db_error(user_service, mock_db_session):
    """Test user creation when a database error occurs."""
    user_create = UserCreate(email="error@example.com", password="password123")
    
    # Mock get_any_user_exists to return True (not first user)
    user_service.get_any_user_exists = AsyncMock(return_value=True)

    # Simulate a database error on commit
    mock_db_session.commit.side_effect = SQLAlchemyError("Database connection lost")

    with pytest.raises(Exception, match="Failed to create user due to a database error"):
        await user_service.create_user(user_create)
    
    mock_db_session.add.assert_called_once()
    mock_db_session.rollback.assert_called_once() # Ensure rollback is called

@pytest.mark.asyncio
async def test_get_user_by_email_found(user_service, mock_db_session):
    """Test retrieving a user by email when found."""
    expected_user = User(email="found@example.com", hashed_password="hashed_pass")
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = expected_user

    user = await user_service.get_user_by_email("found@example.com")

    assert user == expected_user
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(user_service, mock_db_session):
    """Test retrieving a user by email when not found."""
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None

    user = await user_service.get_user_by_email("notfound@example.com")

    assert user is None
    mock_db_session.execute.assert_called_once()

@pytest.mark.asyncio
async def test_authenticate_user_success(user_service, mock_db_session):
    """Test successful user authentication."""
    plain_password = "correctpassword"
    hashed_password = get_password_hash(plain_password)
    authenticated_user = User(email="auth@example.com", hashed_password=hashed_password, is_active=True)
    
    user_service.get_user_by_email = AsyncMock(return_value=authenticated_user)

    user = await user_service.authenticate_user("auth@example.com", plain_password)

    assert user == authenticated_user

@pytest.mark.asyncio
async def test_authenticate_user_not_found(user_service, mock_db_session):
    """Test authentication when user is not found."""
    user_service.get_user_by_email = AsyncMock(return_value=None)

    with pytest.raises(InvalidCredentialsException, match="Incorrect email or password."):
        await user_service.authenticate_user("nonexistent@example.com", "anypassword")

@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(user_service, mock_db_session):
    """Test authentication with incorrect password."""
    hashed_password = get_password_hash("correctpassword")
    user_with_wrong_pass = User(email="wrongpass@example.com", hashed_password=hashed_password, is_active=True)
    
    user_service.get_user_by_email = AsyncMock(return_value=user_with_wrong_pass)

    with pytest.raises(InvalidCredentialsException, match="Incorrect email or password."):
        await user_service.authenticate_user("wrongpass@example.com", "incorrectpassword")

@pytest.mark.asyncio
async def test_get_any_user_exists_true(user_service, mock_db_session):
    """Test if any user exists when there is at least one."""
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = 1 # Simulate a user ID found

    exists = await user_service.get_any_user_exists()
    assert exists is True

@pytest.mark.asyncio
async def test_get_any_user_exists_false(user_service, mock_db_session):
    """Test if any user exists when there are no users."""
    mock_db_session.execute.return_value.scalars.return_value.first.return_value = None

    exists = await user_service.get_any_user_exists()
    assert exists is False