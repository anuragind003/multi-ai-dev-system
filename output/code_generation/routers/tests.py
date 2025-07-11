from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from database import get_db
from services import IntegrationTestService
from schemas import TestCreate, TestUpdate, TestResponse, TestResultResponse, APIResponse
from security import get_api_key, has_role
from exceptions import NotFoundException, ConflictException, ForbiddenException
from utils.logger import logger

router = APIRouter()

@router.post(
    "/tests",
    response_model=TestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new integration test",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin"]))]
)
async def create_integration_test(
    test_data: TestCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new integration test with the provided details.
    Requires 'admin' role.
    """
    logger.info(f"Received request to create test: {test_data.name}")
    service = IntegrationTestService(db)
    try:
        new_test = await service.create_test(test_data)
        return new_test
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"Error creating test: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create test.")

@router.get(
    "/tests",
    response_model=List[TestResponse],
    summary="Retrieve all integration tests",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin", "user"]))]
)
async def get_all_integration_tests(
    skip: int = Query(0, ge=0, description="Number of items to skip (for pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a list of all integration tests.
    Supports pagination. Requires 'admin' or 'user' role.
    """
    logger.info(f"Received request to get all tests (skip: {skip}, limit: {limit}).")
    service = IntegrationTestService(db)
    tests = await service.get_all_tests(skip=skip, limit=limit)
    return tests

@router.get(
    "/tests/{test_id}",
    response_model=TestResponse,
    summary="Retrieve a single integration test by ID",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin", "user"]))]
)
async def get_integration_test(
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieves a single integration test by its unique ID.
    Requires 'admin' or 'user' role.
    """
    logger.info(f"Received request to get test ID: {test_id}")
    service = IntegrationTestService(db)
    try:
        test = await service.get_test(test_id)
        return test
    except NotFoundException as e:
        raise e
    except Exception as e:
        logger.error(f"Error getting test ID {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve test.")

@router.put(
    "/tests/{test_id}",
    response_model=TestResponse,
    summary="Update an existing integration test",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin"]))]
)
async def update_integration_test(
    test_id: int,
    test_data: TestUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates an existing integration test identified by its ID.
    Requires 'admin' role.
    """
    logger.info(f"Received request to update test ID: {test_id}")
    service = IntegrationTestService(db)
    try:
        updated_test = await service.update_test(test_id, test_data)
        return updated_test
    except NotFoundException as e:
        raise e
    except ConflictException as e:
        raise e
    except Exception as e:
        logger.error(f"Error updating test ID {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update test.")

@router.delete(
    "/tests/{test_id}",
    response_model=APIResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an integration test",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin"]))]
)
async def delete_integration_test(
    test_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes an integration test identified by its ID.
    Requires 'admin' role.
    """
    logger.info(f"Received request to delete test ID: {test_id}")
    service = IntegrationTestService(db)
    try:
        await service.delete_test(test_id)
        return APIResponse(
            message=f"Test with ID {test_id} deleted successfully.",
            status_code=status.HTTP_200_OK
        )
    except NotFoundException as e:
        raise e
    except Exception as e:
        logger.error(f"Error deleting test ID {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete test.")

@router.post(
    "/tests/{test_id}/execute",
    response_model=TestResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a specific integration test",
    dependencies=[Depends(get_api_key), Depends(lambda: has_role(["admin", "user"]))]
)
async def execute_integration_test(
    test_id: int,
    executed_by: Optional[str] = Query("API_User", max_length=100, description="Name of the user or system executing the test"),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes a specific integration test by its ID and records the result.
    Requires 'admin' or 'user' role.
    """
    logger.info(f"Received request to execute test ID: {test_id} by {executed_by}")
    service = IntegrationTestService(db)
    try:
        test_result = await service.execute_test(test_id, executed_by)
        return test_result
    except NotFoundException as e:
        raise e
    except ConflictException as e: # For inactive tests
        raise e
    except Exception as e:
        logger.error(f"Error executing test ID {test_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to execute test.")