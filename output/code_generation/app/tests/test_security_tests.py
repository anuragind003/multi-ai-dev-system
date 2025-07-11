import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from main import app
from database import get_db, Base, engine
from app.models.security_test import User, UserRole, SecurityTest, TestStatus, Vulnerability, Finding
from app.core.security import get_password_hash
from config import settings

# --- Test Database Setup ---
@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """
    Sets up and tears down the test database for the entire test session.
    """
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all) # Clean slate
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Drop tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def db_session_override():
    """
    Provides a fresh, independent database session for each test function.
    Rolls back transactions after each test.
    """
    async with engine.connect() as connection:
        async with connection.begin() as transaction:
            session = AsyncSession(bind=connection)
            yield session
            await transaction.rollback() # Rollback changes after each test
            await session.close()

@pytest.fixture(scope="function", autouse=True)
async def override_get_db(db_session_override):
    """
    Overrides the get_db dependency in FastAPI to use the test session.
    """
    app.dependency_overrides[get_db] = lambda: db_session_override

# --- Test Users Fixtures ---
@pytest.fixture
async def create_test_users(db_session_override: AsyncSession):
    """Creates test users (admin, tester, viewer) for authentication."""
    admin_user = User(
        username="testadmin",
        hashed_password=get_password_hash("adminpass"),
        email="admin@example.com",
        role=UserRole.ADMIN,
        is_active=True
    )
    tester_user = User(
        username="testtester",
        hashed_password=get_password_hash("testerpass"),
        email="tester@example.com",
        role=UserRole.TESTER,
        is_active=True
    )
    viewer_user = User(
        username="testviewer",
        hashed_password=get_password_hash("viewerpass"),
        email="viewer@example.com",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session_override.add_all([admin_user, tester_user, viewer_user])
    await db_session_override.commit()
    await db_session_override.refresh(admin_user)
    await db_session_override.refresh(tester_user)
    await db_session_override.refresh(viewer_user)
    return {
        "admin": admin_user,
        "tester": tester_user,
        "viewer": viewer_user
    }

@pytest.fixture
async def admin_token(create_test_users: dict, client: AsyncClient):
    """Gets an access token for the admin user."""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token",
        data={"username": "testadmin", "password": "adminpass"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def tester_token(create_test_users: dict, client: AsyncClient):
    """Gets an access token for the tester user."""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token",
        data={"username": "testtester", "password": "testerpass"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def viewer_token(create_test_users: dict, client: AsyncClient):
    """Gets an access token for the viewer user."""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token",
        data={"username": "testviewer", "password": "viewerpass"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

@pytest.fixture
async def client():
    """Provides an asynchronous test client for FastAPI."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

# --- Security Test Service Tests ---

@pytest.mark.asyncio
async def test_create_security_test(db_session_override: AsyncSession, admin_token: str, create_test_users: dict, client: AsyncClient):
    """Test creating a security test as an admin."""
    tester_user = create_test_users["tester"]
    test_data = {
        "name": "Web App Pen Test",
        "description": "Full penetration test for main web application.",
        "test_type": "Penetration Test",
        "target_scope": "https://example.com",
        "status": "pending",
        "assigned_to": tester_user.id
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/",
        json=test_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    created_test = response.json()
    assert created_test["name"] == test_data["name"]
    assert created_test["status"] == "pending"
    assert created_test["assigned_to"] == tester_user.id

    # Verify in DB
    result = await db_session_override.execute(select(SecurityTest).filter_by(id=created_test["id"]))
    db_test = result.scalars().first()
    assert db_test is not None
    assert db_test.name == test_data["name"]

@pytest.mark.asyncio
async def test_create_security_test_as_tester(db_session_override: AsyncSession, tester_token: str, client: AsyncClient):
    """Test creating a security test as a tester."""
    test_data = {
        "name": "API Vulnerability Scan",
        "description": "Automated scan for API endpoints.",
        "test_type": "Vulnerability Scan",
        "target_scope": "api.example.com",
        "status": "in_progress"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/",
        json=test_data,
        headers={"Authorization": f"Bearer {tester_token}"}
    )
    assert response.status_code == 201
    assert response.json()["name"] == test_data["name"]

@pytest.mark.asyncio
async def test_create_security_test_forbidden_as_viewer(viewer_token: str, client: AsyncClient):
    """Test creating a security test as a viewer (should be forbidden)."""
    test_data = {
        "name": "Forbidden Test",
        "description": "Should not be created.",
        "test_type": "Penetration Test",
        "target_scope": "forbidden.com"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/",
        json=test_data,
        headers={"Authorization": f"Bearer {viewer_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_all_security_tests(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test retrieving all security tests."""
    # Create a test directly in DB for retrieval
    test1 = SecurityTest(name="Test 1", test_type="PT", target_scope="scope1")
    test2 = SecurityTest(name="Test 2", test_type="VS", target_scope="scope2", status=TestStatus.COMPLETED)
    db_session_override.add_all([test1, test2])
    await db_session_override.commit()
    await db_session_override.refresh(test1)
    await db_session_override.refresh(test2)

    response = await client.get(
        f"{settings.API_V1_STR}/security-tests/",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    tests = response.json()
    assert len(tests) >= 2 # Account for tests created in other tests
    assert any(t["name"] == "Test 1" for t in tests)
    assert any(t["name"] == "Test 2" for t in tests)

@pytest.mark.asyncio
async def test_get_security_test_by_id(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test retrieving a single security test by ID."""
    test = SecurityTest(name="Specific Test", test_type="PT", target_scope="specific.com")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    response = await client.get(
        f"{settings.API_V1_STR}/security-tests/{test.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    retrieved_test = response.json()
    assert retrieved_test["id"] == test.id
    assert retrieved_test["name"] == test.name

@pytest.mark.asyncio
async def test_get_security_test_not_found(admin_token: str, client: AsyncClient):
    """Test retrieving a non-existent security test."""
    response = await client.get(
        f"{settings.API_V1_STR}/security-tests/99999",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]

@pytest.mark.asyncio
async def test_update_security_test(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test updating a security test."""
    test = SecurityTest(name="Old Name", test_type="PT", target_scope="old.com")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    update_data = {"name": "New Name", "status": "completed"}
    response = await client.put(
        f"{settings.API_V1_STR}/security-tests/{test.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    updated_test = response.json()
    assert updated_test["name"] == "New Name"
    assert updated_test["status"] == "completed"

    # Verify in DB
    result = await db_session_override.execute(select(SecurityTest).filter_by(id=test.id))
    db_test = result.scalars().first()
    assert db_test.name == "New Name"
    assert db_test.status == TestStatus.COMPLETED

@pytest.mark.asyncio
async def test_update_security_test_forbidden_status_change(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test updating a completed security test to a different status (should be forbidden)."""
    test = SecurityTest(name="Completed Test", test_type="PT", target_scope="scope", status=TestStatus.COMPLETED)
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    update_data = {"status": "in_progress"}
    response = await client.put(
        f"{settings.API_V1_STR}/security-tests/{test.id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "Cannot change status of a completed test." in response.json()["detail"]

@pytest.mark.asyncio
async def test_delete_security_test(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test deleting a security test."""
    test = SecurityTest(name="Test to Delete", test_type="PT", target_scope="delete.com")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    response = await client.delete(
        f"{settings.API_V1_STR}/security-tests/{test.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

    # Verify deletion in DB
    result = await db_session_override.execute(select(SecurityTest).filter_by(id=test.id))
    db_test = result.scalars().first()
    assert db_test is None

@pytest.mark.asyncio
async def test_delete_security_test_forbidden_as_tester(db_session_override: AsyncSession, tester_token: str, client: AsyncClient):
    """Test deleting a security test as a tester (should be forbidden)."""
    test = SecurityTest(name="Test to Delete (Forbidden)", test_type="PT", target_scope="forbidden.com")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    response = await client.delete(
        f"{settings.API_V1_STR}/security-tests/{test.id}",
        headers={"Authorization": f"Bearer {tester_token}"}
    )
    assert response.status_code == 403
    assert "Not enough permissions" in response.json()["detail"]

# --- Vulnerability Service Tests ---

@pytest.mark.asyncio
async def test_create_vulnerability(db_session_override: AsyncSession, admin_token: str, create_test_users: dict, client: AsyncClient):
    """Test creating a vulnerability."""
    test = SecurityTest(name="Test for Vuln", test_type="PT", target_scope="scope")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    vuln_data = {
        "security_test_id": test.id,
        "name": "SQL Injection",
        "description": "Classic SQLi vulnerability.",
        "severity": "critical",
        "cvss_score": "9.8"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/{test.id}/vulnerabilities",
        json=vuln_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    created_vuln = response.json()
    assert created_vuln["name"] == vuln_data["name"]
    assert created_vuln["security_test_id"] == test.id
    assert created_vuln["reported_by"] == create_test_users["admin"].id

    # Verify in DB
    result = await db_session_override.execute(select(Vulnerability).filter_by(id=created_vuln["id"]))
    db_vuln = result.scalars().first()
    assert db_vuln is not None
    assert db_vuln.name == vuln_data["name"]

@pytest.mark.asyncio
async def test_create_vulnerability_bad_test_id(admin_token: str, client: AsyncClient):
    """Test creating a vulnerability with mismatching test ID in path and body."""
    vuln_data = {
        "security_test_id": 999, # Mismatch
        "name": "Mismatch Vuln",
        "description": "Should fail.",
        "severity": "low"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/1/vulnerabilities", # Path ID is 1
        json=vuln_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 400
    assert "must match path parameter" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_vulnerabilities_for_test(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test retrieving vulnerabilities for a specific test."""
    test = SecurityTest(name="Test with Vulns", test_type="PT", target_scope="scope")
    db_session_override.add(test)
    await db_session_override.commit()
    await db_session_override.refresh(test)

    vuln1 = Vulnerability(security_test_id=test.id, name="XSS", severity="high")
    vuln2 = Vulnerability(security_test_id=test.id, name="CSRF", severity="medium")
    db_session_override.add_all([vuln1, vuln2])
    await db_session_override.commit()

    response = await client.get(
        f"{settings.API_V1_STR}/security-tests/{test.id}/vulnerabilities",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    vulns = response.json()
    assert len(vulns) >= 2
    assert any(v["name"] == "XSS" for v in vulns)
    assert any(v["name"] == "CSRF" for v in vulns)

# --- Finding Service Tests ---

@pytest.mark.asyncio
async def test_create_finding(db_session_override: AsyncSession, admin_token: str, create_test_users: dict, client: AsyncClient):
    """Test creating a finding."""
    test = SecurityTest(name="Test for Finding", test_type="PT", target_scope="scope")
    vuln = Vulnerability(security_test_id=test.id, name="Vuln for Finding", severity="low")
    db_session_override.add_all([test, vuln])
    await db_session_override.commit()
    await db_session_override.refresh(test)
    await db_session_override.refresh(vuln)

    finding_data = {
        "vulnerability_id": vuln.id,
        "title": "Specific Finding 1",
        "details": "Details of the finding.",
        "status": "open",
        "affected_asset": "192.168.1.1"
    }
    response = await client.post(
        f"{settings.API_V1_STR}/security-tests/vulnerabilities/{vuln.id}/findings",
        json=finding_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201
    created_finding = response.json()
    assert created_finding["title"] == finding_data["title"]
    assert created_finding["vulnerability_id"] == vuln.id
    assert created_finding["reported_by"] == create_test_users["admin"].id

    # Verify in DB
    result = await db_session_override.execute(select(Finding).filter_by(id=created_finding["id"]))
    db_finding = result.scalars().first()
    assert db_finding is not None
    assert db_finding.title == finding_data["title"]

@pytest.mark.asyncio
async def test_get_findings_for_vulnerability(db_session_override: AsyncSession, admin_token: str, client: AsyncClient):
    """Test retrieving findings for a specific vulnerability."""
    test = SecurityTest(name="Test for Finding List", test_type="PT", target_scope="scope")
    vuln = Vulnerability(security_test_id=test.id, name="Vuln for Finding List", severity="low")
    db_session_override.add_all([test, vuln])
    await db_session_override.commit()
    await db_session_override.refresh(test)
    await db_session_override.refresh(vuln)

    finding1 = Finding(vulnerability_id=vuln.id, title="Finding A", status="open")
    finding2 = Finding(vulnerability_id=vuln.id, title="Finding B", status="closed")
    db_session_override.add_all([finding1, finding2])
    await db_session_override.commit()

    response = await client.get(
        f"{settings.API_V1_STR}/security-tests/vulnerabilities/{vuln.id}/findings",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    findings = response.json()
    assert len(findings) >= 2
    assert any(f["title"] == "Finding A" for f in findings)
    assert any(f["title"] == "Finding B" for f in findings)