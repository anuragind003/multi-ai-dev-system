from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.extensions import db

class Task(db.Model):
    """
    SQLAlchemy model for the 'Task' entity.

    Defines the structure of the tasks table in the database, including fields
    for ID, title, description, due date, completion status, and a foreign key
    linking to the User who owns the task.
    """
    __tablename__ = 'tasks'

    id: Column[int] = Column(Integer, primary_key=True)
    title: Column[str] = Column(String(120), nullable=False)
    description: Column[Optional[str]] = Column(Text, nullable=True)
    due_date: Column[Optional[datetime]] = Column(DateTime, nullable=True)
    completed: Column[bool] = Column(Boolean, default=False, nullable=False)
    created_at: Column[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Column[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Foreign key to the 'users' table
    user_id: Column[int] = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Define a relationship with the User model.
    # This allows accessing the associated User object from a Task instance (e.g., task.user).
    # 'backref' creates a 'tasks' attribute on the User model, allowing access to
    # all tasks for a user (e.g., user.tasks).
    user: relationship = relationship('User', backref=db.backref('tasks', lazy=True))

    def __repr__(self) -> str:
        """
        Returns a string representation of the Task object, useful for debugging.
        """
        return f'<Task {self.id}: {self.title} (User: {self.user_id})>'

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the Task object to a dictionary, suitable for JSON serialization.
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed': self.completed,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'user_id': self.user_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        Creates a Task object from a dictionary.
        Useful for creating new tasks from incoming request data.
        """
        # Ensure required fields are present and valid
        if 'title' not in data or not isinstance(data['title'], str) or not data['title'].strip():
            raise ValueError("Task 'title' is required and cannot be empty.")
        
        if 'user_id' not in data or not isinstance(data['user_id'], int):
            raise ValueError("Task 'user_id' is required and must be an integer.")

        # Convert due_date string to datetime object if provided
        due_date: Optional[datetime] = None
        if 'due_date' in data and data['due_date']:
            try:
                due_date = datetime.fromisoformat(data['due_date'])
            except ValueError:
                raise ValueError("Invalid 'due_date' format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS.ffffff).")

        # Validate 'completed' if provided, otherwise default
        completed: bool = data.get('completed', False)
        if not isinstance(completed, bool):
            raise ValueError("Task 'completed' must be a boolean value.")

        return cls(
            title=data['title'].strip(), # Strip whitespace from title
            description=data.get('description'),
            due_date=due_date,
            completed=completed,
            user_id=data['user_id']
        )