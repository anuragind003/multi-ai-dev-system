import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy.exc import SQLAlchemyError
import logging

# Configure logging for the test app
logging.basicConfig(level=logging.INFO)

# Import the SQLAlchemy db instance from app.extensions
# This assumes app/extensions.py exists and initializes the SQLAlchemy object.
from app.extensions import db

# Import blueprints from the main application
# Based on the provided RAG context, these are the expected blueprint names and paths.
from app.routes.lead_routes import lead_bp
from app.routes.admin import admin_bp
from app.routes.reports import reports_bp # Using 'reports_bp' as defined in app/routes/reports.py

# Import models so SQLAlchemy can discover them for db.create_all()
# This assumes app/models.py exists and defines these ORM models.
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign

# Assuming 'config' module is available (e.g., config.py at project root)
# and it defines a 'Config' class.
# If 'config.py' is inside 'app' directory, this import would be 'from app.config import Config'
from config import Config

def create_app(test_config=None):
    """
    Creates and configures a Flask application instance for integration testing.

    Args:
        test_config (dict, optional): A dictionary of configuration overrides for testing.
                                     Defaults to None, in which case default test config is used.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__, instance_relative_config=True)

    # Load default configuration from Config class
    app.config.from_object(Config)

    # Override with test-specific configurations
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get('TEST_DATABASE_URL', 'postgresql://test_user:test_password@localhost:5432/cdp_test_db'),
        # Add other test-specific overrides here if needed
    )

    if test_config:
        # Apply any additional test_config overrides
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists (for config files, etc.)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Directory already exists

    # Initialize extensions
    db.init_app(app)
    CORS(app) # Enable CORS for the app, though less critical for integration tests

    # Register blueprints
    app.register_blueprint(lead_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reports_bp)

    # Set up application context for database operations
    with app.app_context():
        try:
            # Drop and create all tables for a clean test environment
            # This is crucial for integration tests to ensure isolation between tests.
            db.drop_all()
            db.create_all()
            app.logger.info("Database tables dropped and recreated for testing.")
        except SQLAlchemyError as e:
            app.logger.error(f"Error during database setup for testing: {e}")
            # In a real test suite, this might raise an exception to fail the test setup.
            # For now, just log the error.

    return app