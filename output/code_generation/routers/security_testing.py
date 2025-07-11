from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional, Annotated
from schemas import (
    TestProjectCreate, TestProjectUpdate, TestProjectResponse,
    VulnerabilityScanCreate, VulnerabilityScanUpdate, VulnerabilityScanResponse,
    VulnerabilityCreate, VulnerabilityUpdate, VulnerabilityResponse,
    PenetrationTestCreate, PenetrationTestUpdate, PenetrationTestResponse,
    PenetrationTestFindingCreate, PenetrationTestFindingUpdate, PenetrationTestFindingResponse,
    UserResponse # For nested responses
)
from services import (
    TestProjectService, VulnerabilityScanService, VulnerabilityService,
    PenetrationTestService, PenetrationTestFindingService
)
from dependencies import DBSession, get_current_tester_or_admin_user, get_current_viewer_or_above_user, get_current_admin_user
from exceptions import NotFoundException, ForbiddenException, BadRequestException
from models import User
from fastapi_limiter.depends import RateLimiter
import logging

logger = logging.getLogger("security_testing_api")

router = APIRouter(prefix="/security-testing", tags=["Security Testing"])

# --- Test Project Endpoints ---
@router.post("/projects", response_model=TestProjectResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new test project",
             description="Allows 'tester' or 'admin' roles to create a new security test project.")
