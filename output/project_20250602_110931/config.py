import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables from a .env file if it exists.
# This allows for easy management of sensitive data and environment-specific settings.
load_dotenv()

# Define the base directory of the project.
# This assumes config.py is located at the root level of the project.
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """
    Base configuration class.
    Contains settings common to all environments (development, testing, production).
    """
    # Flask Secret Key: Used for signing session cookies and other security-related needs.
    # It's crucial to keep this secret and load it from an environment variable in production.
    # A fallback is provided for development convenience, but it's insecure for production.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_that_should_be_changed_in_production_and_is_long_enough'

    # SQLAlchemy Configuration:
    # Disable tracking modifications to save memory and avoid unnecessary overhead.
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT (JSON Web Token) Configuration:
    # Used for token-based authentication (e.g., with Flask-JWT-Extended).
    # JWT Secret Key: Similar to Flask's SECRET_KEY, must be kept secret.
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super_secret_jwt_key_for_development_only'
    # Access Token Expiration: How long an access token is valid.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    # Refresh Token Expiration: How long a refresh token is valid (for obtaining new access tokens).
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # Application-specific settings can be added here if they are global.

class DevelopmentConfig(Config):
    """
    Development environment configuration.
    Enables debug mode and uses a local SQLite database file.
    """
    DEBUG = True
    # Database URI for development.
    # Prioritize environment variable 'DEV_DATABASE_URL', otherwise use a local SQLite file.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'sqlite:///' + os.path.join(BASE_DIR, 'site.db')

class TestingConfig(Config):
    """
    Testing environment configuration.
    Enables testing mode and uses an in-memory SQLite database for isolated tests.
    """
    TESTING = True
    DEBUG = True # Debug mode can be useful during testing for detailed error messages.
    # Database URI for testing.
    # Prioritize environment variable 'TEST_DATABASE_URL', otherwise use an in-memory SQLite.
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'sqlite:///:memory:' # In-memory database for fast, ephemeral tests.

class ProductionConfig(Config):
    """
    Production environment configuration.
    Disables debug and testing modes and requires a PostgreSQL database URI from environment variables.
    """
    DEBUG = False # Debug mode must be OFF in production for security and performance.
    TESTING = False
    # Database URI for production.
    # This MUST be set as an environment variable (e.g., 'DATABASE_URL') for production deployment.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Ensure the production database URL is set. Raise an error if it's missing.
    if SQLALCHEMY_DATABASE_URI is None:
        raise ValueError("DATABASE_URL environment variable not set for Production environment.")

# Dictionary to map environment names to their respective configuration classes.
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Default to development if FLASK_ENV is not explicitly set.
}

def get_config(env_name: str = None):
    """
    Returns the appropriate configuration class based on the provided environment name.
    If `env_name` is not provided, it defaults to the `FLASK_ENV` environment variable.
    If `FLASK_ENV` is also not set, it defaults to 'development'.

    Args:
        env_name (str, optional): The name of the environment (e.g., 'development', 'testing', 'production').
                                  Defaults to None, which triggers environment variable lookup.

    Returns:
        Config: An instance of the configuration class for the specified environment.

    Raises:
        ValueError: If an invalid environment name is provided via `env_name` or `FLASK_ENV`.
    """
    if env_name is None:
        # Get the environment name from the FLASK_ENV environment variable, default to 'development'.
        env_name = os.environ.get('FLASK_ENV', 'development')

    # Retrieve the configuration class from the mapping.
    config_class = config_by_name.get(env_name)

    # Raise an error if the environment name is not recognized.
    if config_class is None:
        valid_envs = ', '.join(config_by_name.keys())
        raise ValueError(f"Invalid FLASK_ENV '{env_name}'. Must be one of: {valid_envs}")

    return config_class