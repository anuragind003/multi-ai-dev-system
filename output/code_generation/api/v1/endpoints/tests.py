from typing import List, Annotated
from fastapi import APIRouter, Depends, status, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas.schemas import TestCaseCreate, TestCaseUpdate, TestCaseResponse, TestRunCreate, TestRunUpdate, TestRunResponse
from services.test_service import TestService
from models.models import User, UserRole
from security.dependencies import get_current_user, has_permission
from core.exceptions import NotFoundException, ConflictException, UnprocessableEntityException
from core.logger import logger

router = APIRouter()

# --- Test Case Endpoints ---

@router.post(
    "/cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test case",
    responses={
        status.HTTP_409_CONFLICT: {"description": "Test case with this title already exists for the creator"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires QA_ENGINEER or ADMIN)"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}
    }
)
async def create_test_case(
    test_case_in: TestCaseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.QA_ENGINEER, UserRole.ADMIN]))]
):
    """
    Creates a new test case.
    Users with 'QA_ENGINEER' or 'ADMIN' roles can create test cases.
    """
    test_service = TestService(db)
    new_test_case = await test_service.create_test_case(test_case_in, current_user.id)
    logger.info(f"Test case '{new_test_case.title}' (ID: {new_test_case.id}) created by user {current_user.username}.")
    return new_test_case

@router.get(
    "/cases",
    response_model=List[TestCaseResponse],
    summary="Get all test cases",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires any authenticated user)"}
    }
)
async def get_all_test_cases(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)] # Any authenticated user can read
):
    """
    Retrieves a list of all test cases with pagination.
    Any authenticated user can view test cases.
    """
    test_service = TestService(db)
    test_cases = await test_service.get_all_test_cases(skip=skip, limit=limit)
    return test_cases

@router.get(
    "/cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Get a test case by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test case not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires any authenticated user)"}
    }
)
async def get_test_case_by_id(
    test_case_id: Annotated[int, Path(ge=1, description="The ID of the test case to retrieve")],
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves a single test case by its ID.
    Any authenticated user can view test cases.
    """
    test_service = TestService(db)
    test_case = await test_service.get_test_case_by_id(test_case_id)
    if not test_case:
        raise NotFoundException(detail="Test case not found")
    return test_case

@router.put(
    "/cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update an existing test case",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test case not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires QA_ENGINEER or ADMIN)"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}
    }
)
async def update_test_case(
    test_case_id: Annotated[int, Path(ge=1, description="The ID of the test case to update")],
    test_case_update: TestCaseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.QA_ENGINEER, UserRole.ADMIN]))]
):
    """
    Updates an existing test case.
    Users with 'QA_ENGINEER' or 'ADMIN' roles can update test cases.
    """
    test_service = TestService(db)
    updated_test_case = await test_service.update_test_case(test_case_id, test_case_update)
    logger.info(f"Test case (ID: {test_case_id}) updated by user {current_user.username}.")
    return updated_test_case

@router.delete(
    "/cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a test case",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test case not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires ADMIN)"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Cannot delete test case with associated test runs"}
    }
)
async def delete_test_case(
    test_case_id: Annotated[int, Path(ge=1, description="The ID of the test case to delete")],
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.ADMIN]))]
):
    """
    Deletes a test case.
    Only users with 'ADMIN' role can delete test cases.
    """
    test_service = TestService(db)
    await test_service.delete_test_case(test_case_id)
    logger.info(f"Test case (ID: {test_case_id}) deleted by user {current_user.username}.")
    return {"message": "Test case deleted successfully"}

# --- Test Run Endpoints ---

@router.post(
    "/runs",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test run",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test case not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Test case not active or validation error"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires QA_ENGINEER or ADMIN)"}
    }
)
async def create_test_run(
    test_run_in: TestRunCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.QA_ENGINEER, UserRole.ADMIN]))]
):
    """
    Creates a new test run for a specific test case.
    Users with 'QA_ENGINEER' or 'ADMIN' roles can create test runs.
    The associated test case must be 'active'.
    """
    test_service = TestService(db)
    new_test_run = await test_service.create_test_run(test_run_in, current_user.id)
    logger.info(f"Test run (ID: {new_test_run.id}) created for test case {test_run_in.test_case_id} by user {current_user.username}.")
    return new_test_run

@router.get(
    "/runs",
    response_model=List[TestRunResponse],
    summary="Get all test runs",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires any authenticated user)"}
    }
)
async def get_all_test_runs(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves a list of all test runs with pagination.
    Any authenticated user can view test runs.
    """
    test_service = TestService(db)
    test_runs = await test_service.get_all_test_runs(skip=skip, limit=limit)
    return test_runs

@router.get(
    "/runs/{test_run_id}",
    response_model=TestRunResponse,
    summary="Get a test run by ID",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test run not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires any authenticated user)"}
    }
)
async def get_test_run_by_id(
    test_run_id: Annotated[int, Path(ge=1, description="The ID of the test run to retrieve")],
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Retrieves a single test run by its ID.
    Any authenticated user can view test runs.
    """
    test_service = TestService(db)
    test_run = await test_service.get_test_run_by_id(test_run_id)
    if not test_run:
        raise NotFoundException(detail="Test run not found")
    return test_run

@router.put(
    "/runs/{test_run_id}",
    response_model=TestRunResponse,
    summary="Update an existing test run",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test run not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires QA_ENGINEER or ADMIN)"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Validation error"}
    }
)
async def update_test_run(
    test_run_id: Annotated[int, Path(ge=1, description="The ID of the test run to update")],
    test_run_update: TestRunUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.QA_ENGINEER, UserRole.ADMIN]))]
):
    """
    Updates an existing test run.
    Users with 'QA_ENGINEER' or 'ADMIN' roles can update test runs.
    """
    test_service = TestService(db)
    updated_test_run = await test_service.update_test_run(test_run_id, test_run_update)
    logger.info(f"Test run (ID: {test_run_id}) updated by user {current_user.username}.")
    return updated_test_run

@router.delete(
    "/runs/{test_run_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a test run",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test run not found"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires ADMIN)"}
    }
)
async def delete_test_run(
    test_run_id: Annotated[int, Path(ge=1, description="The ID of the test run to delete")],
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.ADMIN]))]
):
    """
    Deletes a test run.
    Only users with 'ADMIN' role can delete test runs.
    """
    test_service = TestService(db)
    await test_service.delete_test_run(test_run_id)
    logger.info(f"Test run (ID: {test_run_id}) deleted by user {current_user.username}.")
    return {"message": "Test run deleted successfully"}

@router.post(
    "/runs/{test_run_id}/execute",
    response_model=TestRunResponse,
    summary="Execute a test run",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Test run not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"description": "Test run cannot be executed in its current state"},
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required"},
        status.HTTP_403_FORBIDDEN: {"description": "Not enough permissions (requires QA_ENGINEER or ADMIN)"}
    }
)
async def execute_test_run(
    test_run_id: Annotated[int, Path(ge=1, description="The ID of the test run to execute")],
    db: AsyncSession = Depends(get_db),
    current_user: Annotated[User, Depends(has_permission([UserRole.QA_ENGINEER, UserRole.ADMIN]))]
):
    """
    Simulates the execution of a test run.
    Users with 'QA_ENGINEER' or 'ADMIN' roles can execute test runs.
    """
    test_service = TestService(db)
    executed_test_run = await test_service.execute_test_run(test_run_id, current_user)
    logger.info(f"Test run (ID: {test_run_id}) executed by user {current_user.username}.")
    return executed_test_run