@RateLimiter(times=5, seconds=10) # Limit to 5 requests per 10 seconds
async def create_test_project(
    project_in: TestProjectCreate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    project_service = TestProjectService(db)
    try:
        new_project = await project_service.create_project(project_in, current_user.id)
        return new_project
    except Exception as e:
        logger.error(f"Error creating test project: {e}")
        raise

@router.get("/projects", response_model=List[TestProjectResponse],
            summary="Get all test projects",
            description="Retrieves a list of all security test projects. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=10, seconds=10)
async def get_all_test_projects(
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    project_service = TestProjectService(db)
    projects = await project_service.get_projects(skip=skip, limit=limit)
    return projects

@router.get("/projects/{project_id}", response_model=TestProjectResponse,
            summary="Get a test project by ID",
            description="Retrieves details of a specific security test project by its ID. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=20, seconds=10)
async def get_test_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    return project

@router.put("/projects/{project_id}", response_model=TestProjectResponse,
            summary="Update a test project",
            description="Updates an existing security test project. Only 'tester' or 'admin' can update.")
@RateLimiter(times=5, seconds=10)
async def update_test_project(
    project_id: int,
    project_in: TestProjectUpdate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    # Authorization check: Only owner or admin can update
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to update this project.")

    updated_project = await project_service.update_project(project_id, project_in)
    return updated_project

@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a test project",
             description="Deletes a security test project. Only 'admin' can delete.")
@RateLimiter(times=2, seconds=10)
async def delete_test_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)], # Only admin can delete
    db: DBSession
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    await project_service.delete_project(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Vulnerability Scan Endpoints ---
@router.post("/projects/{project_id}/scans", response_model=VulnerabilityScanResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new vulnerability scan for a project",
             description="Adds a new vulnerability scan record to a specific test project. Accessible by 'tester' or 'admin'.")
@RateLimiter(times=5, seconds=10)
async def create_vulnerability_scan(
    project_id: int,
    scan_in: VulnerabilityScanCreate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    # Authorization check: Only project owner or admin can add scans
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to add scans to this project.")

    scan_service = VulnerabilityScanService(db)
    new_scan = await scan_service.create_scan(project_id, scan_in)
    return new_scan

@router.get("/projects/{project_id}/scans", response_model=List[VulnerabilityScanResponse],
            summary="Get all vulnerability scans for a project",
            description="Retrieves all vulnerability scans associated with a specific test project. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=10, seconds=10)
async def get_vulnerability_scans_for_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    scan_service = VulnerabilityScanService(db)
    scans = await scan_service.get_scans_for_project(project_id, skip=skip, limit=limit)
    return scans

@router.get("/scans/{scan_id}", response_model=VulnerabilityScanResponse,
            summary="Get a vulnerability scan by ID",
            description="Retrieves details of a specific vulnerability scan by its ID. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=20, seconds=10)
async def get_vulnerability_scan(
    scan_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession
):
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(scan_id)
    if not scan:
        raise NotFoundException(detail="Vulnerability scan not found.")
    return scan

@router.put("/scans/{scan_id}", response_model=VulnerabilityScanResponse,
            summary="Update a vulnerability scan",
            description="Updates an existing vulnerability scan. Only 'tester' or 'admin' can update.")
@RateLimiter(times=5, seconds=10)
async def update_vulnerability_scan(
    scan_id: int,
    scan_in: VulnerabilityScanUpdate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(scan_id)
    if not scan:
        raise NotFoundException(detail="Vulnerability scan not found.")
    # Authorization check: Only project owner or admin can update scans
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(scan.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to update this scan.")

    updated_scan = await scan_service.update_scan(scan_id, scan_in)
    return updated_scan

@router.delete("/scans/{scan_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a vulnerability scan",
             description="Deletes a vulnerability scan. Only 'admin' can delete.")
@RateLimiter(times=2, seconds=10)
async def delete_vulnerability_scan(
    scan_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: DBSession
):
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(scan_id)
    if not scan:
        raise NotFoundException(detail="Vulnerability scan not found.")
    await scan_service.delete_scan(scan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Vulnerability Endpoints ---
@router.post("/scans/{scan_id}/vulnerabilities", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a new vulnerability to a scan",
             description="Adds a new vulnerability finding to a specific vulnerability scan. Accessible by 'tester' or 'admin'.")
@RateLimiter(times=5, seconds=10)
async def create_vulnerability(
    scan_id: int,
    vuln_in: VulnerabilityCreate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(scan_id)
    if not scan:
        raise NotFoundException(detail="Vulnerability scan not found.")
    # Authorization check: Only project owner or admin can add vulnerabilities
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(scan.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to add vulnerabilities to this scan.")

    vuln_service = VulnerabilityService(db)
    new_vuln = await vuln_service.create_vulnerability(scan_id, vuln_in)
    return new_vuln

@router.get("/scans/{scan_id}/vulnerabilities", response_model=List[VulnerabilityResponse],
            summary="Get all vulnerabilities for a scan",
            description="Retrieves all vulnerability findings associated with a specific scan. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=10, seconds=10)
async def get_vulnerabilities_for_scan(
    scan_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(scan_id)
    if not scan:
        raise NotFoundException(detail="Vulnerability scan not found.")
    vuln_service = VulnerabilityService(db)
    vulnerabilities = await vuln_service.get_vulnerabilities_for_scan(scan_id, skip=skip, limit=limit)
    return vulnerabilities

@router.get("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse,
            summary="Get a vulnerability by ID",
            description="Retrieves details of a specific vulnerability finding by its ID. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=20, seconds=10)
async def get_vulnerability(
    vuln_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession
):
    vuln_service = VulnerabilityService(db)
    vuln = await vuln_service.get_vulnerability_by_id(vuln_id)
    if not vuln:
        raise NotFoundException(detail="Vulnerability not found.")
    return vuln

@router.put("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse,
            summary="Update a vulnerability",
            description="Updates an existing vulnerability finding. Only 'tester' or 'admin' can update.")
@RateLimiter(times=5, seconds=10)
async def update_vulnerability(
    vuln_id: int,
    vuln_in: VulnerabilityUpdate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    vuln_service = VulnerabilityService(db)
    vuln = await vuln_service.get_vulnerability_by_id(vuln_id)
    if not vuln:
        raise NotFoundException(detail="Vulnerability not found.")
    # Authorization check: Only project owner or admin can update vulnerabilities
    scan_service = VulnerabilityScanService(db)
    scan = await scan_service.get_scan_by_id(vuln.scan_id)
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(scan.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to update this vulnerability.")

    updated_vuln = await vuln_service.update_vulnerability(vuln_id, vuln_in)
    return updated_vuln

@router.delete("/vulnerabilities/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a vulnerability",
             description="Deletes a vulnerability finding. Only 'admin' can delete.")
@RateLimiter(times=2, seconds=10)
async def delete_vulnerability(
    vuln_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: DBSession
):
    vuln_service = VulnerabilityService(db)
    vuln = await vuln_service.get_vulnerability_by_id(vuln_id)
    if not vuln:
        raise NotFoundException(detail="Vulnerability not found.")
    await vuln_service.delete_vulnerability(vuln_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Penetration Test Endpoints ---
@router.post("/projects/{project_id}/penetration-tests", response_model=PenetrationTestResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new penetration test for a project",
             description="Adds a new penetration test record to a specific test project. Accessible by 'tester' or 'admin'.")
@RateLimiter(times=5, seconds=10)
async def create_penetration_test(
    project_id: int,
    pen_test_in: PenetrationTestCreate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    # Authorization check: Only project owner or admin can add pen tests
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to add penetration tests to this project.")

    pen_test_service = PenetrationTestService(db)
    new_pen_test = await pen_test_service.create_pen_test(project_id, pen_test_in)
    return new_pen_test

@router.get("/projects/{project_id}/penetration-tests", response_model=List[PenetrationTestResponse],
            summary="Get all penetration tests for a project",
            description="Retrieves all penetration tests associated with a specific test project. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=10, seconds=10)
async def get_penetration_tests_for_project(
    project_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(project_id)
    if not project:
        raise NotFoundException(detail="Test project not found.")
    pen_test_service = PenetrationTestService(db)
    pen_tests = await pen_test_service.get_pen_tests_for_project(project_id, skip=skip, limit=limit)
    return pen_tests

@router.get("/penetration-tests/{pen_test_id}", response_model=PenetrationTestResponse,
            summary="Get a penetration test by ID",
            description="Retrieves details of a specific penetration test by its ID. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=20, seconds=10)
async def get_penetration_test(
    pen_test_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession
):
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(pen_test_id)
    if not pen_test:
        raise NotFoundException(detail="Penetration test not found.")
    return pen_test

@router.put("/penetration-tests/{pen_test_id}", response_model=PenetrationTestResponse,
            summary="Update a penetration test",
            description="Updates an existing penetration test. Only 'tester' or 'admin' can update.")
@RateLimiter(times=5, seconds=10)
async def update_penetration_test(
    pen_test_id: int,
    pen_test_in: PenetrationTestUpdate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(pen_test_id)
    if not pen_test:
        raise NotFoundException(detail="Penetration test not found.")
    # Authorization check: Only project owner or admin can update pen tests
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(pen_test.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to update this penetration test.")

    updated_pen_test = await pen_test_service.update_pen_test(pen_test_id, pen_test_in)
    return updated_pen_test

@router.delete("/penetration-tests/{pen_test_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a penetration test",
             description="Deletes a penetration test. Only 'admin' can delete.")
@RateLimiter(times=2, seconds=10)
async def delete_penetration_test(
    pen_test_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: DBSession
):
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(pen_test_id)
    if not pen_test:
        raise NotFoundException(detail="Penetration test not found.")
    await pen_test_service.delete_pen_test(pen_test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# --- Penetration Test Finding Endpoints ---
@router.post("/penetration-tests/{pen_test_id}/findings", response_model=PenetrationTestFindingResponse, status_code=status.HTTP_201_CREATED,
             summary="Add a new finding to a penetration test",
             description="Adds a new finding to a specific penetration test. Accessible by 'tester' or 'admin'.")
@RateLimiter(times=5, seconds=10)
async def create_penetration_test_finding(
    pen_test_id: int,
    finding_in: PenetrationTestFindingCreate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(pen_test_id)
    if not pen_test:
        raise NotFoundException(detail="Penetration test not found.")
    # Authorization check: Only project owner or admin can add findings
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(pen_test.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to add findings to this penetration test.")

    finding_service = PenetrationTestFindingService(db)
    new_finding = await finding_service.create_finding(pen_test_id, finding_in)
    return new_finding

@router.get("/penetration-tests/{pen_test_id}/findings", response_model=List[PenetrationTestFindingResponse],
            summary="Get all findings for a penetration test",
            description="Retrieves all findings associated with a specific penetration test. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=10, seconds=10)
async def get_penetration_test_findings(
    pen_test_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000)
):
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(pen_test_id)
    if not pen_test:
        raise NotFoundException(detail="Penetration test not found.")
    finding_service = PenetrationTestFindingService(db)
    findings = await finding_service.get_findings_for_pen_test(pen_test_id, skip=skip, limit=limit)
    return findings

@router.get("/findings/{finding_id}", response_model=PenetrationTestFindingResponse,
            summary="Get a penetration test finding by ID",
            description="Retrieves details of a specific penetration test finding by its ID. Accessible by 'viewer', 'tester', 'admin'.")
@RateLimiter(times=20, seconds=10)
async def get_penetration_test_finding(
    finding_id: int,
    current_user: Annotated[User, Depends(get_current_viewer_or_above_user)],
    db: DBSession
):
    finding_service = PenetrationTestFindingService(db)
    finding = await finding_service.get_finding_by_id(finding_id)
    if not finding:
        raise NotFoundException(detail="Penetration test finding not found.")
    return finding

@router.put("/findings/{finding_id}", response_model=PenetrationTestFindingResponse,
            summary="Update a penetration test finding",
            description="Updates an existing penetration test finding. Only 'tester' or 'admin' can update.")
@RateLimiter(times=5, seconds=10)
async def update_penetration_test_finding(
    finding_id: int,
    finding_in: PenetrationTestFindingUpdate,
    current_user: Annotated[User, Depends(get_current_tester_or_admin_user)],
    db: DBSession
):
    finding_service = PenetrationTestFindingService(db)
    finding = await finding_service.get_finding_by_id(finding_id)
    if not finding:
        raise NotFoundException(detail="Penetration test finding not found.")
    # Authorization check: Only project owner or admin can update findings
    pen_test_service = PenetrationTestService(db)
    pen_test = await pen_test_service.get_pen_test_by_id(finding.pen_test_id)
    project_service = TestProjectService(db)
    project = await project_service.get_project_by_id(pen_test.project_id)
    if project.owner_id != current_user.id and current_user.role.value != "admin":
        raise ForbiddenException(detail="You do not have permission to update this finding.")

    updated_finding = await finding_service.update_finding(finding_id, finding_in)
    return updated_finding

@router.delete("/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT,
             summary="Delete a penetration test finding",
             description="Deletes a penetration test finding. Only 'admin' can delete.")
@RateLimiter(times=2, seconds=10)
async def delete_penetration_test_finding(
    finding_id: int,
    current_user: Annotated[User, Depends(get_current_admin_user)],
    db: DBSession
):
    finding_service = PenetrationTestFindingService(db)
    finding = await finding_service.get_finding_by_id(finding_id)
    if not finding:
        raise NotFoundException(detail="Penetration test finding not found.")
    await finding_service.delete_finding(finding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)