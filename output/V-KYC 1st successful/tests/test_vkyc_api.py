import pytest
from httpx import AsyncClient
from datetime import datetime
from schemas import VKYCRecordCreate, VKYCSearchParams
from middleware.security import get_current_user, MOCK_USERS_DB, User

@pytest.mark.asyncio
async def test_create_vkyc_record_success(client: AsyncClient, mock_nfs_file_handler):
    """Test successful creation of a VKYC record via API."""
    # Ensure the mock file handler reports the file exists
    mock_nfs_file_handler.mock_files["path/to/api_recording.mp4"] = b"api content"

    record_data = {
        "lan_id": "API001",
        "customer_name": "API Test Customer",
        "recording_date": datetime.now().isoformat(),
        "file_path": "path/to/api_recording.mp4",
        "status": "Active"
    }
    # Override get_current_user to return an admin user for this test
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))

    response = await client.post("/api/v1/vkyc/records", json=record_data)
    assert response.status_code == 201
    assert response.json()["lan_id"] == "API001"
    assert response.json()["customer_name"] == "API Test Customer"

@pytest.mark.asyncio
async def test_create_vkyc_record_unauthorized(client: AsyncClient):
    """Test creating a VKYC record without proper authorization."""
    # Override get_current_user to return a non-admin user
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))

    record_data = {
        "lan_id": "API002",
        "customer_name": "Unauthorized Customer",
        "recording_date": datetime.now().isoformat(),
        "file_path": "path/to/some_recording.mp4",
        "status": "Active"
    }
    response = await client.post("/api/v1/vkyc/records", json=record_data)
    assert response.status_code == 403 # Forbidden

@pytest.mark.asyncio
async def test_get_vkyc_records_success(client: AsyncClient, mock_nfs_file_handler):
    """Test retrieving VKYC records via API."""
    mock_nfs_file_handler.mock_files["path/to/rec_api1.mp4"] = b"content1"
    mock_nfs_file_handler.mock_files["path/to/rec_api2.mp4"] = b"content2"
    # Create some records first
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))
    await client.post("/api/v1/vkyc/records", json={
        "lan_id": "APIREC01", "customer_name": "API Rec 1",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/rec_api1.mp4"
    })
    await client.post("/api/v1/vkyc/records", json={
        "lan_id": "APIREC02", "customer_name": "API Rec 2",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/rec_api2.mp4"
    })

    # Now query as a regular user
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))
    response = await client.get("/api/v1/vkyc/records?lan_id=APIREC01")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["lan_id"] == "APIREC01"

@pytest.mark.asyncio
async def test_download_vkyc_recording_success(client: AsyncClient, mock_nfs_file_handler):
    """Test successful download of a VKYC recording via API."""
    mock_nfs_file_handler.mock_files["path/to/download_test.mp4"] = b"mock video content for download"
    # Create a record
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))
    create_response = await client.post("/api/v1/vkyc/records", json={
        "lan_id": "APIDL01", "customer_name": "API Download Test",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/download_test.mp4"
    })
    record_id = create_response.json()["id"]

    # Download as a regular user
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))
    response = await client.get(f"/api/v1/vkyc/records/{record_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "video/mp4"
    assert response.headers["content-disposition"].startswith("attachment; filename=APIDL01_")
    assert response.content == b"mock video content for download"

@pytest.mark.asyncio
async def test_download_vkyc_recording_not_found(client: AsyncClient):
    """Test downloading a non-existent VKYC record."""
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))
    response = await client.get("/api/v1/vkyc/records/9999/download")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_bulk_upload_success(client: AsyncClient, mock_nfs_file_handler):
    """Test successful bulk upload via API."""
    mock_nfs_file_handler.mock_files["path/to/bulk_api1.mp4"] = b"content1"
    mock_nfs_file_handler.mock_files["path/to/bulk_api2.mp4"] = b"content2"
    # Create some records for the bulk upload to find
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))
    await client.post("/api/v1/vkyc/records", json={
        "lan_id": "BULKAPI01", "customer_name": "Bulk API 1",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/bulk_api1.mp4"
    })
    await client.post("/api/v1/vkyc/records", json={
        "lan_id": "BULKAPI02", "customer_name": "Bulk API 2",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/bulk_api2.mp4"
    })

    csv_content = "LAN_ID\nBULKAPI01\nBULKAPI03\nBULKAPI02".encode('utf-8')
    files = {"file": ("test.csv", csv_content, "text/csv")}

    response = await client.post("/api/v1/vkyc/bulk-upload", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["total_records_processed"] == 3
    assert data["successful_records"] == 2
    assert data["failed_records"] == 1
    assert "BULKAPI03" in data["failed_lan_ids"]

@pytest.mark.asyncio
async def test_bulk_upload_invalid_file_type(client: AsyncClient):
    """Test bulk upload with an invalid file type via API."""
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))
    pdf_content = b"%PDF-1.4\n..."
    files = {"file": ("test.pdf", pdf_content, "application/pdf")}
    response = await client.post("/api/v1/vkyc/bulk-upload", files=files)
    assert response.status_code == 422
    assert "Only CSV or TXT files are allowed" in response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_download_success(client: AsyncClient, mock_nfs_file_handler):
    """Test successful bulk download request via API."""
    mock_nfs_file_handler.mock_files["path/to/bdl1.mp4"] = b"bdl content 1"
    mock_nfs_file_handler.mock_files["path/to/bdl2.mp4"] = b"bdl content 2"
    # Create records
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["jane.admin"].model_dump(exclude={"hashed_password"}))
    create_resp1 = await client.post("/api/v1/vkyc/records", json={
        "lan_id": "APIBDL01", "customer_name": "API BDL 1",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/bdl1.mp4"
    })
    create_resp2 = await client.post("/api/v1/vkyc/records", json={
        "lan_id": "APIBDL02", "customer_name": "API BDL 2",
        "recording_date": datetime.now().isoformat(), "file_path": "path/to/bdl2.mp4"
    })
    record_id1 = create_resp1.json()["id"]
    record_id2 = create_resp2.json()["id"]

    # Request bulk download
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))
    request_data = {"lan_ids": ["APIBDL01", "APIBDL03", "APIBDL02"]} # APIBDL03 is non-existent
    response = await client.post("/api/v1/vkyc/bulk-download", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "Prepared 2 download links" in data["message"]
    assert len(data["download_links"]) == 2
    assert f"/api/v1/vkyc/records/{record_id1}/download" in data["download_links"]
    assert f"/api/v1/vkyc/records/{record_id2}/download" in data["download_links"]
    assert len(data["failed_lan_ids"]) == 1
    assert "APIBDL03" in data["failed_lan_ids"]

@pytest.mark.asyncio
async def test_bulk_download_too_many_lan_ids(client: AsyncClient):
    """Test bulk download request with too many LAN IDs."""
    client.app.dependency_overrides[get_current_user] = lambda: User(**MOCK_USERS_DB["john.doe"].model_dump(exclude={"hashed_password"}))
    request_data = {"lan_ids": [f"LAN{i}" for i in range(12)]} # 12 IDs, max is 10
    response = await client.post("/api/v1/vkyc/bulk-download", json=request_data)
    assert response.status_code == 422
    assert "Maximum 10 LAN IDs allowed per bulk download request." in response.json()["detail"]

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test the health check endpoint."""
    response = await client.get("/api/v1/auth/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "message": "VKYC Backend is running."}