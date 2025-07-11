# basic_crud_query_templates.py
# Provides basic CRUD query templates using SQLAlchemy.

from sqlalchemy import text
from connection_management import SessionManager
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    metadata = Column(JSON)

# CRUD operations using SQLAlchemy
def create_task(description: str, metadata: dict = None):
    with SessionManager() as db:
        try:
            new_task = Task(description=description, metadata=metadata)
            db.add(new_task)
            db.commit()
            db.refresh(new_task)
            return new_task.id
        except Exception as e:
            db.rollback()
            print(f"Error creating task: {e}")
            return None

def get_task_by_id(task_id: str):
    with SessionManager() as db:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            return task
        except Exception as e:
            print(f"Error getting task by ID: {e}")
            return None

def update_task(task_id: str, description: str, metadata: dict = None):
    with SessionManager() as db:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.description = description
                task.metadata = metadata
                db.commit()
                db.refresh(task)
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            print(f"Error updating task: {e}")
            return False

def delete_task(task_id: str):
    with SessionManager() as db:
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                db.delete(task)
                db.commit()
                return True
            else:
                return False
        except Exception as e:
            db.rollback()
            print(f"Error deleting task: {e}")
            return False

# Example usage (for testing)
if __name__ == '__main__':
    # Create a task
    task_id = create_task("Test task", {"status": "pending"})
    if task_id:
        print(f"Created task with ID: {task_id}")

        # Get the task
        retrieved_task = get_task_by_id(task_id)
        if retrieved_task:
            print(f"Retrieved task: {retrieved_task.description}")

        # Update the task
        if update_task(task_id, "Updated test task", {"status": "in progress"}):
            print("Task updated successfully")

        # Delete the task
        if delete_task(task_id):
            print("Task deleted successfully")
    else:
        print("Failed to create task")