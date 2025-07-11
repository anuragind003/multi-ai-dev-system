from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from ..schemas import TaskCreate, TaskUpdate, TaskResponse
from ..services import TaskService
from ..auth import get_current_user, User

router = APIRouter()

@router.post("/tasks", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Create a new task")
async def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new task.
    """
    task_service = TaskService(db)
    return task_service.create_task(task, current_user.id)

@router.get("/tasks/{task_id}", response_model=TaskResponse, summary="Get a task by ID")
async def read_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get a task by its ID.
    """
    task_service = TaskService(db)
    return task_service.get_task(task_id, current_user.id)

@router.put("/tasks/{task_id}", response_model=TaskResponse, summary="Update a task")
async def update_task(task_id: int, task_update: TaskUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Update a task.
    """
    task_service = TaskService(db)
    return task_service.update_task(task_id, task_update, current_user.id)

@router.delete("/tasks/{task_id}", status_code=status.HTTP_200_OK, summary="Delete a task")
async def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Delete a task.
    """
    task_service = TaskService(db)
    return task_service.delete_task(task_id, current_user.id)

@router.get("/tasks", response_model=List[TaskResponse], summary="Get all tasks")
async def read_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Get all tasks for the current user.
    """
    task_service = TaskService(db)
    return task_service.get_all_tasks(current_user.id)