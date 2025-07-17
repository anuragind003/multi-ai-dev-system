import pytest
from unittest.mock import MagicMock, AsyncMock
from io import BytesIO
from fastapi import UploadFile
from sqlalchemy.orm import Session
from services.file_parser_service import FileParserService
from core.exceptions import InvalidFileFormatException, InvalidLANIDCountException, FileTooLargeException
from models import FileUpload
from config import settings

# Mock settings for tests
settings.MIN_LAN_IDS_PER_FILE = 2
settings.MAX_LAN_IDS_PER_FILE = 50
settings.MAX_FILE_SIZE_MB = 1

@pytest.fixture
def mock_db_session():
    """Fixture for a mock SQLAlchemy session."""
    session = MagicMock(spec=Session)
    session.add = MagicMock()
    session.commit = MagicMock()
    session.refresh = MagicMock()
    return session

@pytest.fixture
def file_parser_service(mock_db_session):
    """Fixture for FileParserService with a mock DB session."""
    return FileParserService(db_session=mock_db_session)

@pytest.mark.asyncio
async def test_parse_and_validate_file_csv_success(file_parser_service, mock_db_session):
    """Test successful parsing and validation of a CSV file."""
    csv_content = "LAN12345\nLAN67890\nLANABCDE"
    mock_file = UploadFile(
        filename="test.csv",
        file=BytesIO(csv_content.encode('utf-8')),
        content_type="text/csv"
    )
    mock_file.size = len(csv_content.encode('utf-8')) # Simulate file size

    # Mock the database add/commit/refresh to return a mock FileUpload object
    mock_file_upload_instance = MagicMock(spec=FileUpload)
    mock_file_upload_instance.id = 1
    mock_file_upload_instance.filename = "test.csv"
    mock_file_upload_instance.status = "Completed"
    mock_file_upload_instance.message = "File processed successfully."
    mock_file_upload_instance.total_lan_ids = 3
    mock_file_upload_instance.valid_lan_ids_count = 3
    mock_file_upload_instance.invalid_lan_ids_count = 0
    mock_file_upload_instance.processed_lan_ids = ["LAN12345", "LAN67890", "LANABCDE"]
    mock_file_upload_instance.invalid_lan_ids_details = []

    mock_db_session.add.return_value = None
    mock_db_session.commit.return_value = None
    mock_db_session.refresh.side_effect = lambda obj: setattr(obj, 'id', 1) # Simulate ID assignment

    # Patch is_valid_lan_id to return True for our test data
    with pytest.MonkeyPatch().context() as m:
        m.setattr("utils.lan_id_validator.is_valid_lan_id", lambda x: True)
        
        result = await file_parser_service.parse_and_validate_file(mock_file, "testuser")

    assert result["status"] == "Completed"
    assert result["total_lan_ids"] == 3
    assert result["valid_lan_ids_count"] == 3
    assert result["invalid_lan_ids_count"] == 0
    assert result["filename"] == "test.csv"
    assert mock_db_session.add.called
    assert mock_db_session.commit.called
    assert mock_db_session.refresh.called

@pytest.mark.asyncio
async def test_parse_and_validate_file_txt_with_invalid_ids(file_parser_service, mock_db_session):
    """Test parsing TXT with some invalid LAN IDs."""
    txt_content = "LAN12345\nINVALID_ID\nLANABCDE\nSHORT"
    mock_file = UploadFile(
        filename="test.txt",
        file=BytesIO(txt_content.encode('utf-8')),
        content_type="text/plain"
    )
    mock_file.size = len(txt_content.encode('utf-8'))

    # Patch is_valid_lan_id to simulate some invalid IDs
    def mock_is_valid(lan_id):
        return lan_id in ["LAN12345", "LANABCDE"]

    with pytest.MonkeyPatch().context() as m:
        m.setattr("utils.lan_id_validator.is_valid_lan_id", mock_is_valid)
        
        result = await file_parser_service.parse_and_validate_file(mock_file, "testuser")

    assert result["status"] == "Completed with Errors"
    assert result["total_lan_ids"] == 4
    assert result["valid_lan_ids_count"] == 2
    assert result["invalid_lan_ids_count"] == 2
    assert len(result["invalid_lan_ids_details"]) == 2
    assert result["invalid_lan_ids_details"][0]["lan_id"] == "INVALID_ID"
    assert result["invalid_lan_ids_details"][1]["lan_id"] == "SHORT"
    assert mock_db_session.add.called

