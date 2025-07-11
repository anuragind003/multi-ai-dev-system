import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timedelta, timezone

from services.auth_service import AuthService
from services.test_service import TestService
from crud.user_crud import UserCRUD
from crud.test_crud import TestCRUD
from schemas import UserCreate, LoginRequest, TestCaseCreate, TestRunCreate, TestRunUpdate, TestResultCreate
from models import User, TestCase, TestRun, TestResult
from core.exceptions import UnauthorizedException, ConflictException, NotFoundException
from core.security import get_password_hash, create_access_token
from config import settings

# Mock the settings for token creation in tests
settings.SECRET_KEY = "test_secret_key"
settings.ALGORITHM = "HS256"
settings.ACCESS_TOKEN_EXPIRE_MINUTES = 1

@pytest.fixture
def mock_user_crud():
    """Fixture for a mocked UserCRUD instance."""
    return AsyncMock(spec=UserCRUD)

@pytest.fixture
def mock_test_crud():
    """Fixture for a mocked TestCRUD instance."""
    return AsyncMock(spec=TestCRUD)

@pytest.fixture
def auth_service(mock_user_crud):
    """Fixture for AuthService with mocked dependencies."""
    return AuthService(user_crud=mock_user_crud)

@pytest.fixture
def test_service(mock_test_crud, mock_user_crud):
    """Fixture for TestService with mocked dependencies."""
    return TestService(test_crud=mock_test_crud, user_crud=mock_user_crud)

# --- AuthService Unit Tests ---

