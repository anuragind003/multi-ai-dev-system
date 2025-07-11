from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Path, Query
import logging

from schemas import TestCaseCreate, TestCaseUpdate, TestCaseResponse, TestRunCreate, TestRunUpdate, TestRunResponse, TestResultCreate, TestResultResponse, HTTPError
from services.test_service import TestService
from models import User
from core.dependencies import get_test_service, get_current_active_user, get_current_qa_engineer_user, get_current_admin_user
from core.exceptions import NotFoundException, ConflictException, ForbiddenException

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Test Case Endpoints ---
@router.post(
    "/cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test case (QA Engineer/Admin)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires QA Engineer or Admin role"},
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Test case with this name already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def create_test_case(
    test_case_in: TestCaseCreate,
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_qa_engineer_user) # Only QA Engineers and Admins can create
):
    """
    Creates a new end-to-end test case.
    Requires 'qa_engineer' or 'admin' role.
    """
    try:
        test_case = await test_service.create_test_case(test_case_in, current_user)
        logger.info(f"Test case '{test_case.name}' created by user {current_user.username}.")
        return test_case
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except Exception as e:
        logger.error(f"Error creating test case: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test case creation.")

@router.get(
    "/cases",
    response_model=List[TestCaseResponse],
    summary="Get all test cases (Authenticated users)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"}
    }
)
async def get_all_test_cases(
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_active_user) # Any active user can view
):
    """
    Retrieves a list of all test cases.
    """
    test_cases = await test_service.get_all_test_cases(skip, limit)
    return test_cases

@router.get(
    "/cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Get test case by ID (Authenticated users)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test case not found"}
    }
)
async def get_test_case_by_id(
    test_case_id: int = Path(..., ge=1, description="The ID of the test case to retrieve"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_active_user) # Any active user can view
):
    """
    Retrieves a single test case by its ID.
    """
    try:
        test_case = await test_service.get_test_case(test_case_id)
        return test_case
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving test case {test_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.put(
    "/cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update test case by ID (QA Engineer/Admin)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires QA Engineer or Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test case not found"},
        status.HTTP_409_CONFLICT: {"model": HTTPError, "description": "Conflict: Test case with this name already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def update_test_case(
    test_case_id: int = Path(..., ge=1, description="The ID of the test case to update"),
    test_case_in: TestCaseUpdate,
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_qa_engineer_user) # Only QA Engineers and Admins can update
):
    """
    Updates an existing test case.
    Requires 'qa_engineer' or 'admin' role.
    """
    try:
        updated_test_case = await test_service.update_test_case(test_case_id, test_case_in)
        logger.info(f"Test case {test_case_id} updated by user {current_user.username}.")
        return updated_test_case
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except ConflictException as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating test case {test_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test case update.")

@router.delete(
    "/cases/{test_case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete test case by ID (Admin only)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test case not found"}
    }
)
async def delete_test_case(
    test_case_id: int = Path(..., ge=1, description="The ID of the test case to delete"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_admin_user) # Only Admins can delete
):
    """
    Deletes a test case from the system.
    This endpoint is restricted to users with the 'admin' role.
    """
    try:
        await test_service.delete_test_case(test_case_id)
        logger.info(f"Test case {test_case_id} deleted by admin {current_user.username}.")
        return {"message": "Test case deleted successfully."}
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error deleting test case {test_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test case deletion.")

# --- Test Run Endpoints ---
@router.post(
    "/runs",
    response_model=TestRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new test run (QA Engineer/Admin)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires QA Engineer or Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test case for run not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def start_test_run(
    test_run_in: TestRunCreate,
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_qa_engineer_user) # Only QA Engineers and Admins can start runs
):
    """
    Initiates a new test run for a specified test case.
    Requires 'qa_engineer' or 'admin' role.
    """
    try:
        test_run = await test_service.start_test_run(test_run_in, current_user)
        logger.info(f"Test run {test_run.id} started for test case {test_run.test_case_id} by user {current_user.username}.")
        return test_run
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error starting test run for test case {test_run_in.test_case_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test run creation.")

@router.get(
    "/runs",
    response_model=List[TestRunResponse],
    summary="Get all test runs (Authenticated users)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"}
    }
)
async def get_all_test_runs(
    test_case_id: Optional[int] = Query(None, ge=1, description="Filter runs by test case ID"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_active_user) # Any active user can view
):
    """
    Retrieves a list of all test runs, optionally filtered by test case ID.
    """
    test_runs = await test_service.get_all_test_runs(test_case_id, skip, limit)
    return test_runs

@router.get(
    "/runs/{test_run_id}",
    response_model=TestRunResponse,
    summary="Get test run by ID (Authenticated users)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test run not found"}
    }
)
async def get_test_run_by_id(
    test_run_id: int = Path(..., ge=1, description="The ID of the test run to retrieve"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_active_user) # Any active user can view
):
    """
    Retrieves a single test run by its ID, including its associated results.
    """
    try:
        test_run = await test_service.get_test_run(test_run_id)
        return test_run
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving test run {test_run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")

@router.put(
    "/runs/{test_run_id}",
    response_model=TestRunResponse,
    summary="Update test run status (QA Engineer/Admin)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires QA Engineer or Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test run not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def update_test_run_status(
    test_run_id: int = Path(..., ge=1, description="The ID of the test run to update"),
    test_run_update: TestRunUpdate,
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_qa_engineer_user) # Only QA Engineers and Admins can update
):
    """
    Updates the status and notes of an existing test run.
    Requires 'qa_engineer' or 'admin' role.
    """
    try:
        updated_run = await test_service.update_test_run_status(test_run_id, test_run_update)
        logger.info(f"Test run {test_run_id} status updated to '{updated_run.status}' by user {current_user.username}.")
        return updated_run
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error updating test run {test_run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test run update.")

# --- Test Result Endpoints ---
@router.post(
    "/runs/{test_run_id}/results",
    response_model=TestResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a test result for a run (QA Engineer/Admin)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"model": HTTPError, "description": "Forbidden: Requires QA Engineer or Admin role"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test run not found"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": HTTPError, "description": "Validation Error"}
    }
)
async def log_test_result(
    test_run_id: int = Path(..., ge=1, description="The ID of the test run to log results for"),
    test_result_in: TestResultCreate,
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_qa_engineer_user) # Only QA Engineers and Admins can log results
):
    """
    Logs a new test result for a specific step within a test run.
    Requires 'qa_engineer' or 'admin' role.
    """
    try:
        test_result = await test_service.log_test_result(test_run_id, test_result_in)
        logger.info(f"Test result for run {test_run_id}, step {test_result.step_number} logged by user {current_user.username}.")
        return test_result
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error logging test result for run {test_run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error during test result logging.")

@router.get(
    "/runs/{test_run_id}/results",
    response_model=List[TestResultResponse],
    summary="Get all test results for a specific run (Authenticated users)",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": HTTPError, "description": "Unauthorized"},
        status.HTTP_404_NOT_FOUND: {"model": HTTPError, "description": "Not Found: Test run not found"}
    }
)
async def get_test_results_for_run(
    test_run_id: int = Path(..., ge=1, description="The ID of the test run to retrieve results for"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    test_service: TestService = Depends(get_test_service),
    current_user: User = Depends(get_current_active_user) # Any active user can view
):
    """
    Retrieves all test results associated with a specific test run.
    """
    try:
        results = await test_service.get_test_results_for_run(test_run_id, skip, limit)
        return results
    except NotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except Exception as e:
        logger.error(f"Error retrieving test results for run {test_run_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error.")