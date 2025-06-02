from datetime import datetime
import logging
from app.extensions import db

logger = logging.getLogger(__name__)

class Task(db.Model):
    """
    Represents a task in the Simple Task Tracker application.

    Attributes:
        id (int): Primary key for the task.
        title (str): The title of the task (e.g., "Buy groceries"). Must not be null.
        description (str): A detailed description of the task. Can be null.
        due_date (datetime): The optional due date and time for the task. Can be null.
        completed (bool): Indicates whether the task has been completed. Defaults to False.
        user_id (int): Foreign key linking the task to its owning user. Must not be null.
        user (User): Relationship to the User model, allowing access to the user object.
    """
    __tablename__ = 'task'

    id: db.Mapped[int] = db.Column(db.Integer, primary_key=True)
    title: db.Mapped[str] = db.Column(db.String(120), nullable=False)
    description: db.Mapped[str | None] = db.Column(db.Text, nullable=True)
    due_date: db.Mapped[datetime | None] = db.Column(db.DateTime, nullable=True)
    completed: db.Mapped[bool] = db.Column(db.Boolean, default=False, nullable=False)

    user_id: db.Mapped[int] = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    user: db.Mapped['User'] = db.relationship('User', backref='tasks', lazy=True)

    def __repr__(self) -> str:
        """
        Returns a string representation of the Task object, useful for debugging.
        """
        return f"<Task {self.id}: '{self.title}' (User: {self.user_id}, Completed: {self.completed})>"

    def to_dict(self) -> dict:
        """
        Converts the Task object to a dictionary, useful for serializing to JSON
        for API responses.
        """
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed': self.completed,
            'user_id': self.user_id
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """
        Creates a Task object from a dictionary, typically used when receiving
        task data from an API request (e.g., JSON payload).

        Args:
            data (dict): A dictionary containing task attributes.
                         Expected keys: 'title', 'description' (optional),
                         'due_date' (optional, ISO 8601 string), 'completed' (optional).
                         Note: 'user_id' is typically set by the application logic
                         (e.g., from the authenticated user's ID) rather than directly
                         from the input dictionary for security reasons.

        Returns:
            Task: A new Task instance populated with the provided data.
        """
        task = cls(
            title=data.get('title'),
            description=data.get('description'),
            completed=data.get('completed', False)
        )

        if 'due_date' in data and data['due_date']:
            try:
                if isinstance(data['due_date'], str):
                    task.due_date = datetime.fromisoformat(data['due_date'])
                elif isinstance(data['due_date'], datetime):
                    task.due_date = data['due_date']
            except ValueError:
                logger.warning(f"Could not parse due_date '{data['due_date']}' for task '{data.get('title')}'. Setting to None.")
                task.due_date = None
        return task