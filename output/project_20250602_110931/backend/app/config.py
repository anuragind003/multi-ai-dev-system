import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Base configuration class for the Flask application.
    Contains common settings applicable to all environments.
    """
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_should_be_changed_in_production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Default database URI, can be overridden by environment-specific configs
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///site.db'
    # Security settings
    PASSWORD_SALT = os.environ.get('PASSWORD_SALT') or 'super_secret_salt_for_hashing'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'another_jwt_secret_key_for_tokens'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 3600)) # 1 hour in seconds

class DevelopmentConfig(Config):
    """
    Development specific configuration.
    Uses SQLite database and enables debug mode.
    """
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or 'sqlite:///dev_site.db'

class TestingConfig(Config):
    """
    Testing specific configuration.
    Uses an in-memory SQLite database for fast, isolated tests.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:' # In-memory SQLite database for tests
    # Disable CSRF protection for easier testing if Flask-WTF is used
    WTF_CSRF_ENABLED = False
    # JWT tokens expire quickly for testing purposes
    JWT_ACCESS_TOKEN_EXPIRES = 60 # 1 minute for testing

class ProductionConfig(Config):
    """
    Production specific configuration.
    Disables debug mode and expects a PostgreSQL database.
    """
    DEBUG = False
    # In production, always expect DATABASE_URL to be set for PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@host:port/dbname'
    # Ensure a strong secret key is set in the environment
    if not Config.SECRET_KEY or Config.SECRET_KEY == 'a_very_secret_key_that_should_be_changed_in_production':
        raise ValueError("SECRET_KEY must be set in environment for production.")
    if not Config.PASSWORD_SALT or Config.PASSWORD_SALT == 'super_secret_salt_for_hashing':
        raise ValueError("PASSWORD_SALT must be set in environment for production.")
    if not Config.JWT_SECRET_KEY or Config.JWT_SECRET_KEY == 'another_jwt_secret_key_for_tokens':
        raise ValueError("JWT_SECRET_KEY must be set in environment for production.")

# Dictionary to map environment names to their respective configuration classes
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Default to development if FLASK_ENV is not set
}

def get_config(env_name: str = 'default'):
    """
    Retrieves the appropriate configuration class based on the environment name.

    Args:
        env_name (str): The name of the environment (e.g., 'development', 'testing', 'production').

    Returns:
        Config: An instance of the configuration class for the specified environment.
    """
    return config_by_name.get(env_name, config_by_name['default'])