import pytest
from unittest.mock import MagicMock, AsyncMock
from io import BytesIO
from sqlalchemy.orm import Session

from app.services.file_parser import FileParserService
from app.core.exceptions import InvalidFileContentError, LANIDCountExceededError, FileProcessingError, DatabaseError
from app.db.models import ParsedFile

# Mock database session
@pytest.fixture
def mock_db_session():
    """Provides a mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.rollback = MagicMock()
    session.refresh = MagicMock()
    return session

# Mock UploadFile
def create_mock_upload_file(content: str, filename: str = "test.txt"):
    """Creates a mock UploadFile object."""
    mock_file = AsyncMock()
    mock_file.filename = filename
    mock_file.read.return_value = content.encode('utf-8')
    return mock_file

@pytest.fixture
def file_parser_service(mock_db_session):
    """Provides an instance of FileParserService with a mock DB session."""
    return FileParserService(mock_db_session)

@pytest.mark.asyncio
async def test_parse_and_validate_file_success(file_parser_service, mock_db_session):
    """Test successful parsing and validation of a valid file."""
    content = "LAN1234567\nLAN8901234\nLAN5678901"
    mock_file = create_mock_upload_file(content, "valid_lan_ids.txt")

    result = await file_parser_service.parse_and_validate_file(mock_file)

    assert result["filename"] == "valid_lan_ids.txt"
    assert result["status"] == "success"
    assert result["message"] == "File processed successfully. All LAN IDs are valid."
    assert result["total_lan_ids"] == 3
    assert result["valid_lan_ids_count"] == 3
    assert result["invalid_lan_ids_count"] == 0
    assert len(result["validation_results"]) == 3
    assert all(res.is_valid for res in result["validation_results"])
    assert result["parsed_file_id"] is not None

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()
    assert isinstance(mock_db_session.add.call_args[0][0], ParsedFile)

@pytest.mark.asyncio
async def test_parse_and_validate_file_partial_success(file_parser_service, mock_db_session):
    """Test parsing with some invalid LAN IDs."""
    content = "LAN1234567\nINVALID_LAN\nLAN5678901\nSHORT_LAN"
    mock_file = create_mock_upload_file(content, "partial_lan_ids.txt")

    result = await file_parser_service.parse_and_validate_file(mock_file)

    assert result["filename"] == "partial_lan_ids.txt"
    assert result["status"] == "partial_success"
    assert "File processed with some invalid LAN IDs." in result["message"]
    assert result["total_lan_ids"] == 4
    assert result["valid_lan_ids_count"] == 2
    assert result["invalid_lan_ids_count"] == 2
    assert len(result["validation_results"]) == 4
    assert result["validation_results"][0].is_valid is True
    assert result["validation_results"][1].is_valid is False
    assert result["validation_results"][1].error_message == "Invalid format. Expected 'LAN' followed by 7 digits (e.g., LAN1234567)."
    assert result["validation_results"][2].is_valid is True
    assert result["validation_results"][3].is_valid is False
    assert result["parsed_file_id"] is not None

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_parse_and_validate_file_all_invalid(file_parser_service, mock_db_session):
    """Test parsing where all LAN IDs are invalid."""
    content = "INVALID_LAN\nANOTHER_INVALID"
    mock_file = create_mock_upload_file(content, "all_invalid.txt")

    result = await file_parser_service.parse_and_validate_file(mock_file)

    assert result["filename"] == "all_invalid.txt"
    assert result["status"] == "failed"
    assert "File processing failed: All LAN IDs are invalid." in result["message"]
    assert result["total_lan_ids"] == 2
    assert result["valid_lan_ids_count"] == 0
    assert result["invalid_lan_ids_count"] == 2
    assert all(not res.is_valid for res in result["validation_results"])
    assert result["parsed_file_id"] is not None

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.refresh.assert_called_once()

@pytest.mark.asyncio
async def test_parse_and_validate_file_empty_file(file_parser_service):
    """Test handling of an empty file."""
    mock_file = create_mock_upload_file("", "empty.txt")
    with pytest.raises(InvalidFileContentError, match="Uploaded file is empty."):
        await file_parser_service.parse_and_validate_file(mock_file)

@pytest.mark.asyncio
async def test_parse_and_validate_file_too_few_lan_ids(file_parser_service):
    """Test handling of a file with too few LAN IDs."""
    content = "LAN1234567" # Only 1 LAN ID
    mock_file = create_mock_upload_file(content, "too_few.txt")
    with pytest.raises(LANIDCountExceededError, match=f"Number of LAN IDs \\(1\\) must be between {FileParserService.MIN_LAN_IDS} and {FileParserService.MAX_LAN_IDS}."):
        await file_parser_service.parse_and_validate_file(mock_file)

@pytest.mark.asyncio
async def test_parse_and_validate_file_too_many_lan_ids(file_parser_service):
    """Test handling of a file with too many LAN IDs."""
    content = "\n".join([f"LAN{i:07d}" for i in range(FileParserService.MAX_LAN_IDS + 1)]) # 51 LAN IDs
    mock_file = create_mock_upload_file(content, "too_many.txt")
    with pytest.raises(LANIDCountExceededError, match=f"Number of LAN IDs \\({FileParserService.MAX_LAN_IDS + 1}\\) must be between {FileParserService.MIN_LAN_IDS} and {FileParserService.MAX_LAN_IDS}."):
        await file_parser_service.parse_and_validate_file(mock_file)

@pytest.mark.asyncio
async def test_parse_and_validate_file_database_error(file_parser_service, mock_db_session):
    """Test handling of a database error during saving."""
    content = "LAN1234567\nLAN8901234"
    mock_file = create_mock_upload_file(content, "db_error.txt")

    mock_db_session.commit.side_effect = SQLAlchemyError("DB connection lost")

    with pytest.raises(DatabaseError, match="Failed to save file processing results"):
        await file_parser_service.parse_and_validate_file(mock_file)

    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()
    mock_db_session.rollback.assert_called_once() # Ensure rollback is called
    mock_db_session.refresh.assert_not_called()

@pytest.mark.asyncio
async def test_parse_and_validate_file_unicode_error(file_parser_service):
    """Test handling of a file with invalid encoding."""
    mock_file = AsyncMock()
    mock_file.filename = "bad_encoding.txt"
    # Simulate non-UTF-8 content
    mock_file.read.return_value = b'\x80abc' # Invalid start byte for UTF-8

    with pytest.raises(InvalidFileContentError, match="File encoding error. Please ensure it's UTF-8 encoded."):
        await file_parser_service.parse_and_validate_file(mock_file)

@pytest.mark.asyncio
async def test_parse_and_validate_file_general_exception(file_parser_service):
    """Test handling of a general unexpected exception during file processing."""
    mock_file = AsyncMock()
    mock_file.filename = "general_error.txt"
    mock_file.read.side_effect = Exception("Simulated unexpected error")

    with pytest.raises(FileProcessingError, match="An unexpected error occurred while processing"):
        await file_parser_service.parse_and_validate_file(mock_file)

def test_validate_lan_id_valid(file_parser_service):
    """Test _validate_lan_id with a valid LAN ID."""
    is_valid, error_msg = file_parser_service._validate_lan_id("LAN1234567")
    assert is_valid is True
    assert error_msg == ""

def test_validate_lan_id_invalid_format(file_parser_service):
    """Test _validate_lan_id with an invalid format."""
    is_valid, error_msg = file_parser_service._validate_lan_id("INVALIDLAN")
    assert is_valid is False
    assert "Invalid format" in error_msg

    is_valid, error_msg = file_parser_service._validate_lan_id("LAN123")
    assert is_valid is False
    assert "Invalid format" in error_msg

    is_valid, error_msg = file_parser_service._validate_lan_id("lan1234567")
    assert is_valid is False
    assert "Invalid format" in error_msg

def test_validate_lan_id_empty(file_parser_service):
    """Test _validate_lan_id with an empty string."""
    is_valid, error_msg = file_parser_service._validate_lan_id("")
    assert is_valid is False
    assert "LAN ID cannot be empty."

def test_validate_lan_id_whitespace(file_parser_service):
    """Test _validate_lan_id with whitespace."""
    is_valid, error_msg = file_parser_service._validate_lan_id("   LAN1234567   ")
    # The service strips content, but _validate_lan_id expects already stripped.
    # If this was called directly with unstripped, it would fail.
    # For this test, assume it's already stripped by the caller.
    assert is_valid is False # Because the regex doesn't account for leading/trailing spaces
    assert "Invalid format" in error_msg