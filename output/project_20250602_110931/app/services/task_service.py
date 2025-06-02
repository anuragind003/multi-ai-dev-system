import datetime
from datetime import timezone
import logging
from typing import List, Optional, Dict, Any

from app.models.task import Task
from app.database import db

logger = logging.getLogger(__name__)

class TaskService:
    """
    Encapsulates business logic for task operations.
    Provides methods for creating, retrieving, updating, and deleting tasks,
    including any associated validation or business rules.
    """

    @staticmethod
    def create_task(user_id: int, title: str, description: Optional[str] = None,
                    due_date: Optional[datetime.date] = None) -> Optional[Task]:
        """
        Creates a new task for a given user.

        Args:
            user_id (int): The ID of the user creating the task.
            title (str): The title of the task.
            description (Optional[str]): The description of the task.
            due_date (Optional[datetime.date]): The optional due date for the task.

        Returns:
            Optional[Task]: The newly created Task object if successful, None otherwise.
        """
        if not title or not isinstance(title, str) or not title.strip():
            logger.warning(f"Attempted to create task with invalid title: '{title}' for user {user_id}")
            return None

        try:
            now_utc = datetime.datetime.now(timezone.utc)
            new_task = Task(
                user_id=user_id,
                title=title.strip(),
                description=description.strip() if description else None,
                due_date=due_date,
                created_at=now_utc,
                updated_at=now_utc,
                is_completed=False
            )
            db.session.add(new_task)
            db.session.commit()
            logger.info(f"Task '{new_task.title}' (ID: {new_task.id}) created for user {user_id}.")
            return new_task
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating task for user {user_id} with title '{title}': {e}", exc_info=True)
            return None

    @staticmethod
    def get_task_by_id(task_id: int, user_id: int) -> Optional[Task]:
        """
        Retrieves a single task by its ID, ensuring it belongs to the specified user.

        Args:
            task_id (int): The ID of the task to retrieve.
            user_id (int): The ID of the user who owns the task.

        Returns:
            Optional[Task]: The Task object if found and owned by the user, None otherwise.
        """
        try:
            task = Task.query.filter_by(id=task_id, user_id=user_id).first()
            if not task:
                logger.info(f"Task with ID {task_id} not found or not owned by user {user_id}.")
            return task
        except Exception as e:
            logger.error(f"Error retrieving task by ID {task_id} for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def get_tasks_by_user(user_id: int, include_completed: bool = True) -> List[Task]:
        """
        Retrieves all tasks for a given user.

        Args:
            user_id (int): The ID of the user whose tasks are to be retrieved.
            include_completed (bool): If True, includes completed tasks. If False, only returns incomplete tasks.

        Returns:
            List[Task]: A list of Task objects. Returns an empty list if no tasks are found or on error.
        """
        try:
            query = Task.query.filter_by(user_id=user_id)
            if not include_completed:
                query = query.filter_by(is_completed=False)
            tasks = query.order_by(Task.created_at.desc()).all()
            logger.info(f"Retrieved {len(tasks)} tasks for user {user_id}.")
            return tasks
        except Exception as e:
            logger.error(f"Error retrieving tasks for user {user_id}: {e}", exc_info=True)
            return []

    @staticmethod
    def update_task(task_id: int, user_id: int, updates: Dict[str, Any]) -> Optional[Task]:
        """
        Updates an existing task.

        Args:
            task_id (int): The ID of the task to update.
            user_id (int): The ID of the user who owns the task (for authorization).
            updates (Dict[str, Any]): A dictionary containing fields to update (e.g., {'title': 'New Title', 'is_completed': True}).

        Returns:
            Optional[Task]: The updated Task object if successful, None otherwise.
        """
        task = TaskService.get_task_by_id(task_id, user_id)
        if not task:
            logger.warning(f"Attempted to update task {task_id} for user {user_id}, but task not found or not owned.")
            return None

        try:
            allowed_fields = {'title', 'description', 'due_date', 'is_completed'}
            for key, value in updates.items():
                if key not in allowed_fields:
                    logger.warning(f"Attempted to update unsupported field '{key}' for task {task_id}.")
                    continue

                if key == 'title':
                    if not isinstance(value, str) or not value.strip():
                        logger.error(f"Invalid title provided for task {task_id}: '{value}'")
                        return None
                    task.title = value.strip()
                elif key == 'description':
                    if value is not None and not isinstance(value, str):
                        logger.error(f"Invalid description type provided for task {task_id}: '{value}'")
                        return None
                    task.description = value.strip() if value else None
                elif key == 'due_date':
                    if value is not None:
                        if isinstance(value, str):
                            try:
                                task.due_date = datetime.datetime.strptime(value, '%Y-%m-%d').date()
                            except ValueError:
                                logger.error(f"Invalid due_date format for task {task_id}: '{value}'")
                                return None
                        elif isinstance(value, datetime.date):
                            task.due_date = value
                        else:
                            logger.error(f"Invalid due_date type for task {task_id}: '{value}'")
                            return None
                    else:
                        task.due_date = None
                elif key == 'is_completed':
                    if not isinstance(value, bool):
                        logger.error(f"Invalid type for is_completed for task {task_id}: '{value}'")
                        return None
                    task.is_completed = value

            task.updated_at = datetime.datetime.now(timezone.utc)
            db.session.commit()
            logger.info(f"Task {task_id} updated successfully for user {user_id}.")
            return task
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating task {task_id} for user {user_id}: {e}", exc_info=True)
            return None

    @staticmethod
    def delete_task(task_id: int, user_id: int) -> bool:
        """
        Deletes a task.

        Args:
            task_id (int): The ID of the task to delete.
            user_id (int): The ID of the user who owns the task (for authorization).

        Returns:
            bool: True if the task was successfully deleted, False otherwise.
        """
        task = TaskService.get_task_by_id(task_id, user_id)
        if not task:
            logger.warning(f"Attempted to delete task {task_id} for user {user_id}, but task not found or not owned.")
            return False

        try:
            db.session.delete(task)
            db.session.commit()
            logger.info(f"Task {task_id} deleted successfully for user {user_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting task {task_id} for user {user_id}: {e}", exc_info=True)
            return False

    @staticmethod
    def mark_task_complete(task_id: int, user_id: int) -> Optional[Task]:
        """
        Marks a task as complete.

        Args:
            task_id (int): The ID of the task to mark complete.
            user_id (int): The ID of the user who owns the task.

        Returns:
            Optional[Task]: The updated Task object if successful, None otherwise.
        """
        logger.info(f"Attempting to mark task {task_id} complete for user {user_id}.")
        return TaskService.update_task(task_id, user_id, {'is_completed': True})

    @staticmethod
    def mark_task_incomplete(task_id: int, user_id: int) -> Optional[Task]:
        """
        Marks a task as incomplete.

        Args:
            task_id (int): The ID of the task to mark incomplete.
            user_id (int): The ID of the user who owns the task.

        Returns:
            Optional[Task]: The updated Task object if successful, None otherwise.
        """
        logger.info(f"Attempting to mark task {task_id} incomplete for user {user_id}.")
        return TaskService.update_task(task_id, user_id, {'is_completed': False})