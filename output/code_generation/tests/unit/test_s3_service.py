import pytest
from unittest.mock import AsyncMock, MagicMock
from botocore.exceptions import ClientError
from fastapi import HTTPException, status
from app.services.s3_service import S3Service

# Mock AWS credentials and bucket for testing
MOCK_AWS_ACCESS_KEY_ID = "test_access_key"
MOCK_AWS_SECRET_ACCESS_KEY = "test_secret_key"
MOCK_AWS_REGION = "us-east-1"
MOCK_S3_BUCKET_NAME = "test-bucket"

@pytest.fixture
def s3_service():
    """Fixture to provide an S3Service instance with mocked aiobotocore."""
    service = S3Service(
        aws_access_key_id=MOCK_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=MOCK_AWS_SECRET_ACCESS_KEY,
        aws_region=MOCK_AWS_REGION,
        bucket_name=MOCK_S3_BUCKET_NAME
    )
    # Mock the internal _get_s3_client method to return a mock client
    service._get_s3_client = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_upload_file_success(s3_service):
    """Test successful file upload."""
    mock_client = AsyncMock()
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    file_content = b"test content"
    object_name = "test_file.txt"
    content_type = "text/plain"

    await s3_service.upload_file(file_content, object_name, content_type)

    mock_client.put_object.assert_called_once_with(
        Bucket=MOCK_S3_BUCKET_NAME,
        Key=object_name,
        Body=file_content,
        ContentType=content_type
    )

@pytest.mark.asyncio
async def test_upload_file_access_denied(s3_service):
    """Test file upload with access denied error."""
    mock_client = AsyncMock()
    mock_client.put_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "PutObject"
    )
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await s3_service.upload_file(b"content", "file.txt")

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in exc_info.value.detail

@pytest.mark.asyncio
async def test_download_file_success(s3_service):
    """Test successful file download."""
    mock_client = AsyncMock()
    mock_body = AsyncMock()
    mock_body.read.return_value = b"downloaded content"
    mock_client.get_object.return_value = {
        "Body": mock_body,
        "ContentType": "text/plain"
    }
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    object_name = "download_file.txt"
    content, content_type = await s3_service.download_file(object_name)

    mock_client.get_object.assert_called_once_with(
        Bucket=MOCK_S3_BUCKET_NAME, Key=object_name
    )
    assert content == b"downloaded content"
    assert content_type == "text/plain"

@pytest.mark.asyncio
async def test_download_file_not_found(s3_service):
    """Test file download when file not found."""
    mock_client = AsyncMock()
    mock_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}, "GetObject"
    )
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await s3_service.download_file("non_existent_file.txt")

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in exc_info.value.detail

@pytest.mark.asyncio
async def test_delete_file_success(s3_service):
    """Test successful file deletion."""
    mock_client = AsyncMock()
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    object_name = "delete_file.txt"
    await s3_service.delete_file(object_name)

    mock_client.delete_object.assert_called_once_with(
        Bucket=MOCK_S3_BUCKET_NAME, Key=object_name
    )

@pytest.mark.asyncio
async def test_delete_file_access_denied(s3_service):
    """Test file deletion with access denied error."""
    mock_client = AsyncMock()
    mock_client.delete_object.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}, "DeleteObject"
    )
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    with pytest.raises(HTTPException) as exc_info:
        await s3_service.delete_file("file_to_delete.txt")

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Access denied" in exc_info.value.detail

@pytest.mark.asyncio
async def test_list_files_success(s3_service):
    """Test successful listing of files."""
    mock_client = AsyncMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "file1.txt"},
            {"Key": "folder/file2.jpg"}
        ]
    }
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    files = await s3_service.list_files()

    mock_client.list_objects_v2.assert_called_once_with(
        Bucket=MOCK_S3_BUCKET_NAME, Prefix=""
    )
    assert files == ["file1.txt", "folder/file2.jpg"]

@pytest.mark.asyncio
async def test_list_files_empty(s3_service):
    """Test listing files when bucket is empty."""
    mock_client = AsyncMock()
    mock_client.list_objects_v2.return_value = {"Contents": []}
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    files = await s3_service.list_files()

    assert files == []

@pytest.mark.asyncio
async def test_list_files_with_prefix(s3_service):
    """Test listing files with a specific prefix."""
    mock_client = AsyncMock()
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "temp/file1.txt"},
            {"Key": "temp/sub/file2.jpg"}
        ]
    }
    s3_service._get_s3_client.return_value.__aenter__.return_value = mock_client

    files = await s3_service.list_files(prefix="temp/")

    mock_client.list_objects_v2.assert_called_once_with(
        Bucket=MOCK_S3_BUCKET_NAME, Prefix="temp/"
    )
    assert files == ["temp/file1.txt", "temp/sub/file2.jpg"]