@pytest.mark.asyncio
async def test_register_user_success(auth_service, mock_user_crud):
    user_in = UserCreate(username="testuser", email="test@example.com", password="password123", role="qa_engineer")
    mock_user_crud.get_user_by_username.return_value = None
    mock_user_crud.get_user_by_email.return_value = None
    
    # Mock the return value of create_user to be a User model instance
    mock_db_user = User(
        id=1, username="testuser", email="test@example.com", hashed_password=get_password_hash("password123"),
        is_active=True, role="qa_engineer", created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    mock_user_crud.create_user.return_value = mock_db_user

    user_response = await auth_service.register_user(user_in)

    mock_user_crud.get_user_by_username.assert_called_once_with("testuser")
    mock_user_crud.get_user_by_email.assert_called_once_with("test@example.com")
    mock_user_crud.create_user.assert_called_once()
    assert user_response.username == "testuser"
    assert user_response.email == "test@example.com"
    assert user_response.role == "qa_engineer"
    assert user_response.id == 1

@pytest.mark.asyncio
async def test_register_user_conflict_username(auth_service, mock_user_crud):
    user_in = UserCreate(username="existinguser", email="new@example.com", password="password123", role="qa_engineer")
    mock_user_crud.get_user_by_username.return_value = MagicMock(spec=User) # Simulate existing user

    with pytest.raises(ConflictException, match="Username 'existinguser' already registered."):
        await auth_service.register_user(user_in)

    mock_user_crud.get_user_by_username.assert_called_once_with("existinguser")
    mock_user_crud.create_user.assert_not_called()

@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service, mock_user_crud):
    login_data = LoginRequest(username="testuser", password="password123")
    hashed_password = get_password_hash("password123")
    mock_db_user = User(
        id=1, username="testuser", email="test@example.com", hashed_password=hashed_password,
        is_active=True, role="qa_engineer", created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    mock_user_crud.get_user_by_username.return_value = mock_db_user

    token = await auth_service.authenticate_user(login_data)

    mock_user_crud.get_user_by_username.assert_called_once_with("testuser")
    assert token.token_type == "bearer"
    assert token.access_token is not None

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(auth_service, mock_user_crud):
    login_data = LoginRequest(username="testuser", password="wrongpassword")
    hashed_password = get_password_hash("password123")
    mock_db_user = User(
        id=1, username="testuser", email="test@example.com", hashed_password=hashed_password,
        is_active=True, role="qa_engineer", created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    mock_user_crud.get_user_by_username.return_value = mock_db_user

    with pytest.raises(UnauthorizedException, match="Incorrect username or password."):
        await auth_service.authenticate_user(login_data)

@pytest.mark.asyncio
async def test_get_current_user_success(auth_service, mock_user_crud):
    mock_db_user = User(
        id=1, username="testuser", email="test@example.com", hashed_password="hashed_password",
        is_active=True, role="qa_engineer", created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    mock_user_crud.get_user_by_username.return_value = mock_db_user
    
    # Create a valid token for the mock user
    token_data = {"sub": "testuser", "user_id": 1, "roles": ["qa_engineer"]}
    valid_token = create_access_token(token_data, expires_delta=timedelta(minutes=5))

    current_user_response = await auth_service.get_current_user(valid_token)

    mock_user_crud.get_user_by_username.assert_called_once_with("testuser")
    assert current_user_response.username == "testuser"
    assert current_user_response.id == 1

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(auth_service, mock_user_crud):
    invalid_token = "invalid.jwt.token"

    with pytest.raises(UnauthorizedException, match="Invalid or expired token."):
        await auth_service.get_current_user(invalid_token)

    mock_user_crud.get_user_by_username.assert_not_called()

# --- TestService Unit Tests ---

@pytest.mark.asyncio
async def test_create_test_case_success(test_service, mock_test_crud, mock_user_crud):
    test_case_in = TestCaseCreate(
        name="Login Flow Test",
        description="Verify user can log in successfully.",
        steps="1. Navigate to login page; 2. Enter credentials; 3. Click login button",
        expected_result="User is redirected to dashboard",
        priority="high"
    )
    current_user = User(id=1, username="qa_user", email="qa@example.com", role="qa_engineer", is_active=True)
    
    mock_user_crud.get_user_by_id.return_value = current_user # Ensure user exists
    
    mock_db_test_case = TestCase(
        id=1, created_by_user_id=current_user.id, status="draft", created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        **test_case_in.model_dump()
    )
    mock_test_crud.create_test_case.return_value = mock_db_test_case

    test_case_response = await test_service.create_test_case(test_case_in, current_user)

    mock_user_crud.get_user_by_id.assert_called_once_with(current_user.id)
    mock_test_crud.create_test_case.assert_called_once_with(test_case_in, current_user.id)
    assert test_case_response.name == "Login Flow Test"
    assert test_case_response.created_by_user_id == current_user.id

@pytest.mark.asyncio
async def test_get_test_case_not_found(test_service, mock_test_crud):
    mock_test_crud.get_test_case.return_value = None

    with pytest.raises(NotFoundException, match="Test case with ID 999 not found."):
        await test_service.get_test_case(999)

@pytest.mark.asyncio
async def test_update_test_case_success(test_service, mock_test_crud):
    test_case_id = 1
    test_case_update = TestCaseUpdate(name="Updated Login Test", priority="medium")
    
    mock_db_test_case = TestCase(
        id=test_case_id, name="Original Name", description="Desc", steps="Steps", expected_result="Result",
        priority="high", status="active", created_by_user_id=1, created_at=datetime.utcnow(), updated_at=datetime.utcnow()
    )
    mock_test_crud.update_test_case.return_value = mock_db_test_case
    mock_db_test_case.name = test_case_update.name # Simulate update
    mock_db_test_case.priority = test_case_update.priority # Simulate update

    updated_test_case = await test_service.update_test_case(test_case_id, test_case_update)

    mock_test_crud.update_test_case.assert_called_once_with(test_case_id, test_case_update)
    assert updated_test_case.name == "Updated Login Test"
    assert updated_test_case.priority == "medium"

@pytest.mark.asyncio
async def test_start_test_run_success(test_service, mock_test_crud):
    test_run_in = TestRunCreate(test_case_id=1, notes="Initial run")
    current_user = User(id=1, username="qa_user", email="qa@example.com", role="qa_engineer", is_active=True)
    
    mock_db_test_run = TestRun(
        id=101, test_case_id=1, executed_by_user_id=current_user.id, status="pending",
        started_at=datetime.utcnow(), notes="Initial run"
    )
    mock_test_crud.create_test_run.return_value = mock_db_test_run

    test_run_response = await test_service.start_test_run(test_run_in, current_user)

    mock_test_crud.create_test_run.assert_called_once_with(test_run_in, current_user.id)
    assert test_run_response.id == 101
    assert test_run_response.test_case_id == 1
    assert test_run_response.executed_by_user_id == current_user.id
    assert test_run_response.status == "pending"

@pytest.mark.asyncio
async def test_update_test_run_status_success(test_service, mock_test_crud):
    test_run_id = 101
    test_run_update = TestRunUpdate(status="passed")
    
    mock_db_test_run = TestRun(
        id=test_run_id, test_case_id=1, executed_by_user_id=1, status="running",
        started_at=datetime.utcnow(), notes="Initial run"
    )
    mock_test_crud.update_test_run.return_value = mock_db_test_run
    mock_db_test_run.status = test_run_update.status # Simulate update
    mock_db_test_run.completed_at = datetime.utcnow() # Simulate update

    updated_run = await test_service.update_test_run_status(test_run_id, test_run_update)

    mock_test_crud.update_test_run.assert_called_once()
    assert updated_run.status == "passed"
    assert updated_run.completed_at is not None

@pytest.mark.asyncio
async def test_log_test_result_success(test_service, mock_test_crud):
    test_run_id = 101
    test_result_in = TestResultCreate(
        step_number=1, step_description="Verify login button", actual_result="Button clickable", status="pass"
    )
    
    mock_db_test_result = TestResult(
        id=201, test_run_id=test_run_id, recorded_at=datetime.utcnow(),
        **test_result_in.model_dump()
    )
    mock_test_crud.create_test_result.return_value = mock_db_test_result

    test_result_response = await test_service.log_test_result(test_run_id, test_result_in)

    mock_test_crud.create_test_result.assert_called_once_with(test_run_id, test_result_in)
    assert test_result_response.id == 201
    assert test_result_response.test_run_id == test_run_id
    assert test_result_response.status == "pass"