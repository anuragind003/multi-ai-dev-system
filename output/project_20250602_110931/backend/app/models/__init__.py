# backend/app/models/__init__.py

# This file initializes the 'models' package for the Flask application.
# Its primary purpose is to make SQLAlchemy model classes (like User and Task)
# defined in separate submodules directly accessible when the 'models' package is imported.
# For example, instead of 'from app.models.user import User', you can use
# 'from app.models import User' after these imports are set up here.

# Import the User model.
from .user import User

# Import the Task model.
from .task import Task

# Define __all__ to explicitly list the public objects that should be imported
# when 'from app.models import *' is used. This is good practice for package design.
__all__ = [
    'User',
    'Task',
]