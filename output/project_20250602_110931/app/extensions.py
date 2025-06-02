from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager

# Initialize Flask extensions without binding them to an app instance yet.
# This allows for flexible application creation, especially useful for testing
# and managing circular imports in larger applications.
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def init_app(app: Flask):
    """
    Initializes Flask extensions with the given Flask application instance.

    This function centralizes the setup of all extensions, ensuring they are
    properly configured with the application's settings (e.g., database URI,
    secret keys). It should be called from the application factory function.

    Args:
        app: The Flask application instance.
    """
    # Initialize SQLAlchemy with the Flask app.
    # Database URI and other SQLAlchemy configurations (e.g.,
    # SQLALCHEMY_TRACK_MODIFICATIONS) are expected to be set in app.config.
    # Example: app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    db.init_app(app)

    # Initialize Flask-Bcrypt for secure password hashing and verification.
    # This extension handles the complexity of salting and hashing passwords.
    bcrypt.init_app(app)

    # Initialize Flask-JWT-Extended for JWT-based authentication.
    # This manages the creation, signing, and verification of JSON Web Tokens.
    # It requires 'JWT_SECRET_KEY' to be set in app.config for token signing.
    # Example: app.config['JWT_SECRET_KEY'] = 'your_super_secret_jwt_key'
    jwt.init_app(app)

    # Additional configurations or callbacks for JWTManager (e.g.,
    # user identity loading, token revocation) are typically defined in
    # authentication blueprints or models for better organization,
    # but the core manager is initialized here.