@pytest.mark.asyncio
async def test_parse_and_validate_file_unsupported_format(file_parser_service):
    """Test handling of unsupported file formats."""
    mock_file = UploadFile(
        filename="test.pdf",
        file=BytesIO(b"pdf content"),
        content_type="application/pdf"
    )
    mock_file.size = 100

    with pytest.raises(InvalidFileFormatException):
        await file_parser_service.parse_and_validate_file(mock_file, "testuser")

@pytest.mark.asyncio
async def test_parse_and_validate_file_too_few_ids(file_parser_service):
    """Test handling of files with too few LAN IDs."""
    txt_content = "LAN12345" # Only 1 ID, min is 2
    mock_file = UploadFile(
        filename="test.txt",
        file=BytesIO(txt_content.encode('utf-8')),
        content_type="text/plain"
    )
    mock_file.size = len(txt_content.encode('utf-8'))

    with pytest.MonkeyPatch().context() as m:
        m.setattr("utils.lan_id_validator.is_valid_lan_id", lambda x: True)
        with pytest.raises(InvalidLANIDCountException) as excinfo:
            await file_parser_service.parse_and_validate_file(mock_file, "testuser")
        assert "Expected between 2 and 50, but got 1." in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_parse_and_validate_file_too_many_ids(file_parser_service):
    """Test handling of files with too many LAN IDs."""
    # Create content with 51 LAN IDs (max is 50)
    lan_ids = [f"LAN{i:05d}" for i in range(51)]
    txt_content = "\n".join(lan_ids)
    mock_file = UploadFile(
        filename="test.txt",
        file=BytesIO(txt_content.encode('utf-8')),
        content_type="text/plain"
    )
    mock_file.size = len(txt_content.encode('utf-8'))

    with pytest.MonkeyPatch().context() as m:
        m.setattr("utils.lan_id_validator.is_valid_lan_id", lambda x: True)
        with pytest.raises(InvalidLANIDCountException) as excinfo:
            await file_parser_service.parse_and_validate_file(mock_file, "testuser")
        assert "Expected between 2 and 50, but got 51." in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_parse_and_validate_file_too_large(file_parser_service):
    """Test handling of files exceeding max size."""
    large_content = b"a" * (settings.MAX_FILE_SIZE_MB * 1024 * 1024 + 1) # 1MB + 1 byte
    mock_file = UploadFile(
        filename="large.txt",
        file=BytesIO(large_content),
        content_type="text/plain"
    )
    mock_file.size = len(large_content)

    with pytest.raises(FileTooLargeException):
        await file_parser_service.parse_and_validate_file(mock_file, "testuser")

@pytest.mark.asyncio
async def test_parse_and_validate_file_empty_file(file_parser_service):
    """Test handling of an empty file."""
    mock_file = UploadFile(
        filename="empty.txt",
        file=BytesIO(b""),
        content_type="text/plain"
    )
    mock_file.size = 0

    with pytest.raises(InvalidLANIDCountException) as excinfo:
        await file_parser_service.parse_and_validate_file(mock_file, "testuser")
    assert "Expected between 2 and 50, but got 0." in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_parse_and_validate_file_unicode_error(file_parser_service):
    """Test handling of file with invalid unicode characters."""
    invalid_content = b'\x80abc' # Invalid UTF-8 sequence
    mock_file = UploadFile(
        filename="bad_encoding.txt",
        file=BytesIO(invalid_content),
        content_type="text/plain"
    )
    mock_file.size = len(invalid_content)

    with pytest.raises(InvalidFileFormatException) as excinfo:
        await file_parser_service.parse_and_validate_file(mock_file, "testuser")
    assert "File content is not valid UTF-8." in str(excinfo.value.detail)