import os

# Define the base directory of the application
# This assumes config.py is located in the 'app' directory
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Base configuration class."""
    DEBUG = False
    TESTING = False
    # A strong secret key is crucial for security in production.
    # It should be loaded from an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_strong_and_random_secret_key_for_development'

    # SQLite database configuration
    # The database file will be located in the 'app' directory
    DATABASE = os.path.join(basedir, 'products.db')

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = True

class ProductionConfig(Config):
    """Production configuration."""
    # In a production environment, DEBUG should always be False
    # and SECRET_KEY must be set via environment variables.
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = True # Keep debug true for easier testing feedback
    # Use an in-memory SQLite database for testing to ensure a clean state for each test run
    DATABASE = ':memory:'

# Dictionary to easily select configurations based on environment
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig # Default to development if no specific config is chosen
}