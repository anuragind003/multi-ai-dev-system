from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
import logging

from models import TestCase, TestRun, TestResult
from schemas import TestCaseCreate, TestCaseUpdate, TestRunCreate, TestRunUpdate, TestResultCreate
from core.exceptions import CustomException, ConflictException, NotFoundException

logger = logging.getLogger(__name__)

class TestCRUD:
    """
    CRUD operations for TestCase, TestRun, and TestResult models.
    Handles database interactions for test management.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- Test Case CRUD ---
    async def create_test_case(self, test_case_in: TestCaseCreate, created_by_user_id: int) -> TestCase:
        """
        Creates a new test case.
        Raises ConflictException if a test case with the same name already exists.
        """
        try:
            db_test_case = TestCase(
                **test_case_in.model_dump(),
                created_by_user_id=created_by_user_id
            )
            self.db.add(db_test_case)
            await self.db.commit()
            await self.db.refresh(db_test_case)
            logger.info(f"Test case '{db_test_case.name}' created by user {created_by_user_id}.")
            return db_test_case
        except IntegrityError:
            await self.db.rollback()
            logger.warning(f"Attempted to create test case with existing name: {test_case_in.name}")
            raise ConflictException(f"Test case with name '{test_case_in.name}' already exists.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating test case '{test_case_in.name}': {e}", exc_info=True)
            raise CustomException(f"Failed to create test case: {e}")

    async def get_test_case(self, test_case_id: int) -> Optional[TestCase]:
        """Retrieves a test case by its ID."""
        stmt = select(TestCase).where(TestCase.id == test_case_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_test_cases(self, skip: int = 0, limit: int = 100) -> List[TestCase]:
        """Retrieves a list of test cases with pagination."""
        stmt = select(TestCase).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_test_case(self, test_case_id: int, test_case_in: TestCaseUpdate) -> TestCase:
        """
        Updates an existing test case.
        Raises NotFoundException if test case does not exist.
        Raises ConflictException if updated name already exists for another test case.
        """
        db_test_case = await self.get_test_case(test_case_id)
        if not db_test_case:
            raise NotFoundException(f"Test case with ID {test_case_id} not found.")

        update_data = test_case_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_test_case, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(db_test_case)
            logger.info(f"Test case '{db_test_case.name}' (ID: {test_case_id}) updated successfully.")
            return db_test_case
        except IntegrityError:
            await self.db.rollback()
            logger.warning(f"Attempted to update test case {test_case_id} with existing name.")
            raise ConflictException(f"Test case with name '{test_case_in.name}' already exists.")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating test case {test_case_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to update test case: {e}")

    async def delete_test_case(self, test_case_id: int) -> bool:
        """
        Deletes a test case.
        Raises NotFoundException if test case does not exist.
        """
        db_test_case = await self.get_test_case(test_case_id)
        if not db_test_case:
            raise NotFoundException(f"Test case with ID {test_case_id} not found.")

        try:
            await self.db.delete(db_test_case)
            await self.db.commit()
            logger.info(f"Test case '{db_test_case.name}' (ID: {test_case_id}) deleted successfully.")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting test case {test_case_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to delete test case: {e}")

    # --- Test Run CRUD ---
    async def create_test_run(self, test_run_in: TestRunCreate, executed_by_user_id: int) -> TestRun:
        """
        Creates a new test run for a given test case.
        Raises NotFoundException if the test case does not exist.
        """
        test_case = await self.get_test_case(test_run_in.test_case_id)
        if not test_case:
            raise NotFoundException(f"Test case with ID {test_run_in.test_case_id} not found.")

        try:
            db_test_run = TestRun(
                test_case_id=test_run_in.test_case_id,
                executed_by_user_id=executed_by_user_id,
                notes=test_run_in.notes,
                status="pending" # Initial status
            )
            self.db.add(db_test_run)
            await self.db.commit()
            await self.db.refresh(db_test_run)
            logger.info(f"Test run {db_test_run.id} created for test case {test_run_in.test_case_id}.")
            return db_test_run
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating test run for test case {test_run_in.test_case_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to create test run: {e}")

    async def get_test_run(self, test_run_id: int) -> Optional[TestRun]:
        """Retrieves a test run by its ID, including related test results."""
        stmt = select(TestRun).options(selectinload(TestRun.test_results)).where(TestRun.id == test_run_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_test_runs(self, test_case_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[TestRun]:
        """Retrieves a list of test runs with pagination, optionally filtered by test case ID."""
        stmt = select(TestRun)
        if test_case_id:
            stmt = stmt.where(TestRun.test_case_id == test_case_id)
        stmt = stmt.offset(skip).limit(limit).order_by(TestRun.started_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_test_run(self, test_run_id: int, test_run_in: TestRunUpdate) -> TestRun:
        """
        Updates an existing test run's information.
        Raises NotFoundException if test run does not exist.
        """
        db_test_run = await self.get_test_run(test_run_id)
        if not db_test_run:
            raise NotFoundException(f"Test run with ID {test_run_id} not found.")

        update_data = test_run_in.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_test_run, key, value)

        try:
            await self.db.commit()
            await self.db.refresh(db_test_run)
            logger.info(f"Test run {test_run_id} updated to status '{db_test_run.status}'.")
            return db_test_run
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating test run {test_run_id}: {e}", exc_info=True)
            raise CustomException(f"Failed to update test run: {e}")

    # --- Test Result CRUD ---
    async def create_test_result(self, test_run_id: int, test_result_in: TestResultCreate) -> TestResult:
        """
        Records a new test result for a specific test run.
        Raises NotFoundException if the test run does not exist.
        """
        test_run = await self.get_test_run(test_run_id)
        if not test_run:
            raise NotFoundException(f"Test run with ID {test_run_id} not found.")

        try:
            db_test_result = TestResult(
                test_run_id=test_run_id,
                **test_result_in.model_dump()
            )
            self.db.add(db_test_result)
            await self.db.commit()
            await self.db.refresh(db_test_result)
            logger.info(f"Test result for run {test_run_id}, step {test_result_in.step_number} recorded as '{test_result_in.status}'.")
            return db_test_result
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating test result for run {test_run_id}, step {test_result_in.step_number}: {e}", exc_info=True)
            raise CustomException(f"Failed to create test result: {e}")

    async def get_test_results_by_run(self, test_run_id: int, skip: int = 0, limit: int = 100) -> List[TestResult]:
        """Retrieves all test results for a given test run."""
        stmt = select(TestResult).where(TestResult.test_run_id == test_run_id).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())