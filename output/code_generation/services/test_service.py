from typing import List, Optional
from datetime import datetime
import logging

from crud.test_crud import TestCRUD
from crud.user_crud import UserCRUD
from schemas import TestCaseCreate, TestCaseUpdate, TestCaseResponse, TestRunCreate, TestRunUpdate, TestRunResponse, TestResultCreate, TestResultResponse
from models import User, TestCase, TestRun, TestResult
from core.exceptions import NotFoundException, ConflictException, CustomException

logger = logging.getLogger(__name__)

class TestService:
    """
    Service layer for managing test cases, test runs, and test results.
    Encapsulates business logic and interacts with CRUD operations.
    """
    def __init__(self, test_crud: TestCRUD, user_crud: UserCRUD):
        self.test_crud = test_crud
        self.user_crud = user_crud

    # --- Test Case Operations ---
    async def create_test_case(self, test_case_in: TestCaseCreate, current_user: User) -> TestCaseResponse:
        """
        Creates a new test case.
        Ensures the creating user exists.
        """
        # Input validation is handled by Pydantic schema TestCaseCreate
        
        # Check if user exists (though current_user is already validated by auth)
        user = await self.user_crud.get_user_by_id(current_user.id)
        if not user:
            raise CustomException("Creating user not found in database.", status_code=500) # Should not happen if auth is correct

        db_test_case = await self.test_crud.create_test_case(test_case_in, current_user.id)
        return TestCaseResponse.model_validate(db_test_case)

    async def get_test_case(self, test_case_id: int) -> TestCaseResponse:
        """Retrieves a single test case by ID."""
        test_case = await self.test_crud.get_test_case(test_case_id)
        if not test_case:
            raise NotFoundException(f"Test case with ID {test_case_id} not found.")
        return TestCaseResponse.model_validate(test_case)

    async def get_all_test_cases(self, skip: int = 0, limit: int = 100) -> List[TestCaseResponse]:
        """Retrieves all test cases with pagination."""
        test_cases = await self.test_crud.get_test_cases(skip, limit)
        return [TestCaseResponse.model_validate(tc) for tc in test_cases]

    async def update_test_case(self, test_case_id: int, test_case_in: TestCaseUpdate) -> TestCaseResponse:
        """Updates an existing test case."""
        # Input validation handled by Pydantic schema TestCaseUpdate
        db_test_case = await self.test_crud.update_test_case(test_case_id, test_case_in)
        return TestCaseResponse.model_validate(db_test_case)

    async def delete_test_case(self, test_case_id: int) -> bool:
        """Deletes a test case."""
        success = await self.test_crud.delete_test_case(test_case_id)
        if not success:
            raise NotFoundException(f"Test case with ID {test_case_id} not found for deletion.")
        return success

    # --- Test Run Operations ---
    async def start_test_run(self, test_run_in: TestRunCreate, current_user: User) -> TestRunResponse:
        """
        Initiates a new test run for a specified test case.
        Sets initial status to 'running'.
        """
        # Validate test_case_id exists implicitly via test_crud.create_test_run
        db_test_run = await self.test_crud.create_test_run(test_run_in, current_user.id)
        # Optionally, update status to 'running' immediately after creation if it's meant to start right away
        # db_test_run.status = "running"
        # await self.test_crud.db.commit()
        # await self.test_crud.db.refresh(db_test_run)
        return TestRunResponse.model_validate(db_test_run)

    async def get_test_run(self, test_run_id: int) -> TestRunResponse:
        """Retrieves a single test run by ID, including its results."""
        test_run = await self.test_crud.get_test_run(test_run_id)
        if not test_run:
            raise NotFoundException(f"Test run with ID {test_run_id} not found.")
        return TestRunResponse.model_validate(test_run)

    async def get_all_test_runs(self, test_case_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[TestRunResponse]:
        """Retrieves all test runs with pagination, optionally filtered by test case ID."""
        test_runs = await self.test_crud.get_test_runs(test_case_id, skip, limit)
        return [TestRunResponse.model_validate(tr) for tr in test_runs]

    async def update_test_run_status(self, test_run_id: int, test_run_update: TestRunUpdate) -> TestRunResponse:
        """Updates the status and notes of a test run."""
        # If status is 'passed' or 'failed', set completed_at
        if test_run_update.status in ["passed", "failed", "skipped"] and test_run_update.completed_at is None:
            test_run_update.completed_at = datetime.utcnow()
            
        db_test_run = await self.test_crud.update_test_run(test_run_id, test_run_update)
        return TestRunResponse.model_validate(db_test_run)

    # --- Test Result Operations ---
    async def log_test_result(self, test_run_id: int, test_result_in: TestResultCreate) -> TestResultResponse:
        """
        Logs a new test result for a specific step within a test run.
        """
        # Validate test_run_id exists implicitly via test_crud.create_test_result
        db_test_result = await self.test_crud.create_test_result(test_run_id, test_result_in)
        return TestResultResponse.model_validate(db_test_result)

    async def get_test_results_for_run(self, test_run_id: int, skip: int = 0, limit: int = 100) -> List[TestResultResponse]:
        """Retrieves all test results for a given test run."""
        # Check if test run exists first
        test_run = await self.test_crud.get_test_run(test_run_id)
        if not test_run:
            raise NotFoundException(f"Test run with ID {test_run_id} not found.")
            
        results = await self.test_crud.get_test_results_by_run(test_run_id, skip, limit)
        return [TestResultResponse.model_validate(res) for res in results]