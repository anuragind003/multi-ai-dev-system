from flask import Flask
from flask_sqlalchemy import SQLAlchemy

class TestConfig:
    """Configuration for the test Flask app."""
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:" # Use in-memory SQLite for fast unit tests
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True

def create_test_app():
    """
    Creates and configures a Flask application instance specifically for unit testing.
    It sets up an in-memory SQLite database for isolated and fast tests.
    """
    app = Flask(__name__)
    app.config.from_object(TestConfig)

    # Initialize SQLAlchemy directly with the app instance.
    # This creates a new SQLAlchemy instance for each test app,
    # ensuring isolation between test runs.
    db = SQLAlchemy(app)
    app.db = db # Attach the db instance to the app for easy access in tests

    # For unit tests, we typically don't register all blueprints or routes
    # unless we are specifically testing route-level logic.
    # This setup is primarily for testing models and services that interact with the database.

    return app