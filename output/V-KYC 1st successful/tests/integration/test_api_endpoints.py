import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
from app.main import app
from app.services.s3_service import S3Service

# Mock S3Service for integration tests to avoid actual AWS calls
@pytest.fixture(autouse=True)
def mock_s3_service():
    """
    Mocks the S3Service instance used by the FastAPI app.
    This ensures that API tests do not make actual AWS calls.
    """
    with patch('app.main.S3Service', autospec=True) as MockS3Service:
        mock_instance = MockS3Service.return_value
        # Configure mock methods for common scenarios
        mock_instance.upload_file = AsyncMock(return_value=None)
        mock_instance.download_file = AsyncMock(return_value=(b"mock content", "text/plain"))
        mock_instance.delete_file = AsyncMock(return_value=None)
        mock_instance.list_files = AsyncMock(return_value=["mock_file1.txt", "mock_file2.jpg"])
        yield mock_instance

@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "S3 Temporary File Storage API is running."}

@pytest.mark.asyncio
async def test_upload_file_success(mock_s3_service):
    """Test successful file upload via API."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        file_content = b"This is a test file content."
        files = {"file": ("test_upload.txt", file_content, "text/plain")}
        response = await client.post("/upload", files=files)

    assert response.status_code == 201
    assert "uploaded successfully" in response.json()["message"]
    mock_s3_service.upload_file.assert_called_once_with(
        file_content, "temp/test_upload.txt", "text/plain"
    )

@pytest.mark.asyncio
async def test_upload_file_failure(mock_s3_service):
    """Test file upload failure due to S3 service error."""
    mock_s3_service.upload_file.side_effect = Exception("S3 service error")
    async with AsyncClient(app=app, base_url="http://test") as client:
        file_content = b"This is a test file content."
        files = {"file": ("test_upload.txt", file_content, "text/plain")}
        response = await client.post("/upload", files=files)

    assert response.status_code == 500
    assert "Failed to upload file" in response.json()["detail"]

@pytest.mark.asyncio
async def test_download_file_success(mock_s3_service):
    """Test successful file download via API."""
    object_name = "mock_file.txt"
    mock_s3_service.download_file.return_value = (b"mock file data", "text/plain")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/download/{object_name}")

    assert response.status_code == 200
    assert response.content == b"mock file data"
    assert response.headers["content-type"] == "text/plain"
    assert f"attachment; filename={object_name}" in response.headers["content-disposition"]
    mock_s3_service.download_file.assert_called_once_with(object_name)

@pytest.mark.asyncio
async def test_download_file_not_found(mock_s3_service):
    """Test file download when file not found."""
    object_name = "non_existent_file.txt"
    mock_s3_service.download_file.side_effect = HTTPException(status_code=404, detail="File not found")

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/download/{object_name}")

    assert response.status_code == 404
    assert "File not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_file_success(mock_s3_service):
    """Test successful file deletion via API."""
    object_name = "file_to_delete.txt"
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/delete/{object_name}")

    assert response.status_code == 200
    assert "deleted successfully" in response.json()["message"]
    mock_s3_service.delete_file.assert_called_once_with(object_name)

@pytest.mark.asyncio
async def test_delete_file_failure(mock_s3_service):
    """Test file deletion failure due to S3 service error."""
    object_name = "file_to_delete.txt"
    mock_s3_service.delete_file.side_effect = Exception("S3 deletion error")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/delete/{object_name}")

    assert response.status_code == 500
    assert "Failed to delete file" in response.json()["detail"]

@pytest.mark.asyncio
async def test_list_files_success(mock_s3_service):
    """Test successful listing of files via API."""
    mock_s3_service.list_files.return_value = ["file_a.txt", "file_b.pdf"]
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/list")

    assert response.status_code == 200
    assert response.json() == ["file_a.txt", "file_b.pdf"]
    mock_s3_service.list_files.assert_called_once()

@pytest.mark.asyncio
async def test_list_files_failure(mock_s3_service):
    """Test listing files failure due to S3 service error."""
    mock_s3_service.list_files.side_effect = Exception("S3 list error")
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/list")

    assert response.status_code == 500
    assert "Failed to list files" in response.json()["detail"]