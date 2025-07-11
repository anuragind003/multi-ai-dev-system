import pytest
from sqlalchemy.orm import Session
from app.services.user_service import UserService
from app.services.recording_service import RecordingService
from app.schemas import UserCreate, UserUpdate, RecordingCreate
from app.exceptions import NotFoundException, ConflictException, InvalidInputException, ServiceUnavailableException
from app.models import User, Role, Recording
from app.security import verify_password, get_password_hash
import os

# Assuming conftest.py sets up the test database and provides get_db override

@pytest.fixture
def db_session(setup_test_db):
    """Provides a fresh database session for each test."""
    from app.database import TestingSessionLocal
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback() # Rollback any changes made during the test
        db.close()

@pytest.fixture
def user_service(db_session: Session):
    """Provides a UserService instance."""
    return UserService(db_session)

@pytest.fixture
def recording_service(db_session: Session):
    """Provides a RecordingService instance."""
    return RecordingService(db_session)

@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Retrieves the test admin user."""
    return db_session.query(User).filter(User.email == "test_admin@example.com").first()

@pytest.fixture
def auditor_user(db_session: Session) -> User:
    """Retrieves the test auditor user."""
    return db_session.query(User).filter(User.email == "test_auditor@example.com").first()

# --- UserService Tests ---

def test_user_service_create_user_success(user_service: UserService, db_session: Session):
    """Test successful user creation."""
    new_user_data = UserCreate(
        email="service_test@example.com",
        password="securepassword",
        first_name="Service",
        last_name="Test",
        is_active=True,
        role_id=2 # Auditor role
    )
    user = user_service.create_user(new_user_data)
    assert user.email == new_user_data.email
    assert user.first_name == new_user_data.first_name
    assert user.is_active == new_user_data.is_active
    assert verify_password(new_user_data.password, user.hashed_password)
    assert user.role.name == "auditor"

    # Verify in DB
    db_user = db_session.query(User).filter(User.email == new_user_data.email).first()
    assert db_user is not None
    assert db_user.email == new_user_data.email

def test_user_service_create_user_duplicate_email(user_service: UserService):
    """Test creating user with duplicate email."""
    existing_user_email = "test_admin@example.com"
    new_user_data = UserCreate(
        email=existing_user_email,
        password="password",
        first_name="Duplicate",
        last_name="Email",
        is_active=True,
        role_id=2
    )
    with pytest.raises(ConflictException, match="already exists"):
        user_service.create_user(new_user_data)

def test_user_service_create_user_non_existent_role(user_service: UserService):
    """Test creating user with non-existent role ID."""
    new_user_data = UserCreate(
        email="no_role@example.com",
        password="password",
        first_name="No",
        last_name="Role",
        is_active=True,
        role_id=999 # Non-existent
    )
    with pytest.raises(NotFoundException, match="Role with ID 999 not found"):
        user_service.create_user(new_user_data)

def test_user_service_get_user_by_id_success(user_service: UserService, admin_user: User):
    """Test retrieving user by ID."""
    retrieved_user = user_service.get_user_by_id(admin_user.id)
    assert retrieved_user.id == admin_user.id
    assert retrieved_user.email == admin_user.email

def test_user_service_get_user_by_id_not_found(user_service: UserService):
    """Test retrieving non-existent user by ID."""
    with pytest.raises(NotFoundException, match="User with ID 999 not found"):
        user_service.get_user_by_id(999)

def test_user_service_update_user_success(user_service: UserService, admin_user: User):
    """Test successful user update."""
    update_data = UserUpdate(first_name="UpdatedAdmin", is_active=False)
    updated_user = user_service.update_user(admin_user.id, update_data)
    assert updated_user.first_name == "UpdatedAdmin"
    assert updated_user.is_active is False

    # Verify in DB
    db_user = user_service.get_user_by_id(admin_user.id)
    assert db_user.first_name == "UpdatedAdmin"
    assert db_user.is_active is False

def test_user_service_update_user_change_email_to_existing(user_service: UserService, admin_user: User, auditor_user: User):
    """Test updating user email to an already existing one."""
    update_data = UserUpdate(email=auditor_user.email)
    with pytest.raises(ConflictException, match="already taken by another user"):
        user_service.update_user(admin_user.id, update_data)

def test_user_service_update_user_change_role_to_non_existent(user_service: UserService, admin_user: User):
    """Test updating user role to a non-existent role ID."""
    update_data = UserUpdate(role_id=999)
    with pytest.raises(NotFoundException, match="Role with ID 999 not found"):
        user_service.update_user(admin_user.id, update_data)

def test_user_service_delete_user_success(user_service: UserService, db_session: Session):
    """Test successful user deletion."""
    user_to_delete = UserCreate(
        email="to_delete@example.com",
        password="password",
        first_name="Delete",
        last_name="Me",
        is_active=True,
        role_id=2
    )
    created_user = user_service.create_user(user_to_delete)
    
    user_service.delete_user(created_user.id)
    with pytest.raises(NotFoundException):
        user_service.get_user_by_id(created_user.id)

def test_user_service_delete_user_not_found(user_service: UserService):
    """Test deleting non-existent user."""
    with pytest.raises(NotFoundException, match="User with ID 999 not found"):
        user_service.delete_user(999)

# --- RecordingService Tests ---

def test_recording_service_create_recording_success(recording_service: RecordingService, admin_user: User, mocker):
    """Test successful recording creation."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    new_recording_data = RecordingCreate(
        lan_id="LAN_TEST_001",
        file_name="test_rec_001.mp4",
        file_path="/nfs/test_rec_001.mp4",
        file_size_bytes=1024,
        recording_date="2023-11-01T10:00:00Z"
    )
    recording = recording_service.create_recording(new_recording_data, admin_user.id)
    assert recording.lan_id == new_recording_data.lan_id
    assert recording.file_name == new_recording_data.file_name
    assert recording.uploader_id == admin_user.id
    mocker.patch('os.path.exists', return_value=True) # Ensure subsequent checks pass

