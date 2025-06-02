"""
This module initializes Flask extensions without binding them to a specific
Flask application instance.

This approach supports the Flask application factory pattern, allowing for
flexible application creation and preventing circular import issues.
The extensions will be bound to the Flask app in the application's
initialization file (e.g., app/__init__.py).
"""

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

# Initialize SQLAlchemy for database operations.
# It will be bound to the Flask app instance in app/__init__.py.
db = SQLAlchemy()

# Initialize Bcrypt for secure password hashing and verification.
# This is crucial for securely storing user passwords as per NFR4.3.1.
# It will be bound to the Flask app instance in app/__init__.py.
bcrypt = Bcrypt()

# Initialize JWTManager for handling JSON Web Tokens for authentication.
# This enables secure, stateless user authentication.
# It will be bound to the Flask app instance in app/__init__.py.
jwt = JWTManager()