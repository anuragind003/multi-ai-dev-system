python
### FILE: routers/tasks.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..models import Task, User
from ..schemas import TaskCreate, TaskUpdate, Task
from ..security import get_current_user
import logging

router = APIRouter()

# Configure logging for this module
logger = logging.getLogger(__name__)

@router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
async def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new task.
    """
    try:
        db_task = Task(**task.dict(), owner_id=current_user.id)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Task created: {db_task.title} by user {current_user.username}")
        return db_task
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task")

@router.get("/tasks", response_model=List[Task])
async def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve all tasks for the current user.
    """
    try:
        tasks = db.query(Task).filter(Task.owner_id == current_user.id).offset(skip).limit(limit).all()
        logger.info(f"Tasks retrieved for user {current_user.username}")
        return tasks
    except Exception as e:
        logger.error(f"Error reading tasks: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve tasks")

@router.get("/tasks/{task_id}", response_model=Task)
async def read_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Retrieve a specific task by ID.
    """
    try:
        db_task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
        if not db_task:
            logger.warning(f"Task not found: {task_id} for user {current_user.username}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        logger.info(f"Task retrieved: {db_task.title} by user {current_user.username}")
        return db_task
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error reading task {task_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to retrieve task")

@router.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: int, task: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a specific task.
    """
    try:
        db_task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
        if not db_task:
            logger.warning(f"Task not found: {task_id} for user {current_user.username}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        for key, value in task.dict(exclude_unset=True).items():
            setattr(db_task, key, value)

        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        logger.info(f"Task updated: {db_task.title} by user {current_user.username}")
        return db_task
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating task {task_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update task")

@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a specific task.
    """
    try:
        db_task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
        if not db_task:
            logger.warning(f"Task not found: {task_id} for user {current_user.username}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

        db.delete(db_task)
        db.commit()
        logger.info(f"Task deleted: {task_id} by user {current_user.username}")
    except HTTPException as e:
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting task {task_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete task")