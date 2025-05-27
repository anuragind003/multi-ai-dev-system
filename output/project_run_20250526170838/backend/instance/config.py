import os

# Define the base directory of the project for relative paths.
# This assumes config.py is located at `backend/instance/config.py`
# and the project root is two levels up from `instance`.
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class Config:
    """Base configuration class. Contains common settings for all environments."""

    # Flask Secret Key: Used for session management, CSRF protection, etc.
    # For development, a default is provided. In production, it MUST be set via an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_development_only_change_this_in_production'

    # SQLAlchemy configuration
    # Disable tracking modifications to save memory, as it's not needed with Flask-SQLAlchemy 2.x
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Default database URI. This can be overridden by environment-specific configurations
    # or by the DATABASE_URL environment variable.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # File upload and download directories as per BRD and System Design.
    # These paths are relative to the project's base directory.
    UPLOAD_FOLDER = os.path.join(basedir, 'uploads')
    MOENGAGE_EXPORT_FOLDER = os.path.join(basedir, 'exports', 'moengage')
    DUPLICATE_DATA_FOLDER = os.path.join(basedir, 'exports', 'duplicates')
    UNIQUE_DATA_FOLDER = os.path.join(basedir, 'exports', 'unique')
    ERROR_DATA_FOLDER = os.path.join(basedir, 'exports', 'errors')

    # Ensure that all necessary directories exist when the configuration is loaded.
    # `exist_ok=True` prevents an error if the directory already exists.
    for folder in [UPLOAD_FOLDER, MOENGAGE_EXPORT_FOLDER, DUPLICATE_DATA_FOLDER, UNIQUE_DATA_FOLDER, ERROR_DATA_FOLDER]:
        os.makedirs(folder, exist_ok=True)

    # Maximum content length for file uploads (e.g., 16 MB for CSV/Excel files)
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Megabytes

    # Logging level (can be overridden by specific environments)
    LOG_LEVEL = 'INFO'

class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True  # Enable debug mode for development
    # Specific development database URI. Prioritizes DEV_DATABASE_URL env var, then a default local path.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
                              'postgresql://cdp_dev_user:cdp_dev_password@localhost:5432/cdp_dev_db'
    LOG_LEVEL = 'DEBUG' # More verbose logging in development

class TestingConfig(Config):
    """Testing specific configuration."""
    TESTING = True  # Enable testing mode
    DEBUG = True    # Often useful to keep debug on during testing for more verbose output
    # Specific testing database URI. Prioritizes TEST_DATABASE_URL env var, then a default local path.
    # Using a dedicated test database is crucial to avoid polluting development/production data.
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
                              'postgresql://cdp_test_user:cdp_test_password@localhost:5432/cdp_test_db'
    # Use a distinct secret key for testing to ensure isolation
    SECRET_KEY = 'test_secret_key_for_testing_environment'
    LOG_LEVEL = 'INFO' # Keep logs clean during tests unless specifically debugging

class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False  # Disable debug mode in production for security and performance
    # In production, SECRET_KEY and DATABASE_URL MUST be set as environment variables.
    # We retrieve them here. The application factory (e.g., in backend/__init__.py)
    # should be responsible for validating their presence and raising an error if critical
    # variables are missing, rather than failing during module import.
    SECRET_KEY = os.environ.get('SECRET_KEY')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

    # Print warnings if critical environment variables are not set.
    # The actual application startup should then explicitly check and fail if these are None.
    if SECRET_KEY is None:
        print("WARNING: SECRET_KEY environment variable is not set for Production environment. Application might not function correctly.")
    if SQLALCHEMY_DATABASE_URI is None:
        print("WARNING: DATABASE_URL environment variable is not set for Production environment. Application might not function correctly.")

    LOG_LEVEL = 'WARNING' # Only log warnings and errors in production

# Dictionary to easily retrieve the correct configuration class based on the environment name.
# This allows dynamic loading of configurations based on FLASK_ENV or similar environment variables.
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Default to development if no specific environment is set
}