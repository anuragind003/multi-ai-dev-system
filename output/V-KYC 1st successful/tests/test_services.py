import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import datetime

from services.user_service import UserService
from services.test_service import TestService
from schemas.schemas import UserCreate, UserLogin, TestCaseCreate, TestCaseUpdate, TestRunCreate, TestRunUpdate
from models.models import User, UserRole, TestCase, TestCaseStatus, TestRun, TestRunStatus
from core.exceptions import ConflictException, NotFoundException, UnauthorizedException, UnprocessableEntityException
from security.dependencies import get_password_hash, verify_password

# Mock database session for testing services
@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None
    session.scalars.return_value.all.return_value = []
    session.add.return_value = None
    session.commit.return_value = None
    session.refresh.return_value = None
    session.delete.return_value = None
    return session

# --- UserService Tests ---

@pytest.mark.asyncio
async def test_create_user_success(mock_db_session):
    user_service = UserService(mock_db_session)
    user_in = UserCreate(username="testuser", email="test@example.com", password="Password123!", full_name="Test User", role=UserRole.QA_ENGINEER)
    
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [None, None] # No existing user/email
    
    created_user = await user_service.create_user(user_in)
    
    assert created_user.username == user_in.username
    assert created_user.email == user_in.email
    assert verify_password(user_in.password, created_user.hashed_password)
    assert created_user.role == UserRole.QA_ENGINEER
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(created_user)

@pytest.mark.asyncio
async def test_create_user_conflict_username(mock_db_session):
    user_service = UserService(mock_db_session)
    user_in = UserCreate(username="existinguser", email="new@example.com", password="Password123!")
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = User(username="existinguser") # Simulate existing user
    
    with pytest.raises(ConflictException, match="Username already registered"):
        await user_service.create_user(user_in)
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_not_called()

@pytest.mark.asyncio
async def test_authenticate_user_success(mock_db_session):
    user_service = UserService(mock_db_session)
    hashed_password = get_password_hash("Password123!")
    db_user = User(id=1, username="testuser", email="test@example.com", hashed_password=hashed_password, is_active=True, role=UserRole.QA_ENGINEER)
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_user
    
    authenticated_user = await user_service.authenticate_user(UserLogin(username="testuser", password="Password123!"))
    
    assert authenticated_user.username == db_user.username

@pytest.mark.asyncio
async def test_authenticate_user_invalid_credentials(mock_db_session):
    user_service = UserService(mock_db_session)
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None # No user found
    
    with pytest.raises(UnauthorizedException, match="Incorrect username or password"):
        await user_service.authenticate_user(UserLogin(username="nonexistent", password="wrongpassword"))

@pytest.mark.asyncio
async def test_get_user_by_id_success(mock_db_session):
    user_service = UserService(mock_db_session)
    db_user = User(id=1, username="testuser", email="test@example.com", hashed_password="hashed", is_active=True, role=UserRole.QA_ENGINEER)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_user
    
    user = await user_service.get_user_by_id(1)
    assert user.id == 1
    assert user.username == "testuser"

@pytest.mark.asyncio
async def test_update_user_success(mock_db_session):
    user_service = UserService(mock_db_session)
    db_user = User(id=1, username="olduser", email="old@example.com", hashed_password=get_password_hash("OldPass123!"), is_active=True, role=UserRole.QA_ENGINEER)
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [db_user, None, None] # Get user, no username conflict, no email conflict
    
    user_update = UserCreate(username="newuser", email="new@example.com", password="NewPass123!", full_name="New Name", role=UserRole.ADMIN)
    updated_user = await user_service.update_user(1, user_update)
    
    assert updated_user.username == "newuser"
    assert updated_user.email == "new@example.com"
    assert verify_password("NewPass123!", updated_user.hashed_password)
    assert updated_user.full_name == "New Name"
    assert updated_user.role == UserRole.ADMIN
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(updated_user)

@pytest.mark.asyncio
async def test_delete_user_success(mock_db_session):
    user_service = UserService(mock_db_session)
    db_user = User(id=1, username="todelete", email="delete@example.com", hashed_password="hashed", is_active=True, role=UserRole.QA_ENGINEER)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_user
    
    result = await user_service.delete_user(1)
    assert result is True
    mock_db_session.delete.assert_called_once_with(db_user)
    mock_db_session.commit.assert_called_once()

# --- TestService Tests ---

