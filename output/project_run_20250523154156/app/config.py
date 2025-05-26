import os

# Determine the base directory of the application.
# This assumes config.py is located in the 'app' directory,
# and the database file will be one level up (in the project root).
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class with common settings."""
    # A secret key is essential for Flask applications for session management,
    # CSRF protection, etc. For development, a hardcoded key is used as a fallback.
    # In a production environment, SECRET_KEY MUST be set via environment variables
    # and should be a strong, randomly generated string.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_development_and_testing_only'

    # Database configuration for SQLite
    DATABASE_NAME = 'products.db'
    # The database file will be located in the project root directory.
    DATABASE_PATH = os.path.join(basedir, '..', DATABASE_NAME)

class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True
    # For development, we use the default database path defined in Config.
    # If a separate development database file was desired, it could be overridden here.
    # Example: DATABASE_NAME = 'products_dev.db'
    #          DATABASE_PATH = os.path.join(basedir, '..', DATABASE_NAME)

class TestingConfig(Config):
    """Testing specific configuration."""
    TESTING = True
    DEBUG = True  # Often useful to see full tracebacks during testing.
    # Use an in-memory SQLite database for testing for isolation and speed.
    # This means the database is created in RAM and cleared after the application stops.
    DATABASE_NAME = ':memory:' # Special name for in-memory SQLite
    DATABASE_PATH = DATABASE_NAME # Path is just the special name for in-memory

class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False
    TESTING = False
    # In production, SECRET_KEY should always be provided via environment variables.
    # The base Config provides a fallback, but for a real production system,
    # it's critical to ensure this is set externally.
    # For this MVP, the fallback is acceptable as per the simplicity NFR.