def test_recording_service_create_recording_duplicate_path(recording_service: RecordingService, admin_user: User, mocker):
    """Test creating recording with duplicate file path."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)

    existing_path = "/nfs/existing_rec.mp4"
    recording_service.create_recording(
        RecordingCreate(lan_id="LAN_EXIST", file_name="existing.mp4", file_path=existing_path),
        admin_user.id
    )

    new_recording_data = RecordingCreate(
        lan_id="LAN_NEW",
        file_name="new_rec.mp4",
        file_path=existing_path # Duplicate path
    )
    with pytest.raises(ConflictException, match="already exists"):
        recording_service.create_recording(new_recording_data, admin_user.id)

def test_recording_service_create_recording_nfs_fail(recording_service: RecordingService, admin_user: User, mocker):
    """Test creating recording when NFS simulation fails."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=False)

    new_recording_data = RecordingCreate(
        lan_id="LAN_NFS_FAIL",
        file_name="nfs_fail.mp4",
        file_path="/nfs/nfs_fail.mp4"
    )
    with pytest.raises(ServiceUnavailableException, match="Failed to create file on storage server"):
        recording_service.create_recording(new_recording_data, admin_user.id)

def test_recording_service_get_recording_by_id_success(recording_service: RecordingService, admin_user: User, mocker):
    """Test retrieving recording by ID."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="GET_REC", file_name="get_rec.mp4", file_path="/nfs/get_rec.mp4"),
        admin_user.id
    )
    retrieved_rec = recording_service.get_recording_by_id(created_rec.id)
    assert retrieved_rec.id == created_rec.id
    assert retrieved_rec.lan_id == created_rec.lan_id

def test_recording_service_get_recording_by_id_not_found(recording_service: RecordingService):
    """Test retrieving non-existent recording by ID."""
    with pytest.raises(NotFoundException, match="Recording with ID 999 not found"):
        recording_service.get_recording_by_id(999)

def test_recording_service_update_recording_success(recording_service: RecordingService, admin_user: User, mocker):
    """Test successful recording update."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="UPDATE_REC", file_name="update_rec.mp4", file_path="/nfs/update_rec.mp4"),
        admin_user.id
    )
    update_data = RecordingUpdate(file_name="updated_rec.mp4", status="archived")
    updated_rec = recording_service.update_recording(created_rec.id, update_data)
    assert updated_rec.file_name == "updated_rec.mp4"
    assert updated_rec.status == "archived"

def test_recording_service_update_recording_change_path(recording_service: RecordingService, admin_user: User, mocker):
    """Test updating recording with a new file path."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="PATH_CHANGE", file_name="old_path.mp4", file_path="/nfs/old_path.mp4"),
        admin_user.id
    )
    new_path = "/nfs/new_path.mp4"
    update_data = RecordingUpdate(file_path=new_path)
    updated_rec = recording_service.update_recording(created_rec.id, update_data)
    assert updated_rec.file_path == new_path
    # Ensure NFS access was called for delete old and write new
    assert mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access').call_count == 3 # create, delete, write

def test_recording_service_delete_recording_success(recording_service: RecordingService, admin_user: User, mocker):
    """Test successful recording deletion."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="DELETE_REC", file_name="delete_rec.mp4", file_path="/nfs/delete_rec.mp4"),
        admin_user.id
    )
    recording_service.delete_recording(created_rec.id)
    with pytest.raises(NotFoundException):
        recording_service.get_recording_by_id(created_rec.id)
    # Ensure NFS delete was called
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access').assert_called_with(created_rec.file_path, operation="delete")

def test_recording_service_delete_recording_nfs_fail(recording_service: RecordingService, admin_user: User, mocker):
    """Test deleting recording when NFS simulation fails."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', side_effect=[True, False]) # Create succeeds, delete fails
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="DELETE_NFS_FAIL", file_name="delete_nfs_fail.mp4", file_path="/nfs/delete_nfs_fail.mp4"),
        admin_user.id
    )
    with pytest.raises(ServiceUnavailableException, match="Failed to delete file from storage server"):
        recording_service.delete_recording(created_rec.id)
    # Ensure recording metadata is NOT deleted if NFS delete fails
    assert recording_service.get_recording_by_id(created_rec.id) is not None

def test_recording_service_download_recording_file_success(recording_service: RecordingService, admin_user: User, mocker):
    """Test successful recording file download simulation."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', return_value=True)
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="DOWNLOAD_REC", file_name="download_rec.mp4", file_path="/nfs/download_rec.mp4"),
        admin_user.id
    )
    file_path = recording_service.download_recording_file(created_rec.id)
    assert file_path.endswith("download_rec.mp4")
    # Ensure NFS read was called
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access').assert_called_with(created_rec.file_path, operation="read")

def test_recording_service_download_recording_file_nfs_fail(recording_service: RecordingService, admin_user: User, mocker):
    """Test downloading recording when NFS simulation fails."""
    mocker.patch('app.services.recording_service.RecordingService._simulate_nfs_access', side_effect=[True, False]) # Create succeeds, read fails
    
    created_rec = recording_service.create_recording(
        RecordingCreate(lan_id="DOWNLOAD_NFS_FAIL", file_name="download_nfs_fail.mp4", file_path="/nfs/download_nfs_fail.mp4"),
        admin_user.id
    )
    with pytest.raises(ServiceUnavailableException, match="Recording file not found or inaccessible on storage server"):
        recording_service.download_recording_file(created_rec.id)