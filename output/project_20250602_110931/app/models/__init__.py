# app/models/__init__.py

# This file initializes the 'models' package.
# Its primary purpose is to import all defined model classes,
# making them easily accessible from the 'app.models' namespace.
# For example, instead of 'from app.models.user import User',
# you can use 'from app.models import User'.

from .user import User
from .task import Task

# Define what symbols are exposed when 'from app.models import *' is used.
__all__ = [
    'User',
    'Task',
]

# Note: The SQLAlchemy database instance (e.g., 'db') is typically
# initialized in the main application factory (e.g., 'app/__init__.py')
# and then imported into individual model files (like 'user.py' and 'task.py')
# to define the model schema. This '__init__.py' file focuses solely
# on package structure and model accessibility.