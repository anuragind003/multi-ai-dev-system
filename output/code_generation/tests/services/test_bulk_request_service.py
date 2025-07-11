import pytest
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from services.bulk_request_service import BulkRequestService
from db.models import BulkRequest, LanIdStatus, BulkRequestStatusEnum, LanIdProcessingStatusEnum
from schemas.bulk_request import BulkRequestCreate, LanIdInput
from core.exceptions import NotFoundException, InternalServerError

# Mock the SessionLocal for background task to avoid actual DB connection in tests
# This is a bit tricky with how SessionLocal is imported in the service.
# For a robust test setup, consider using pytest-mock and patching `db.database.SessionLocal`
# or refactoring the background task to accept a session factory.
# For simplicity here, we'll mock the db session passed to the service.

@pytest.fixture
def mock_db_session():
    """Fixture for a mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    session.query.return_value.filter.return_value.first.return_value = None # Default for .first()
    session.query.return_value.filter.return_value.all.return_value = [] # Default for .all()
    return session

@pytest.fixture
def bulk_request_service(mock_db_session):
    """Fixture for BulkRequestService with a mock DB session."""
    return BulkRequestService(mock_db_session)

@pytest.mark.asyncio
async def test_create_bulk_request_success(bulk_request_service, mock_db_session):
    """Test successful creation of a bulk request."""
    user_id = uuid4()
    lan_ids_input = [LanIdInput(lan_id="LAN001"), LanIdInput(lan_id="LAN002")]
    request_data = BulkRequestCreate(lan_ids=lan_ids_input, metadata={"source": "test"})

    # Mock the flush and refresh to return a valid BulkRequest object
    mock_db_session.flush.side_effect = lambda: None
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', uuid4()) # Assign an ID on refresh

    # Mock asyncio.create_task
    bulk_request_service._process_lan_ids_in_background = AsyncMock()

    response = await bulk_request_service.create_bulk_request(request_data, user_id)

    assert response.status == BulkRequestStatusEnum.PENDING
    assert response.user_id == user_id
    assert len(response.lan_id_statuses) == 2
    assert response.lan_id_statuses[0].lan_id == "LAN001"
    assert response.lan_id_statuses[1].lan_id == "LAN002"
    assert response.metadata["total_lan_ids"] == 2
    mock_db_session.add.assert_called()
    mock_db_session.commit.assert_called_once()
    bulk_request_service._process_lan_ids_in_background.assert_called_once_with(response.id)

@pytest.mark.asyncio
async def test_create_bulk_request_db_error(bulk_request_service, mock_db_session):
    """Test database error during bulk request creation."""
    user_id = uuid4()
    lan_ids_input = [LanIdInput(lan_id="LAN001")]
    request_data = BulkRequestCreate(lan_ids=lan_ids_input)

    mock_db_session.add.side_effect = SQLAlchemyError("DB connection failed")

    with pytest.raises(InternalServerError, match="Failed to create bulk request due to a database error."):
        await bulk_request_service.create_bulk_request(request_data, user_id)

    mock_db_session.rollback.assert_called_once()

@pytest.mark.asyncio
async def test_get_bulk_request_by_id_success(bulk_request_service, mock_db_session):
    """Test successful retrieval of a bulk request."""
    request_id = uuid4()
    mock_bulk_request = BulkRequest(
        id=request_id,
        user_id=uuid4(),
        status=BulkRequestStatusEnum.COMPLETED,
        metadata={"total_lan_ids": 1},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_lan_status = LanIdStatus(
        bulk_request_id=request_id,
        lan_id="LAN001",
        status=LanIdProcessingStatusEnum.SUCCESS,
        message="Processed",
        processed_at=datetime.utcnow()
    )
    mock_bulk_request.lan_id_statuses = [mock_lan_status]

    mock_db_session.query.return_value.filter.return_value.first.return_value = mock_bulk_request

    response = await bulk_request_service.get_bulk_request_by_id(request_id)

    assert response.id == request_id
    assert response.status == BulkRequestStatusEnum.COMPLETED
    assert len(response.lan_id_statuses) == 1
    assert response.lan_id_statuses[0].lan_id == "LAN001"
    assert response.lan_id_statuses[0].status == LanIdProcessingStatusEnum.SUCCESS

@pytest.mark.asyncio
async def test_get_bulk_request_by_id_not_found(bulk_request_service, mock_db_session):
    """Test retrieval of a non-existent bulk request."""
    request_id = uuid4()
    mock_db_session.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(NotFoundException, match=f"Bulk request with ID '{request_id}' not found."):
        await bulk_request_service.get_bulk_request_by_id(request_id)

@pytest.mark.asyncio
async def test_process_lan_ids_in_background_success(mock_db_session):
    """Test background processing with all LAN IDs succeeding."""
    request_id = uuid4()
    user_id = uuid4()
    
    # Mock the background DB session
    mock_background_db_session = MagicMock(spec=Session)
    
    # Patch SessionLocal to return our mock session for the background task
    import services.bulk_request_service
    original_session_local = services.bulk_request_service.SessionLocal
    services.bulk_request_service.SessionLocal = MagicMock(return_value=mock_background_db_session)

    mock_bulk_request = BulkRequest(
        id=request_id,
        user_id=user_id,
        status=BulkRequestStatusEnum.PENDING,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    mock_lan_status_1 = LanIdStatus(
        bulk_request_id=request_id, lan_id="LAN001", status=LanIdProcessingStatusEnum.PENDING
    )
    mock_lan_status_2 = LanIdStatus(
        bulk_request_id=request_id, lan_id="LAN002", status=LanIdProcessingStatusEnum.PENDING
    )

    # Configure mocks for the background session's queries
    mock_background_db_session.query.return_value.filter.return_value.first.return_value = mock_bulk_request
    mock_background_db_session.query.return_value.filter.return_value.all.return_value = [
        mock_lan_status_1, mock_lan_status_2
    ]

    service = BulkRequestService(mock_db_session) # The service instance used for initial call
    await service._process_lan_ids_in_background(request_id)

    # Assertions for the background session
    assert mock_bulk_request.status == BulkRequestStatusEnum.COMPLETED
    assert mock_lan_status_1.status == LanIdProcessingStatusEnum.SUCCESS
    assert mock_lan_status_2.status == LanIdProcessingStatusEnum.SUCCESS
    mock_background_db_session.commit.call_count == 3 # Initial bulk status + 2 LAN IDs
    mock_background_db_session.close.assert_called_once()

    # Restore original SessionLocal
    services.bulk_request_service.SessionLocal = original_session_local

@pytest.mark.asyncio
async def test_process_lan_ids_in_background_partial_failure(mock_db_session):
    """Test background processing with some LAN IDs failing."""
    request_id = uuid4()
    user_id = uuid4()
    
    mock_background_db_session = MagicMock(spec=Session)
    import services.bulk_request_service
    original_session_local = services.bulk_request_service.SessionLocal
    services.bulk_request_service.SessionLocal = MagicMock(return_value=mock_background_db_session)

    mock_bulk_request = BulkRequest(
        id=request_id,
        user_id=user_id,
        status=BulkRequestStatusEnum.PENDING,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    # Make one LAN ID simulate failure
    mock_lan_status_1 = LanIdStatus(
        bulk_request_id=request_id, lan_id="LAN001FAIL", status=LanIdProcessingStatusEnum.PENDING
    )
    mock_lan_status_2 = LanIdStatus(
        bulk_request_id=request_id, lan_id="LAN002", status=LanIdProcessingStatusEnum.PENDING
    )

    mock_background_db_session.query.return_value.filter.return_value.first.return_value = mock_bulk_request
    mock_background_db_session.query.return_value.filter.return_value.all.return_value = [
        mock_lan_status_1, mock_lan_status_2
    ]

    service = BulkRequestService(mock_db_session)
    await service._process_lan_ids_in_background(request_id)

    assert mock_bulk_request.status == BulkRequestStatusEnum.FAILED
    assert mock_lan_status_1.status == LanIdProcessingStatusEnum.FAILED
    assert mock_lan_status_2.status == LanIdProcessingStatusEnum.SUCCESS
    mock_background_db_session.commit.call_count == 3
    mock_background_db_session.close.assert_called_once()

    services.bulk_request_service.SessionLocal = original_session_local