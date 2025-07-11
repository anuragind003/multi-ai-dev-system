import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from models import KYCRecord, KYCStatus, UserRole
from schemas import KYCRecordCreate, KYCRecordUpdate, BulkUploadRequest
import io
import csv

# Assuming conftest.py provides `client`, `test_db`, `admin_token`, `auditor_token`, `manager_token`

@pytest.mark.asyncio
async def test_create_kyc_record_auditor(client: AsyncClient, auditor_token: str):
    """Test creating a KYC record as an auditor."""
    kyc_data = {
        "lan_id": "LAN001",
        "customer_name": "Test Customer 1",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN001.mp4"
    }
    response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["lan_id"] == "LAN001"
    assert data["status"] == KYCStatus.PENDING.value
    assert "id" in data

@pytest.mark.asyncio
async def test_create_kyc_record_duplicate_file_path(client: AsyncClient, auditor_token: str):
    """Test creating a KYC record with a duplicate file path."""
    kyc_data = {
        "lan_id": "LAN002",
        "customer_name": "Test Customer 2",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/duplicate.mp4"
    }
    # Create first record
    response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 201

    # Attempt to create second record with same file_path
    response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_kyc_record(client: AsyncClient, auditor_token: str):
    """Test retrieving a KYC record."""
    kyc_data = {
        "lan_id": "LAN003",
        "customer_name": "Test Customer 3",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN003.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    get_response = await client.get(
        f"/api/v1/kyc/{record_id}",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["id"] == record_id
    assert data["lan_id"] == "LAN003"

@pytest.mark.asyncio
async def test_get_kyc_record_not_found(client: AsyncClient, auditor_token: str):
    """Test retrieving a non-existent KYC record."""
    response = await client.get(
        "/api/v1/kyc/99999",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_all_kyc_records(client: AsyncClient, auditor_token: str):
    """Test retrieving all KYC records."""
    # Create a few records
    for i in range(4, 6):
        await client.post(
            "/api/v1/kyc/",
            json={
                "lan_id": f"LAN00{i}",
                "customer_name": f"Customer {i}",
                "recording_date": datetime.now(timezone.utc).isoformat(),
                "file_path": f"/nfs/path/to/LAN00{i}.mp4"
            },
            headers={"Authorization": f"Bearer {auditor_token}"}
        )
    response = await client.get(
        "/api/v1/kyc/",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 2 # Should have at least the ones created in this test

@pytest.mark.asyncio
async def test_update_kyc_record_auditor(client: AsyncClient, auditor_token: str):
    """Test updating a KYC record as an auditor (limited fields)."""
    kyc_data = {
        "lan_id": "LAN006",
        "customer_name": "Original Name",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN006.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    update_data = {
        "customer_name": "Updated Name",
        "file_path": "/nfs/path/to/LAN006_updated.mp4"
    }
    response = await client.put(
        f"/api/v1/kyc/{record_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == "Updated Name"
    assert data["file_path"] == "/nfs/path/to/LAN006_updated.mp4"
    assert data["status"] == KYCStatus.PENDING.value # Status should not change by auditor

@pytest.mark.asyncio
async def test_update_kyc_record_auditor_forbidden_status_change(client: AsyncClient, auditor_token: str):
    """Test auditor attempting to change KYC record status (should be forbidden)."""
    kyc_data = {
        "lan_id": "LAN007",
        "customer_name": "Forbidden Test",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN007.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    update_data = {"status": KYCStatus.APPROVED.value}
    response = await client.put(
        f"/api/v1/kyc/{record_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 403
    assert "Only Managers or Admins can change KYC record status" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_kyc_record_manager_status_change(client: AsyncClient, manager_token: str, auditor_token: str):
    """Test manager changing KYC record status."""
    kyc_data = {
        "lan_id": "LAN008",
        "customer_name": "Manager Test",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN008.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"} # Created by auditor
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    update_data = {"status": KYCStatus.APPROVED.value}
    response = await client.put(
        f"/api/v1/kyc/{record_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == KYCStatus.APPROVED.value
    assert data["approved_by_user_id"] is not None # Should be set to manager's ID

@pytest.mark.asyncio
async def test_delete_kyc_record_manager(client: AsyncClient, manager_token: str, auditor_token: str):
    """Test deleting a KYC record as a manager."""
    kyc_data = {
        "lan_id": "LAN009",
        "customer_name": "Delete Test",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN009.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/kyc/{record_id}",
        headers={"Authorization": f"Bearer {manager_token}"}
    )
    assert delete_response.status_code == 204

    get_response = await client.get(
        f"/api/v1/kyc/{record_id}",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert get_response.status_code == 404

@pytest.mark.asyncio
async def test_delete_kyc_record_auditor_forbidden(client: AsyncClient, auditor_token: str):
    """Test auditor attempting to delete a KYC record (should be forbidden)."""
    kyc_data = {
        "lan_id": "LAN010",
        "customer_name": "Forbidden Delete Test",
        "recording_date": datetime.now(timezone.utc).isoformat(),
        "file_path": "/nfs/path/to/LAN010.mp4"
    }
    create_response = await client.post(
        "/api/v1/kyc/",
        json=kyc_data,
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert create_response.status_code == 201
    record_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"/api/v1/kyc/{record_id}",
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert delete_response.status_code == 403
    assert "Not enough permissions" in delete_response.json()["detail"]

@pytest.mark.asyncio
async def test_bulk_upload_kyc_records(client: AsyncClient, auditor_token: str):
    """Test bulk uploading KYC records via CSV."""
    csv_content = """lan_id,customer_name,recording_date,file_path
LAN_BULK_01,Bulk Customer 1,2023-01-01T10:00:00Z,/nfs/bulk/01.mp4
LAN_BULK_02,Bulk Customer 2,2023-01-02T11:00:00Z,/nfs/bulk/02.mp4
LAN_BULK_03,Bulk Customer 3,2023-01-03T12:00:00Z,/nfs/bulk/03.mp4
"""
    csv_file = io.BytesIO(csv_content.encode('utf-8'))

    response = await client.post(
        "/api/v1/kyc/bulk-upload",
        files={"file": ("bulk_upload.csv", csv_file, "text/csv")},
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    assert data["successful_uploads"] == 3
    assert data["failed_uploads"] == 0
    assert len(data["details"]) == 3
    assert data["details"][0]["status"] == "success"

@pytest.mark.asyncio
async def test_bulk_upload_kyc_records_with_duplicates(client: AsyncClient, auditor_token: str):
    """Test bulk uploading KYC records with some duplicates."""
    # Create one record manually first to ensure a duplicate
    await client.post(
        "/api/v1/kyc/",
        json={
            "lan_id": "LAN_DUP_01",
            "customer_name": "Duplicate Customer",
            "recording_date": datetime.now(timezone.utc).isoformat(),
            "file_path": "/nfs/bulk/duplicate.mp4"
        },
        headers={"Authorization": f"Bearer {auditor_token}"}
    )

    csv_content = """lan_id,customer_name,recording_date,file_path
LAN_DUP_01,Bulk Customer 1,2023-02-01T10:00:00Z,/nfs/bulk/duplicate.mp4
LAN_DUP_02,Bulk Customer 2,2023-02-02T11:00:00Z,/nfs/bulk/04.mp4
LAN_DUP_03,Bulk Customer 3,2023-02-03T12:00:00Z,/nfs/bulk/05.mp4
"""
    csv_file = io.BytesIO(csv_content.encode('utf-8'))

    response = await client.post(
        "/api/v1/kyc/bulk-upload",
        files={"file": ("bulk_upload_dup.csv", csv_file, "text/csv")},
        headers={"Authorization": f"Bearer {auditor_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_records"] == 3
    assert data["successful_uploads"] == 2
    assert data["failed_uploads"] == 1
    assert len(data["details"]) == 3
    assert data["details"][0]["status"] == "failed"
    assert "already exists" in data["details"][0]["message"]
    assert data["details"][1]["status"] == "success"
    assert data["details"][2]["status"] == "success"