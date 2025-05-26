import os

class Config:
    """Base configuration."""
    # Secret key for session management and other security features.
    # It's recommended to set this via an environment variable in production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_development_or_testing_only'

    # Path to the SQLite database file.
    # os.path.abspath(os.path.dirname(__file__)) gets the directory of the current file (config.py).
    # This ensures the database file is located relative to the project root or config file.
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'products.db')

    # Debug mode. Should be False in production.
    DEBUG = False

    # Testing mode.
    TESTING = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Use a separate database file for development to avoid mixing with production data.
    DATABASE_PATH = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'products_dev.db')

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True # Often useful to see errors during testing
    # Use an in-memory SQLite database for tests for speed and isolation.
    DATABASE_PATH = ':memory:'

# You can add a ProductionConfig if specific production settings are needed,
# though for this simple project, the base Config might suffice for production
# if environment variables are properly set.
# class ProductionConfig(Config):
#     """Production configuration."""
#     # Ensure SECRET_KEY is set via environment variable in production.
#     # DATABASE_PATH might point to a more robust location or a different DB type.
#     pass