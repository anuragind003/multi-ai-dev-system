import pytest
from httpx import AsyncClient
from models import TestProject, UserRole, TestStatus
from services import TestProjectService
from sqlalchemy.future import select

@pytest.mark.asyncio
async def test_create_test_project_as_tester(client: AsyncClient, test_user: User, test_user_token: str):
    project_data = {
        "name": "Web App Pen Test",
        "description": "Penetration test for the main web application.",
        "status": "pending"
    }
    response = await client.post(
        "/security-testing/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Web App Pen Test"
    assert data["owner_id"] == test_user.id
    assert data["status"] == "pending"
    assert "id" in data

    # Verify in DB
    project_service = TestProjectService(client.app.dependency_overrides.get(lambda: None)()) # Access overridden db_session
    project_in_db = await project_service.get_project_by_id(data["id"])
    assert project_in_db is not None
    assert project_in_db.name == "Web App Pen Test"

@pytest.mark.asyncio
async def test_create_test_project_as_admin(client: AsyncClient, admin_user: User, admin_user_token: str):
    project_data = {
        "name": "Network Scan Project",
        "description": "Vulnerability scan for internal network.",
        "status": "in_progress"
    }
    response = await client.post(
        "/security-testing/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {admin_user_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Network Scan Project"
    assert data["owner_id"] == admin_user.id
    assert data["status"] == "in_progress"

@pytest.mark.asyncio
async def test_create_test_project_unauthorized(client: AsyncClient, viewer_user_token: str):
    project_data = {
        "name": "Unauthorized Project",
        "description": "Should not be created."
    }
    # Viewer user should not be able to create
    response = await client.post(
        "/security-testing/projects",
        json=project_data,
        headers={"Authorization": f"Bearer {viewer_user_token}"}
    )
    assert response.status_code == 403 # Forbidden

    # No token
    response = await client.post(
        "/security-testing/projects",
        json=project_data
    )
    assert response.status_code == 401 # Unauthorized

@pytest.fixture
async def create_test_project_fixture(db_session, test_user):
    project = TestProject(
        name="Fixture Project",
        description="A project created by fixture.",
        owner_id=test_user.id,
        status=TestStatus.PENDING
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project

@pytest.mark.asyncio
async def test_get_all_test_projects(client: AsyncClient, test_user_token: str, create_test_project_fixture: TestProject):
    response = await client.get(
        "/security-testing/projects",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1 # At least the fixture project
    assert any(p["name"] == "Fixture Project" for p in data)

@pytest.mark.asyncio
async def test_get_test_project_by_id(client: AsyncClient, test_user_token: str, create_test_project_fixture: TestProject):
    response = await client.get(
        f"/security-testing/projects/{create_test_project_fixture.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == create_test_project_fixture.id
    assert data["name"] == create_test_project_fixture.name
    assert data["owner"]["id"] == create_test_project_fixture.owner_id # Check nested owner

@pytest.mark.asyncio
async def test_get_test_project_not_found(client: AsyncClient, test_user_token: str):
    response = await client.get(
        "/security-testing/projects/99999", # Non-existent ID
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Test project not found."

@pytest.mark.asyncio
async def test_update_test_project(client: AsyncClient, test_user: User, test_user_token: str, create_test_project_fixture: TestProject):
    update_data = {
        "description": "Updated description for the fixture project.",
        "status": "completed"
    }
    response = await client.put(
        f"/security-testing/projects/{create_test_project_fixture.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == create_test_project_fixture.id
    assert data["description"] == update_data["description"]
    assert data["status"] == update_data["status"]

    # Verify in DB
    project_service = TestProjectService(client.app.dependency_overrides.get(lambda: None)())
    project_in_db = await project_service.get_project_by_id(create_test_project_fixture.id)
    assert project_in_db.description == update_data["description"]
    assert project_in_db.status == TestStatus.COMPLETED

@pytest.mark.asyncio
async def test_update_test_project_forbidden(client: AsyncClient, viewer_user_token: str, create_test_project_fixture: TestProject):
    update_data = {
        "description": "Attempted update."
    }
    response = await client.put(
        f"/security-testing/projects/{create_test_project_fixture.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {viewer_user_token}"}
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "You do not have permission to update this project."

@pytest.mark.asyncio
async def test_delete_test_project_as_admin(client: AsyncClient, admin_user_token: str, create_test_project_fixture: TestProject):
    response = await client.delete(
        f"/security-testing/projects/{create_test_project_fixture.id}",
        headers={"Authorization": f"Bearer {admin_user_token}"}
    )
    assert response.status_code == 204

    # Verify deletion
    project_service = TestProjectService(client.app.dependency_overrides.get(lambda: None)())
    project_in_db = await project_service.get_project_by_id(create_test_project_fixture.id)
    assert project_in_db is None

@pytest.mark.asyncio
async def test_delete_test_project_forbidden(client: AsyncClient, test_user_token: str, create_test_project_fixture: TestProject):
    response = await client.delete(
        f"/security-testing/projects/{create_test_project_fixture.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert response.status_code == 403 # Tester cannot delete projects