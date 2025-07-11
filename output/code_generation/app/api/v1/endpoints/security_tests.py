import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.schemas.security_test import (
    SecurityTestCreate, SecurityTestUpdate, SecurityTestResponse,
    VulnerabilityCreate, VulnerabilityUpdate, VulnerabilityResponse,
    FindingCreate, FindingUpdate, FindingResponse
)
from app.services.security_test_service import SecurityTestService
from app.api.dependencies import get_current_active_user, has_role
from app.models.security_test import User, UserRole, TestStatus, VulnerabilitySeverity, FindingStatus
from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException, BadRequestException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/security-tests", tags=["Security Tests"])

# --- Security Test Endpoints ---

@router.post("/", response_model=SecurityTestResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new security test")
async def create_security_test(
    test_data: SecurityTestCreate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Creates a new security test entry.
    
    **Roles required:** `admin`, `tester`
    
    - **name**: Name of the test.
    - **description**: Detailed description.
    - **test_type**: Type of test (e.g., "Penetration Test", "Vulnerability Scan").
    - **target_scope**: Scope of the test (e.g., IP ranges, URLs).
    - **start_date**: Optional start date.
    - **end_date**: Optional end date.
    - **status**: Initial status (default: `pending`).
    - **assigned_to**: Optional user ID assigned to the test.
    """
    service = SecurityTestService(db_session)
    try:
        new_test = await service.create_security_test(test_data, current_user)
        return new_test
    except ForbiddenException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating security test: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create security test")

@router.get("/", response_model=List[SecurityTestResponse], summary="Get all security tests")
async def get_all_security_tests(
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200),
    name: Optional[str] = Query(None, description="Filter by test name (case-insensitive partial match)"),
    test_type: Optional[str] = Query(None, description="Filter by test type (case-insensitive partial match)"),
    status: Optional[TestStatus] = Query(None, description="Filter by test status"),
    assigned_to: Optional[int] = Query(None, description="Filter by assigned user ID")
):
    """
    Retrieves a list of all security tests with optional filtering and pagination.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    tests = await service.get_all_security_tests(skip, limit, name, test_type, status, assigned_to)
    return tests

@router.get("/{test_id}", response_model=SecurityTestResponse, summary="Get a security test by ID")
async def get_security_test_by_id(
    test_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Retrieves a single security test by its ID.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    test = await service.get_security_test(test_id)
    if not test:
        raise NotFoundException(detail=f"Security test with ID {test_id} not found.")
    return test

@router.put("/{test_id}", response_model=SecurityTestResponse, summary="Update a security test by ID")
async def update_security_test(
    test_id: int,
    test_data: SecurityTestUpdate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Updates an existing security test.
    
    **Roles required:** `admin`, `tester`
    
    - **test_id**: The ID of the test to update.
    - **test_data**: The updated test information.
    """
    service = SecurityTestService(db_session)
    try:
        updated_test = await service.update_security_test(test_id, test_data, current_user)
        return updated_test
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except BadRequestException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating security test {test_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update security test")

@router.delete("/{test_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a security test by ID")
async def delete_security_test(
    test_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN]))]
):
    """
    Deletes a security test and all its associated vulnerabilities and findings.
    
    **Roles required:** `admin`
    
    - **test_id**: The ID of the test to delete.
    """
    service = SecurityTestService(db_session)
    try:
        await service.delete_security_test(test_id, current_user)
        return {"message": "Security test deleted successfully"}
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting security test {test_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete security test")

# --- Vulnerability Endpoints ---

@router.post("/{test_id}/vulnerabilities", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new vulnerability for a security test")
async def create_vulnerability_for_test(
    test_id: int,
    vuln_data: VulnerabilityCreate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Creates a new vulnerability associated with a specific security test.
    
    **Roles required:** `admin`, `tester`
    
    - **test_id**: The ID of the security test.
    - **vuln_data**: Vulnerability details.
    """
    if vuln_data.security_test_id != test_id:
        raise BadRequestException(detail="Vulnerability's security_test_id must match path parameter.")
    
    service = SecurityTestService(db_session)
    try:
        new_vuln = await service.create_vulnerability(vuln_data, current_user)
        return new_vuln
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except BadRequestException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating vulnerability for test {test_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create vulnerability")

@router.get("/{test_id}/vulnerabilities", response_model=List[VulnerabilityResponse],
             summary="Get all vulnerabilities for a security test")
async def get_vulnerabilities_for_test(
    test_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    """
    Retrieves a list of vulnerabilities for a specific security test.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    # First, check if the test exists
    test = await service.get_security_test(test_id)
    if not test:
        raise NotFoundException(detail=f"Security test with ID {test_id} not found.")
    
    vulnerabilities = await service.get_vulnerabilities_by_test(test_id, skip, limit)
    return vulnerabilities

@router.get("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse, summary="Get a vulnerability by ID")
async def get_vulnerability_by_id(
    vuln_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Retrieves a single vulnerability by its ID.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    vuln = await service.get_vulnerability(vuln_id)
    if not vuln:
        raise NotFoundException(detail=f"Vulnerability with ID {vuln_id} not found.")
    return vuln

@router.put("/vulnerabilities/{vuln_id}", response_model=VulnerabilityResponse, summary="Update a vulnerability by ID")
async def update_vulnerability(
    vuln_id: int,
    vuln_data: VulnerabilityUpdate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Updates an existing vulnerability.
    
    **Roles required:** `admin`, `tester`
    
    - **vuln_id**: The ID of the vulnerability to update.
    - **vuln_data**: The updated vulnerability information.
    """
    service = SecurityTestService(db_session)
    try:
        updated_vuln = await service.update_vulnerability(vuln_id, vuln_data, current_user)
        return updated_vuln
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating vulnerability {vuln_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update vulnerability")

@router.delete("/vulnerabilities/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a vulnerability by ID")
async def delete_vulnerability(
    vuln_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN]))]
):
    """
    Deletes a vulnerability and all its associated findings.
    
    **Roles required:** `admin`
    
    - **vuln_id**: The ID of the vulnerability to delete.
    """
    service = SecurityTestService(db_session)
    try:
        await service.delete_vulnerability(vuln_id, current_user)
        return {"message": "Vulnerability deleted successfully"}
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting vulnerability {vuln_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete vulnerability")

# --- Finding Endpoints ---

@router.post("/vulnerabilities/{vuln_id}/findings", response_model=FindingResponse, status_code=status.HTTP_201_CREATED,
             summary="Create a new finding for a vulnerability")
async def create_finding_for_vulnerability(
    vuln_id: int,
    finding_data: FindingCreate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Creates a new finding associated with a specific vulnerability.
    
    **Roles required:** `admin`, `tester`
    
    - **vuln_id**: The ID of the vulnerability.
    - **finding_data**: Finding details.
    """
    if finding_data.vulnerability_id != vuln_id:
        raise BadRequestException(detail="Finding's vulnerability_id must match path parameter.")
    
    service = SecurityTestService(db_session)
    try:
        new_finding = await service.create_finding(finding_data, current_user)
        return new_finding
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except BadRequestException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating finding for vulnerability {vuln_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create finding")

@router.get("/vulnerabilities/{vuln_id}/findings", response_model=List[FindingResponse],
             summary="Get all findings for a vulnerability")
async def get_findings_for_vulnerability(
    vuln_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=200)
):
    """
    Retrieves a list of findings for a specific vulnerability.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    # First, check if the vulnerability exists
    vuln = await service.get_vulnerability(vuln_id)
    if not vuln:
        raise NotFoundException(detail=f"Vulnerability with ID {vuln_id} not found.")
    
    findings = await service.get_findings_by_vulnerability(vuln_id, skip, limit)
    return findings

@router.get("/findings/{finding_id}", response_model=FindingResponse, summary="Get a finding by ID")
async def get_finding_by_id(
    finding_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Retrieves a single finding by its ID.
    
    **Roles required:** Any active user.
    """
    service = SecurityTestService(db_session)
    finding = await service.get_finding(finding_id)
    if not finding:
        raise NotFoundException(detail=f"Finding with ID {finding_id} not found.")
    return finding

@router.put("/findings/{finding_id}", response_model=FindingResponse, summary="Update a finding by ID")
async def update_finding(
    finding_id: int,
    finding_data: FindingUpdate,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN, UserRole.TESTER]))]
):
    """
    Updates an existing finding.
    
    **Roles required:** `admin`, `tester`
    
    - **finding_id**: The ID of the finding to update.
    - **finding_data**: The updated finding information.
    """
    service = SecurityTestService(db_session)
    try:
        updated_finding = await service.update_finding(finding_id, finding_data, current_user)
        return updated_finding
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating finding {finding_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update finding")

@router.delete("/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a finding by ID")
async def delete_finding(
    finding_id: int,
    db_session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(has_role([UserRole.ADMIN]))]
):
    """
    Deletes a finding.
    
    **Roles required:** `admin`
    
    - **finding_id**: The ID of the finding to delete.
    """
    service = SecurityTestService(db_session)
    try:
        await service.delete_finding(finding_id, current_user)
        return {"message": "Finding deleted successfully"}
    except NotFoundException as e:
        raise e
    except ForbiddenException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting finding {finding_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete finding")