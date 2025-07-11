import pytest
from datetime import datetime, timedelta
from app.services.services import AuthService, RecordingService
from app.schemas.schemas import UserCreate, UserUpdate, RecordingCreate, RecordingUpdate, RecordingFilter
from app.models.models import User, RecordingStatus
from app.core.exceptions import NotFoundException, DuplicateEntryException, UnauthorizedException, ForbiddenException, InvalidInputException
from app.core.security import verify_password

# --- AuthService Tests ---

@pytest.mark.asyncio
async def test_create_user(auth_service: AuthService):
    user_data = UserCreate(
        username="newuser",
        email="new@example.com",
        password="password123",
        full_name="New User",
        roles=["user"]
    )
    user = await auth_service.create_user(user_data)

    assert user.id is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert verify_password("password123", user.hashed_password)
    assert user.full_name == "New User"
    assert user.is_active is True
    assert user.roles == ["user"]

@pytest.mark.asyncio
async def test_create_user_duplicate_username(auth_service: AuthService, create_test_user):
    await create_test_user(username="existinguser")
    user_data = UserCreate(
        username="existinguser",
        email="another@example.com",
        password="password123",
        full_name="Duplicate User",
        roles=["user"]
    )
    with pytest.raises(DuplicateEntryException, match="Username 'existinguser' already exists."):
        await auth_service.create_user(user_data)

@pytest.mark.asyncio
async def test_create_user_duplicate_email(auth_service: AuthService, create_test_user):
    await create_test_user(email="existing@example.com")
    user_data = UserCreate(
        username="anotheruser",
        email="existing@example.com",
        password="password123",
        full_name="Duplicate User",
        roles=["user"]
    )
    with pytest.raises(DuplicateEntryException, match="Email 'existing@example.com' already exists."):
        await auth_service.create_user(user_data)

@pytest.mark.asyncio
async def test_get_user_by_username(auth_service: AuthService, create_test_user):
    created_user = await create_test_user(username="findme")
    found_user = await auth_service.get_user_by_username("findme")
    assert found_user.id == created_user.id
    assert found_user.username == "findme"

@pytest.mark.asyncio
async def test_get_user_by_username_not_found(auth_service: AuthService):
    with pytest.raises(NotFoundException, match="User 'nonexistent' not found."):
        await auth_service.get_user_by_username("nonexistent")

@pytest.mark.asyncio
async def test_get_user_by_id(auth_service: AuthService, create_test_user):
    created_user = await create_test_user(username="findbyid")
    found_user = await auth_service.get_user_by_id(created_user.id)
    assert found_user.id == created_user.id
    assert found_user.username == "findbyid"

@pytest.mark.asyncio
async def test_get_user_by_id_not_found(auth_service: AuthService):
    with pytest.raises(NotFoundException, match="User with ID '999' not found."):
        await auth_service.get_user_by_id(999)

@pytest.mark.asyncio
async def test_get_all_users(auth_service: AuthService, create_test_user):
    await create_test_user(username="user1")
    await create_test_user(username="user2", email="user2@example.com")
    users = await auth_service.get_all_users()
    assert len(users) >= 2 # Account for any users created by other tests in the same session

@pytest.mark.asyncio
async def test_update_user(auth_service: AuthService, create_test_user):
    user = await create_test_user(username="updateuser", email="update@example.com")
    update_data = UserUpdate(full_name="Updated Name", is_active=False, roles=["admin"])
    updated_user = await auth_service.update_user(user.id, update_data)

    assert updated_user.full_name == "Updated Name"
    assert updated_user.is_active is False
    assert updated_user.roles == ["admin"]
    assert updated_user.username == user.username # Should not change if not provided

@pytest.mark.asyncio
async def test_update_user_password(auth_service: AuthService, create_test_user):
    user = await create_test_user(username="passuser")
    update_data = UserUpdate(password="newsecurepassword")
    updated_user = await auth_service.update_user(user.id, update_data)

    assert verify_password("newsecurepassword", updated_user.hashed_password)

@pytest.mark.asyncio
async def test_update_user_not_found(auth_service: AuthService):
    update_data = UserUpdate(full_name="Non Existent")
    with pytest.raises(NotFoundException, match="User with ID '999' not found."):
        await auth_service.update_user(999, update_data)

@pytest.mark.asyncio
async def test_update_user_duplicate_username(auth_service: AuthService, create_test_user):
    user1 = await create_test_user(username="user_a")
    user2 = await create_test_user(username="user_b", email="user_b@example.com")
    update_data = UserUpdate(username="user_a")
    with pytest.raises(DuplicateEntryException, match="Username 'user_a' already exists."):
        await auth_service.update_user(user2.id, update_data)

@pytest.mark.asyncio
async def test_delete_user(auth_service: AuthService, create_test_user):
    user_to_delete = await create_test_user(username="todelete")
    await auth_service.delete_user(user_to_delete.id)
    with pytest.raises(NotFoundException):
        await auth_service.get_user_by_id(user_to_delete.id)