@pytest.mark.asyncio
async def test_create_test_case_success(mock_db_session):
    test_service = TestService(mock_db_session)
    test_case_in = TestCaseCreate(
        title="Login Flow Test",
        description="Verify user can log in successfully.",
        steps="1. Navigate to login page. 2. Enter credentials. 3. Click login.",
        expected_result="User is redirected to dashboard.",
        priority=1,
        status=TestCaseStatus.ACTIVE
    )
    creator_id = 1
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = None # No existing test case
    
    created_test_case = await test_service.create_test_case(test_case_in, creator_id)
    
    assert created_test_case.title == test_case_in.title
    assert created_test_case.creator_id == creator_id
    assert created_test_case.status == TestCaseStatus.ACTIVE
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(created_test_case)

@pytest.mark.asyncio
async def test_create_test_case_conflict(mock_db_session):
    test_service = TestService(mock_db_session)
    test_case_in = TestCaseCreate(
        title="Existing Test Case",
        description="...", steps="...", expected_result="..."
    )
    creator_id = 1
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = TestCase(title="Existing Test Case", creator_id=creator_id)
    
    with pytest.raises(ConflictException, match="Test case with title 'Existing Test Case' already exists for this creator."):
        await test_service.create_test_case(test_case_in, creator_id)
    mock_db_session.add.assert_not_called()

@pytest.mark.asyncio
async def test_update_test_case_success(mock_db_session):
    test_service = TestService(mock_db_session)
    db_test_case = TestCase(id=1, title="Old Title", description="Old Desc", steps="Old Steps", expected_result="Old Result", creator_id=1, status=TestCaseStatus.DRAFT)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_test_case
    
    test_case_update = TestCaseUpdate(title="New Title", status=TestCaseStatus.ACTIVE)
    updated_test_case = await test_service.update_test_case(1, test_case_update)
    
    assert updated_test_case.title == "New Title"
    assert updated_test_case.status == TestCaseStatus.ACTIVE
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(updated_test_case)

@pytest.mark.asyncio
async def test_delete_test_case_success(mock_db_session):
    test_service = TestService(mock_db_session)
    db_test_case = TestCase(id=1, title="To Delete", creator_id=1)
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_test_case
    
    result = await test_service.delete_test_case(1)
    assert result is True
    mock_db_session.delete.assert_called_once_with(db_test_case)
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_test_run_success(mock_db_session):
    test_service = TestService(mock_db_session)
    test_case = TestCase(id=1, title="Active Case", status=TestCaseStatus.ACTIVE, creator_id=1)
    test_run_in = TestRunCreate(test_case_id=1, notes="Initial run")
    executor_id = 2
    
    mock_db_session.execute.return_value.scalar_one_or_none.side_effect = [test_case, None] # Get test case, then no test run
    
    created_test_run = await test_service.create_test_run(test_run_in, executor_id)
    
    assert created_test_run.test_case_id == test_run_in.test_case_id
    assert created_test_run.executor_id == executor_id
    assert created_test_run.status == TestRunStatus.PENDING
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once_with(created_test_run)

@pytest.mark.asyncio
async def test_create_test_run_inactive_test_case(mock_db_session):
    test_service = TestService(mock_db_session)
    test_case = TestCase(id=1, title="Draft Case", status=TestCaseStatus.DRAFT, creator_id=1)
    test_run_in = TestRunCreate(test_case_id=1)
    executor_id = 2
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = test_case
    
    with pytest.raises(UnprocessableEntityException, match="Test case must be 'active' to create a test run."):
        await test_service.create_test_run(test_run_in, executor_id)
    mock_db_session.add.assert_not_called()

@pytest.mark.asyncio
async def test_execute_test_run_success(mock_db_session):
    test_service = TestService(mock_db_session)
    db_test_run = TestRun(id=1, test_case_id=1, executor_id=1, status=TestRunStatus.PENDING)
    executor_user = User(id=1, username="executor", email="exec@example.com", hashed_password="hashed", role=UserRole.QA_ENGINEER)
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_test_run
    
    executed_test_run = await test_service.execute_test_run(1, executor_user)
    
    assert executed_test_run.status in [TestRunStatus.PASSED, TestRunStatus.FAILED]
    assert executed_test_run.end_time is not None
    mock_db_session.commit.assert_called() # Called twice: once for RUNNING, once for final status
    mock_db_session.refresh.assert_called() # Called twice

@pytest.mark.asyncio
async def test_execute_test_run_already_running(mock_db_session):
    test_service = TestService(mock_db_session)
    db_test_run = TestRun(id=1, test_case_id=1, executor_id=1, status=TestRunStatus.RUNNING)
    executor_user = User(id=1, username="executor", email="exec@example.com", hashed_password="hashed", role=UserRole.QA_ENGINEER)
    
    mock_db_session.execute.return_value.scalar_one_or_none.return_value = db_test_run
    
    with pytest.raises(UnprocessableEntityException, match="Test run is already in 'running' state and cannot be re-executed."):
        await test_service.execute_test_run(1, executor_user)
    mock_db_session.commit.assert_not_called()