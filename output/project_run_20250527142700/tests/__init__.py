import os
from flask import Flask
from flask_cors import CORS

# Import the SQLAlchemy db instance from app.extensions
# This assumes app/extensions.py exists and initializes the SQLAlchemy object.
from app.extensions import db

# Import blueprints from the main application
# These imports assume the structure app/routes/lead_routes.py, app/routes/admin.py, app/routes/report_routes.py
from app.routes.lead_routes import lead_bp
from app.routes.admin import admin_bp
from app.routes.report_routes import report_bp

# Import models so SQLAlchemy can discover them for db.create_all()
# This assumes app/models.py exists and defines these ORM models
from app.models import Customer, Offer, CustomerEvent, DataIngestionLog, Campaign


def create_app(test_config=None):
    """
    Application factory function for creating a Flask app instance.
    This function is primarily used for setting up the application for testing,
    allowing for different configurations (e.g., a dedicated test database).
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    # Configure the application
    app.config.from_mapping(
        SECRET_KEY='dev',  # A secret key for development/testing
        # Default to in-memory SQLite for tests for speed and simplicity.
        # For tests requiring PostgreSQL-specific features, this can be overridden
        # by passing a test_config with a PostgreSQL URI.
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        TESTING=True,  # Enable testing mode
    )

    if test_config:
        # Load the test config if passed in, overriding any defaults
        app.config.from_mapping(test_config)

    # Ensure the instance folder exists (optional for tests, but good practice for app factory)
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    app.register_blueprint(lead_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)

    # Create database tables for tests
    # This ensures a clean database for each test run.
    # It's crucial to do this within an application context.
    with app.app_context():
        db.create_all()

    return app