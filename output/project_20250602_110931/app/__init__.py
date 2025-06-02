import os
from datetime import timedelta
from typing import Optional

from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, ExpiredSignatureError, InvalidTokenError, exceptions as jwt_exceptions
from werkzeug.exceptions import HTTPException

# Initialize Flask extensions globally
# These instances will be initialized with the Flask app inside create_app
db = SQLAlchemy()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(test_config: Optional[dict] = None) -> Flask:
    """
    Flask application factory function.

    This function creates and configures the Flask app instance.
    It handles:
    - Loading configuration from files or test_config.
    - Initializing Flask extensions (SQLAlchemy, Bcrypt, JWTManager).
    - Registering blueprints for different parts of the application (auth, tasks).
    - Setting up CLI commands (e.g., for database initialization).
    - Defining global error handlers for common HTTP and JWT-specific errors.

    Args:
        test_config (dict, optional): A dictionary of configuration to override
                                      default settings, typically used for testing.
                                      Defaults to None.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    # --- Application Configuration ---
    # Load configuration from config.py or test_config
    if test_config is None:
        # Load the instance config from config.py if it exists, when not testing.
        # `silent=True` means it won't raise an error if config.py is missing.
        app.config.from_pyfile('config.py', silent=True)
    else:
        # Load the test config passed in for testing purposes.
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists. This folder is used for configurations
    # and for the SQLite database file in development.
    try:
        os.makedirs(app.instance_path)
    except OSError:
        # If the directory already exists, an OSError will be raised.
        # We can ignore it as the goal is just to ensure it exists.
        pass

    # Set default configurations if they are not already set by config.py or test_config.
    # These provide sensible defaults for development and can be overridden.
    app.config.setdefault('SECRET_KEY', os.environ.get('SECRET_KEY', 'a_very_secret_dev_key_that_should_be_changed_in_production'))
    # Database URI: Uses SQLite in the instance folder by default.
    # For production, this should be set in config.py or via environment variables
    # to point to PostgreSQL.
    app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///' + os.path.join(app.instance_path, 'task_tracker.sqlite'))
    app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False) # Suppresses a warning
    app.config.setdefault('JWT_SECRET_KEY', os.environ.get('JWT_SECRET_KEY', 'another_super_secret_jwt_key_for_dev'))
    app.config.setdefault('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1)) # Access tokens expire in 1 hour
    app.config.setdefault('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30)) # Refresh tokens expire in 30 days

    # --- Initialize Extensions ---
    # Initialize the extensions with the Flask application instance.
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)

    # Import models to ensure they are registered with SQLAlchemy's metadata.
    # This is crucial for `db.create_all()` to know which tables to create.
    from . import models # noqa: F401 (ignore unused import warning, it's for side effect)

    # --- Register Blueprints ---
    # Blueprints are used to organize the application into smaller, reusable components.
    # Import them here to avoid potential circular import issues.
    from . import auth
    from . import tasks

    app.register_blueprint(auth.bp)
    app.register_blueprint(tasks.bp)

    # --- CLI Commands ---
    # Register database initialization command with the Flask CLI.
    from . import db_cli
    db_cli.init_app(app)

    # --- Error Handlers ---
    # Define custom error handlers for various HTTP status codes and JWT errors.
    # These handlers return JSON responses, which is typical for APIs.

    @app.errorhandler(404)
    def not_found_error(error: HTTPException):
        """
        Handles 404 Not Found errors.
        Returns a JSON response indicating the resource was not found.
        """
        return jsonify({"message": "Resource not found", "status_code": 404}), 404

    @app.errorhandler(500)
    def internal_server_error(error: Exception):
        """
        Handles 500 Internal Server Errors.
        Logs the error and returns a generic JSON error message.
        """
        # Log the error for debugging purposes in production environments.
        app.logger.error(f"Internal Server Error: {error}")
        return jsonify({"message": "Internal server error", "status_code": 500}), 500

    # JWT specific error handlers from flask_jwt_extended
    @app.errorhandler(ExpiredSignatureError)
    def handle_expired_token_error(e: ExpiredSignatureError):
        """
        Handles JWT expired signature errors (token has passed its expiration time).
        """
        return jsonify({"message": "Token has expired", "status_code": 401}), 401

    @app.errorhandler(InvalidTokenError)
    def handle_invalid_token_error(e: InvalidTokenError):
        """
        Handles general JWT invalid token errors (e.g., malformed token, invalid signature).
        """
        return jsonify({"message": "Invalid token", "status_code": 401}), 401

    @app.errorhandler(jwt_exceptions.NoAuthorizationError)
    def handle_no_authorization_error(e: jwt_exceptions.NoAuthorizationError):
        """
        Handles cases where no authorization token is provided in the request.
        """
        return jsonify({"message": "Authorization token is missing", "status_code": 401}), 401

    @app.errorhandler(jwt_exceptions.WrongTokenError)
    def handle_wrong_token_error(e: jwt_exceptions.WrongTokenError):
        """
        Handles cases where the token type is incorrect (e.g., using a refresh token
        where an access token is expected, or vice-versa).
        """
        return jsonify({"message": "Wrong token type", "status_code": 401}), 401

    @app.errorhandler(jwt_exceptions.RevokedTokenError)
    def handle_revoked_token_error(e: jwt_exceptions.RevokedTokenError):
        """
        Handles cases where the token has been explicitly revoked (e.g., during logout).
        """
        return jsonify({"message": "Token has been revoked", "status_code": 401}), 401

    # General 401 Unauthorized handler. This can catch issues not specifically
    # related to JWT, or if JWT errors are not caught by the specific handlers above.
    @app.errorhandler(401)
    def unauthorized_error(error: HTTPException):
        """
        Handles general 401 Unauthorized errors.
        """
        return jsonify({"message": "Unauthorized access", "status_code": 401}), 401

    # --- Simple Health Check Route ---
    # A basic endpoint to check if the application is running.
    @app.route('/health')
    def health_check():
        """
        A simple health check endpoint for monitoring.
        Returns a JSON response indicating the application's status.
        """
        return jsonify({"status": "ok", "message": "Task Tracker API is running!"}), 200

    return app