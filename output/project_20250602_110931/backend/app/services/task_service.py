import datetime
import logging
from typing import List, Optional, Dict, Any

from app.models.task import Task
from app.database import db_session
from sqlalchemy.exc import SQLAlchemyError

# Configure logging for the service
logger = logging.getLogger(__name__)
# Basic configuration for demonstration. In a real application,
# logging would typically be configured globally in app setup.
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Custom Exceptions for TaskService
class TaskServiceError(Exception):
    """Base exception for TaskService errors."""
    pass

class TaskNotFoundError(TaskServiceError):
    """Exception raised when a task is not found or not owned by the user."""
    pass

class InvalidInputError(TaskServiceError):
    """Exception raised for invalid input data provided to TaskService methods."""
    pass

class TaskService:
    """
    Encapsulates business logic for task operations, including CRUD operations,
    validation, and filtering tasks.
    """

    @staticmethod
    def _parse_due_date(due_date_str: Optional[str]) -> Optional[datetime.date]:
        """
        Helper method to parse a due date string into a date object.

        Args:
            due_date_str (Optional[str]): The due date string in 'YYYY-MM-DD' format.

        Returns:
            Optional[datetime.date]: The parsed date object, or None if input is None.

        Raises:
            InvalidInputError: If the due_date_str format is invalid.
        """
        if due_date_str is None:
            return None
        try:
            return datetime.datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            raise InvalidInputError("Invalid due date format. Use YYYY-MM-DD.")

    @staticmethod
    def create_task(user_id: int, title: str, description: Optional[str] = None,
                    due_date: Optional[str] = None) -> Task:
        """
        Creates a new task for a given user.

        Args:
            user_id (int): The ID of the user creating the task.
            title (str): The title of the task.
            description (Optional[str]): The description of the task.
            due_date (Optional[str]): The due date of the task in 'YYYY-MM-DD' format.

        Returns:
            Task: The created Task object.

        Raises:
            InvalidInputError: If title is empty or due_date format is invalid.
            TaskServiceError: If a database error occurs during task creation.
        """
        if not title or not title.strip():
            raise InvalidInputError("Task title cannot be empty.")

        parsed_due_date = TaskService._parse_due_date(due_date)

        try:
            new_task = Task(
                user_id=user_id,
                title=title.strip(),
                description=description,
                due_date=parsed_due_date
            )
            db_session.add(new_task)
            db_session.commit()
            logger.info(f"Task created successfully: ID={new_task.id}, UserID={user_id}")
            return new_task
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error creating task for user {user_id} with title '{title}': {e}", exc_info=True)
            raise TaskServiceError(f"Failed to create task due to a database error.") from e

    @staticmethod
    def get_task_by_id(task_id: int, user_id: int) -> Optional[Task]:
        """
        Retrieves a single task by its ID, ensuring it belongs to the specified user.

        Args:
            task_id (int): The ID of the task to retrieve.
            user_id (int): The ID of the user who owns the task.

        Returns:
            Optional[Task]: The Task object if found and owned by the user, None otherwise.

        Raises:
            TaskServiceError: If a database error occurs during retrieval.
        """
        try:
            task = db_session.query(Task).filter_by(id=task_id, user_id=user_id).first()
            if task:
                logger.debug(f"Task ID={task_id} found for UserID={user_id}.")
            else:
                logger.debug(f"Task ID={task_id} not found or not owned by UserID={user_id}.")
            return task
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving task by ID {task_id} for user {user_id}: {e}", exc_info=True)
            raise TaskServiceError(f"Failed to retrieve task due to a database error.") from e

    @staticmethod
    def get_all_tasks(user_id: int, completed: Optional[bool] = None) -> List[Task]:
        """
        Retrieves all tasks for a given user, with optional filtering by completion status.

        Args:
            user_id (int): The ID of the user whose tasks to retrieve.
            completed (Optional[bool]): If True, return only completed tasks.
                                        If False, return only incomplete tasks.
                                        If None, return all tasks.

        Returns:
            List[Task]: A list of Task objects. Returns an empty list if no tasks are found
                        or if a database error occurs.

        Raises:
            TaskServiceError: If a database error occurs during retrieval.
        """
        try:
            query = db_session.query(Task).filter_by(user_id=user_id)
            if completed is not None:
                query = query.filter_by(completed=completed)
            
            tasks = query.order_by(Task.created_at.desc()).all()
            logger.info(f"Retrieved {len(tasks)} tasks for UserID={user_id} (completed={completed}).")
            return tasks
        except SQLAlchemyError as e:
            logger.error(f"Database error retrieving all tasks for user {user_id}: {e}", exc_info=True)
            raise TaskServiceError(f"Failed to retrieve tasks due to a database error.") from e

    @staticmethod
    def update_task(task_id: int, user_id: int, updates: Dict[str, Any]) -> Task:
        """
        Updates an existing task.

        Args:
            task_id (int): The ID of the task to update.
            user_id (int): The ID of the user who owns the task (for authorization).
            updates (Dict[str, Any]): A dictionary of fields to update and their new values.
                                      Allowed keys: 'title', 'description', 'due_date', 'completed'.

        Returns:
            Task: The updated Task object.

        Raises:
            TaskNotFoundError: If the task is not found or not owned by the user.
            InvalidInputError: If any update value is invalid (e.g., empty title, bad due_date format,
                               invalid type for 'completed').
            TaskServiceError: If a database error occurs during the update.
        """
        task = TaskService.get_task_by_id(task_id, user_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID {task_id} not found or not owned by user {user_id}.")

        try:
            if 'title' in updates:
                if updates['title'] is None or not isinstance(updates['title'], str) or not updates['title'].strip():
                    raise InvalidInputError("Task title cannot be empty or null.")
                task.title = updates['title'].strip()

            if 'description' in updates:
                # Description can be set to None
                task.description = updates['description']

            if 'due_date' in updates:
                task.due_date = TaskService._parse_due_date(updates['due_date'])

            if 'completed' in updates:
                if not isinstance(updates['completed'], bool):
                    raise InvalidInputError("Completed status must be a boolean value.")
                task.completed = updates['completed']

            db_session.commit()
            logger.info(f"Task ID={task_id} updated successfully for UserID={user_id}.")
            return task
        except (InvalidInputError, TaskNotFoundError) as e:
            db_session.rollback()
            logger.warning(f"Validation or Not Found error updating task {task_id} for user {user_id}: {e}")
            raise # Re-raise custom exceptions for caller to handle
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error updating task {task_id} for user {user_id}: {e}", exc_info=True)
            raise TaskServiceError(f"Failed to update task due to a database error.") from e

    @staticmethod
    def delete_task(task_id: int, user_id: int) -> None:
        """
        Deletes a task.

        Args:
            task_id (int): The ID of the task to delete.
            user_id (int): The ID of the user who owns the task (for authorization).

        Returns:
            None: Indicates successful deletion.

        Raises:
            TaskNotFoundError: If the task is not found or not owned by the user.
            TaskServiceError: If a database error occurs during deletion.
        """
        task = TaskService.get_task_by_id(task_id, user_id)
        if not task:
            raise TaskNotFoundError(f"Task with ID {task_id} not found or not owned by user {user_id}.")

        try:
            db_session.delete(task)
            db_session.commit()
            logger.info(f"Task ID={task_id} deleted successfully for UserID={user_id}.")
        except SQLAlchemyError as e:
            db_session.rollback()
            logger.error(f"Database error deleting task {task_id} for user {user_id}: {e}", exc_info=True)
            raise TaskServiceError(f"Failed to delete task due to a database error.") from e