@pytest.mark.asyncio
async def test_delete_user_not_found(auth_service: AuthService):
    with pytest.raises(NotFoundException, match="User with ID '999' not found."):
        await auth_service.delete_user(999)

@pytest.mark.asyncio
async def test_delete_last_admin_user(auth_service: AuthService, create_test_user):
    # Ensure there's only one admin
    admin_user = await create_test_user(username="admin_only", roles=["admin"])
    # Create a non-admin user to ensure it's not the only user
    await create_test_user(username="regular_user", email="regular@example.com")

    # Attempt to delete the last admin
    with pytest.raises(ForbiddenException, match="Cannot delete the last admin user."):
        await auth_service.delete_user(admin_user.id)

@pytest.mark.asyncio
async def test_authenticate_user_success(auth_service: AuthService, create_test_user):
    await create_test_user(username="authuser", password="authpassword")
    token = await auth_service.authenticate_user("authuser", "authpassword")
    assert token.access_token is not None
    assert token.token_type == "bearer"

@pytest.mark.asyncio
async def test_authenticate_user_invalid_password(auth_service: AuthService, create_test_user):
    await create_test_user(username="authuser_fail", password="authpassword")
    with pytest.raises(UnauthorizedException, match="Incorrect username or password"):
        await auth_service.authenticate_user("authuser_fail", "wrongpassword")

@pytest.mark.asyncio
async def test_authenticate_user_not_found(auth_service: AuthService):
    with pytest.raises(UnauthorizedException, match="Incorrect username or password"):
        await auth_service.authenticate_user("nonexistent_user", "anypassword")

@pytest.mark.asyncio
async def test_authenticate_user_inactive(auth_service: AuthService, create_test_user):
    await create_test_user(username="inactiveuser", password="password", is_active=False)
    with pytest.raises(UnauthorizedException, match="Inactive user"):
        await auth_service.authenticate_user("inactiveuser", "password")

# --- RecordingService Tests ---

@pytest.mark.asyncio
async def test_create_recording(recording_service: RecordingService):
    recording_data = RecordingCreate(
        lan_id="LAN001",
        customer_name="Customer A",
        recording_date=datetime.now(),
        file_path="path/to/LAN001.mp4",
        duration_seconds=600,
        status=RecordingStatus.PENDING,
        notes="Initial recording"
    )
    recording = await recording_service.create_recording(recording_data)

    assert recording.id is not None
    assert recording.lan_id == "LAN001"
    assert recording.customer_name == "Customer A"
    assert recording.status == RecordingStatus.PENDING

@pytest.mark.asyncio
async def test_create_recording_duplicate_lan_id(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="DUP_LAN")
    recording_data = RecordingCreate(
        lan_id="DUP_LAN",
        customer_name="Another Customer",
        recording_date=datetime.now(),
        file_path="path/to/DUP_LAN_2.mp4"
    )
    with pytest.raises(DuplicateEntryException, match="Recording with LAN ID 'DUP_LAN' already exists."):
        await recording_service.create_recording(recording_data)

@pytest.mark.asyncio
async def test_create_recording_duplicate_file_path(recording_service: RecordingService, create_test_recording):
    await create_test_recording(file_path="path/to/DUP_FILE.mp4")
    recording_data = RecordingCreate(
        lan_id="DUP_LAN_2",
        customer_name="Another Customer",
        recording_date=datetime.now(),
        file_path="path/to/DUP_FILE.mp4"
    )
    with pytest.raises(DuplicateEntryException, match="Recording with file path 'path/to/DUP_FILE.mp4' already exists."):
        await recording_service.create_recording(recording_data)

@pytest.mark.asyncio
async def test_get_recording_by_id(recording_service: RecordingService, create_test_recording):
    created_recording = await create_test_recording(lan_id="GET_REC")
    found_recording = await recording_service.get_recording_by_id(created_recording.id)
    assert found_recording.id == created_recording.id
    assert found_recording.lan_id == "GET_REC"

@pytest.mark.asyncio
async def test_get_recording_by_id_not_found(recording_service: RecordingService):
    with pytest.raises(NotFoundException, match="Recording with ID '999' not found."):
        await recording_service.get_recording_by_id(999)

@pytest.mark.asyncio
async def test_get_all_recordings_no_filter(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="REC1")
    await create_test_recording(lan_id="REC2", file_path="path/to/REC2.mp4")
    filters = RecordingFilter()
    recordings = await recording_service.get_all_recordings(filters)
    assert len(recordings) >= 2

@pytest.mark.asyncio
async def test_get_all_recordings_filter_lan_id(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="FILTER_LAN_1", customer_name="Customer X")
    await create_test_recording(lan_id="FILTER_LAN_2", customer_name="Customer Y", file_path="path/to/FILTER_LAN_2.mp4")
    filters = RecordingFilter(lan_id="FILTER_LAN_1")
    recordings = await recording_service.get_all_recordings(filters)
    assert len(recordings) == 1
    assert recordings[0].lan_id == "FILTER_LAN_1"

