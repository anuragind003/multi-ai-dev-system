import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import List, Optional
from datetime import datetime, timezone

from schemas.user import UserCreate, UserUpdate, UserResponse
from services.user_service import UserService
from repositories.user_repository import UserRepository
from exceptions import NotFoundException, ConflictException, UnauthorizedException
from models.user import User
from security.auth import get_password_hash, verify_password

# Mock the password hashing functions for isolated testing
# In a real scenario, you might want to test the actual hashing,
# but for service logic, mocking is fine.
# For simplicity, we'll use actual hashing here, but be aware of the implications.

@pytest.fixture
def mock_user_repository():
    """Fixture to provide a mocked UserRepository."""
    return AsyncMock(spec=UserRepository)

@pytest.fixture
def user_service(mock_user_repository):
    """Fixture to provide a UserService with a mocked repository."""
    return UserService(user_repo=mock_user_repository)

@pytest.fixture
def sample_user_data():
    """Fixture for sample user creation data."""
    return UserCreate(
        email="test@example.com",
        password="Password123!",
        full_name="Test User",
        is_superuser=False
    )

@pytest.fixture
def sample_user_in_db():
    """Fixture for a sample User object as it would be in the DB."""
    return User(
        id=1,
        email="test@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Test User",
        is_active=True,
        is_superuser=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def sample_superuser_in_db():
    """Fixture for a sample superuser object in the DB."""
    return User(
        id=2,
        email="admin@example.com",
        hashed_password=get_password_hash("AdminPassword123!"),
        full_name="Admin User",
        is_active=True,
        is_superuser=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

@pytest.mark.asyncio
async def test_create_user_success(user_service, mock_user_repository, sample_user_data, sample_user_in_db):
    """Test successful user creation."""
    mock_user_repository.get_user_by_email.return_value = None
    mock_user_repository.create_user.return_value = sample_user_in_db

    user_response = await user_service.create_user(sample_user_data)

    mock_user_repository.get_user_by_email.assert_called_once_with(sample_user_data.email)
    mock_user_repository.create_user.assert_called_once()
    assert user_response.email == sample_user_data.email
    assert user_response.full_name == sample_user_data.full_name
    assert user_response.is_superuser == sample_user_data.is_superuser
    assert isinstance(user_response, UserResponse)

@pytest.mark.asyncio
async def test_create_user_conflict(user_service, mock_user_repository, sample_user_data, sample_user_in_db):
    """Test user creation with existing email."""
    mock_user_repository.get_user_by_email.return_value = sample_user_in_db

    with pytest.raises(ConflictException) as exc_info:
        await user_service.create_user(sample_user_data)

    assert "already exists" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_email.assert_called_once_with(sample_user_data.email)
    mock_user_repository.create_user.assert_not_called()

@pytest.mark.asyncio
async def test_get_user_by_id_success(user_service, mock_user_repository, sample_user_in_db):
    """Test successful retrieval of user by ID."""
    mock_user_repository.get_user_by_id.return_value = sample_user_in_db

    user_response = await user_service.get_user_by_id(sample_user_in_db.id)

    mock_user_repository.get_user_by_id.assert_called_once_with(sample_user_in_db.id)
    assert user_response.id == sample_user_in_db.id
    assert user_response.email == sample_user_in_db.email

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(user_service, mock_user_repository):
    """Test retrieval of non-existent user by ID."""
    mock_user_repository.get_user_by_id.return_value = None

    with pytest.raises(NotFoundException) as exc_info:
        await user_service.get_user_by_id(999)

    assert "not found" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_id.assert_called_once_with(999)

@pytest.mark.asyncio
async def test_get_user_by_email_success(user_service, mock_user_repository, sample_user_in_db):
    """Test successful retrieval of user by email."""
    mock_user_repository.get_user_by_email.return_value = sample_user_in_db

    user_response = await user_service.get_user_by_email(sample_user_in_db.email)

    mock_user_repository.get_user_by_email.assert_called_once_with(sample_user_in_db.email)
    assert user_response.email == sample_user_in_db.email

@pytest.mark.asyncio
async def test_get_user_by_email_not_found(user_service, mock_user_repository):
    """Test retrieval of non-existent user by email."""
    mock_user_repository.get_user_by_email.return_value = None

    with pytest.raises(NotFoundException) as exc_info:
        await user_service.get_user_by_email("nonexistent@example.com")

    assert "not found" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_email.assert_called_once_with("nonexistent@example.com")

@pytest.mark.asyncio
async def test_get_all_users_success(user_service, mock_user_repository, sample_user_in_db, sample_superuser_in_db):
    """Test successful retrieval of all users."""
    mock_user_repository.get_users.return_value = [sample_user_in_db, sample_superuser_in_db]

    users = await user_service.get_all_users(skip=0, limit=10)

    mock_user_repository.get_users.assert_called_once_with(skip=0, limit=10)
    assert len(users) == 2
    assert isinstance(users[0], UserResponse)
    assert users[0].email == sample_user_in_db.email
    assert users[1].email == sample_superuser_in_db.email

@pytest.mark.asyncio
async def test_update_user_success(user_service, mock_user_repository, sample_user_in_db):
    """Test successful user update."""
    user_update_data = UserUpdate(full_name="Updated Name")
    updated_user_in_db = sample_user_in_db
    updated_user_in_db.full_name = "Updated Name"

    mock_user_repository.get_user_by_id.return_value = sample_user_in_db
    mock_user_repository.update_user.return_value = updated_user_in_db

    user_response = await user_service.update_user(sample_user_in_db.id, user_update_data)

    mock_user_repository.get_user_by_id.assert_called_once_with(sample_user_in_db.id)
    mock_user_repository.update_user.assert_called_once()
    assert user_response.full_name == "Updated Name"
    assert user_response.email == sample_user_in_db.email # Email should not change

@pytest.mark.asyncio
async def test_update_user_password_success(user_service, mock_user_repository, sample_user_in_db):
    """Test successful user password update."""
    user_update_data = UserUpdate(password="NewPassword123!")
    
    # Mock the user_repo.update_user to return a user with the new hashed password
    updated_user_in_db = sample_user_in_db
    updated_user_in_db.hashed_password = get_password_hash("NewPassword123!")

    mock_user_repository.get_user_by_id.return_value = sample_user_in_db
    mock_user_repository.update_user.return_value = updated_user_in_db

    user_response = await user_service.update_user(sample_user_in_db.id, user_update_data)

    mock_user_repository.get_user_by_id.assert_called_once_with(sample_user_in_db.id)
    mock_user_repository.update_user.assert_called_once()
    # Verify the password was hashed before being passed to the repository
    args, kwargs = mock_user_repository.update_user.call_args
    assert 'hashed_password' in args[1].model_fields_set # Check if hashed_password was set
    assert verify_password("NewPassword123!", args[1].hashed_password) # Verify the hash

@pytest.mark.asyncio
async def test_update_user_not_found(user_service, mock_user_repository):
    """Test updating a non-existent user."""
    mock_user_repository.get_user_by_id.return_value = None

    with pytest.raises(NotFoundException) as exc_info:
        await user_service.update_user(999, UserUpdate(full_name="Non Existent"))

    assert "not found" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_id.assert_called_once_with(999)
    mock_user_repository.update_user.assert_not_called()

@pytest.mark.asyncio
async def test_update_user_email_conflict(user_service, mock_user_repository, sample_user_in_db, sample_superuser_in_db):
    """Test updating user email to an already existing email."""
    user_update_data = UserUpdate(email=sample_superuser_in_db.email)

    mock_user_repository.get_user_by_id.return_value = sample_user_in_db
    mock_user_repository.get_user_by_email.return_value = sample_superuser_in_db # This email is taken

    with pytest.raises(ConflictException) as exc_info:
        await user_service.update_user(sample_user_in_db.id, user_update_data)

    assert "already taken" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_id.assert_called_once_with(sample_user_in_db.id)
    mock_user_repository.get_user_by_email.assert_called_once_with(sample_superuser_in_db.email)
    mock_user_repository.update_user.assert_not_called()

@pytest.mark.asyncio
async def test_delete_user_success(user_service, mock_user_repository):
    """Test successful user deletion."""
    mock_user_repository.delete_user.return_value = True

    result = await user_service.delete_user(1)

    mock_user_repository.delete_user.assert_called_once_with(1)
    assert result is True

@pytest.mark.asyncio
async def test_delete_user_not_found(user_service, mock_user_repository):
    """Test deleting a non-existent user."""
    mock_user_repository.delete_user.return_value = False

    with pytest.raises(NotFoundException) as exc_info:
        await user_service.delete_user(999)

    assert "not found" in str(exc_info.value.detail)
    mock_user_repository.delete_user.assert_called_once_with(999)

@pytest.mark.asyncio
async def test_authenticate_user_success(user_service, mock_user_repository, sample_user_in_db):
    """Test successful user authentication."""
    mock_user_repository.get_user_by_email.return_value = sample_user_in_db

    user_response = await user_service.authenticate_user(sample_user_in_db.email, "Password123!")

    mock_user_repository.get_user_by_email.assert_called_once_with(sample_user_in_db.email)
    assert user_response.email == sample_user_in_db.email
    assert isinstance(user_response, UserResponse)

@pytest.mark.asyncio
async def test_authenticate_user_not_found(user_service, mock_user_repository):
    """Test authentication with non-existent email."""
    mock_user_repository.get_user_by_email.return_value = None

    user_response = await user_service.authenticate_user("nonexistent@example.com", "password")

    mock_user_repository.get_user_by_email.assert_called_once_with("nonexistent@example.com")
    assert user_response is None

@pytest.mark.asyncio
async def test_authenticate_user_wrong_password(user_service, mock_user_repository, sample_user_in_db):
    """Test authentication with incorrect password."""
    mock_user_repository.get_user_by_email.return_value = sample_user_in_db

    user_response = await user_service.authenticate_user(sample_user_in_db.email, "WrongPassword")

    mock_user_repository.get_user_by_email.assert_called_once_with(sample_user_in_db.email)
    assert user_response is None

@pytest.mark.asyncio
async def test_authenticate_user_inactive(user_service, mock_user_repository, sample_user_in_db):
    """Test authentication with inactive user."""
    inactive_user = sample_user_in_db
    inactive_user.is_active = False
    mock_user_repository.get_user_by_email.return_value = inactive_user

    with pytest.raises(UnauthorizedException) as exc_info:
        await user_service.authenticate_user(inactive_user.email, "Password123!")

    assert "Inactive user" in str(exc_info.value.detail)
    mock_user_repository.get_user_by_email.assert_called_once_with(inactive_user.email)