@pytest.mark.asyncio
async def test_get_all_recordings_filter_customer_name(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="CUST_REC_1", customer_name="Specific Customer")
    await create_test_recording(lan_id="CUST_REC_2", customer_name="Another Customer", file_path="path/to/CUST_REC_2.mp4")
    filters = RecordingFilter(customer_name="Specific")
    recordings = await recording_service.get_all_recordings(filters)
    assert len(recordings) == 1
    assert recordings[0].customer_name == "Specific Customer"

@pytest.mark.asyncio
async def test_get_all_recordings_filter_date_range(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="DATE_REC_1", recording_date=datetime(2023, 1, 10))
    await create_test_recording(lan_id="DATE_REC_2", recording_date=datetime(2023, 1, 20), file_path="path/to/DATE_REC_2.mp4")
    await create_test_recording(lan_id="DATE_REC_3", recording_date=datetime(2023, 2, 1), file_path="path/to/DATE_REC_3.mp4")
    filters = RecordingFilter(start_date="2023-01-01", end_date="2023-01-31")
    recordings = await recording_service.get_all_recordings(filters)
    assert len(recordings) == 2
    assert all(r.lan_id in ["DATE_REC_1", "DATE_REC_2"] for r in recordings)

@pytest.mark.asyncio
async def test_get_all_recordings_filter_status(recording_service: RecordingService, create_test_recording):
    await create_test_recording(lan_id="STATUS_REC_1", status=RecordingStatus.APPROVED)
    await create_test_recording(lan_id="STATUS_REC_2", status=RecordingStatus.PENDING, file_path="path/to/STATUS_REC_2.mp4")
    filters = RecordingFilter(status=RecordingStatus.APPROVED)
    recordings = await recording_service.get_all_recordings(filters)
    assert len(recordings) == 1
    assert recordings[0].status == RecordingStatus.APPROVED

@pytest.mark.asyncio
async def test_get_all_recordings_pagination(recording_service: RecordingService, create_test_recording):
    for i in range(1, 15):
        await create_test_recording(lan_id=f"PAG_REC_{i}", file_path=f"path/to/PAG_REC_{i}.mp4")
    
    filters = RecordingFilter()
    page1 = await recording_service.get_all_recordings(filters, page=1, page_size=5)
    assert len(page1) == 5
    assert page1[0].lan_id == "PAG_REC_1" # Assuming order by creation

    page2 = await recording_service.get_all_recordings(filters, page=2, page_size=5)
    assert len(page2) == 5
    assert page2[0].lan_id == "PAG_REC_6"

@pytest.mark.asyncio
async def test_update_recording(recording_service: RecordingService, create_test_recording):
    recording = await create_test_recording(lan_id="UPDATE_REC", status=RecordingStatus.PENDING)
    update_data = RecordingUpdate(status=RecordingStatus.APPROVED, notes="Approved by manager")
    updated_recording = await recording_service.update_recording(recording.id, update_data)

    assert updated_recording.status == RecordingStatus.APPROVED
    assert updated_recording.notes == "Approved by manager"
    assert updated_recording.lan_id == recording.lan_id # Should not change if not provided

@pytest.mark.asyncio
async def test_update_recording_not_found(recording_service: RecordingService):
    update_data = RecordingUpdate(status=RecordingStatus.APPROVED)
    with pytest.raises(NotFoundException, match="Recording with ID '999' not found."):
        await recording_service.update_recording(999, update_data)

@pytest.mark.asyncio
async def test_update_recording_duplicate_lan_id(recording_service: RecordingService, create_test_recording):
    rec1 = await create_test_recording(lan_id="REC_A")
    rec2 = await create_test_recording(lan_id="REC_B", file_path="path/to/REC_B.mp4")
    update_data = RecordingUpdate(lan_id="REC_A")
    with pytest.raises(DuplicateEntryException, match="LAN ID 'REC_A' already exists."):
        await recording_service.update_recording(rec2.id, update_data)

@pytest.mark.asyncio
async def test_update_recording_duplicate_file_path(recording_service: RecordingService, create_test_recording):
    rec1 = await create_test_recording(lan_id="REC_C", file_path="path/to/REC_C.mp4")
    rec2 = await create_test_recording(lan_id="REC_D", file_path="path/to/REC_D_orig.mp4")
    update_data = RecordingUpdate(file_path="path/to/REC_C.mp4")
    with pytest.raises(DuplicateEntryException, match="File path 'path/to/REC_C.mp4' already exists."):
        await recording_service.update_recording(rec2.id, update_data)

@pytest.mark.asyncio
async def test_delete_recording(recording_service: RecordingService, create_test_recording):
    recording_to_delete = await create_test_recording(lan_id="TO_DELETE")
    await recording_service.delete_recording(recording_to_delete.id)
    with pytest.raises(NotFoundException):
        await recording_service.get_recording_by_id(recording_to_delete.id)

@pytest.mark.asyncio
async def test_delete_recording_not_found(recording_service: RecordingService):
    with pytest.raises(NotFoundException, match="Recording with ID '999' not found."):
        await recording_service.delete_recording(999)