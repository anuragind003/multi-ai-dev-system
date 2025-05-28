import os

class Config:
    """Base configuration."""
    # Secret key for Flask sessions, CSRF protection, etc.
    # In production, this should be a strong, randomly generated value loaded from an environment variable.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_development_only_change_this_in_production')

    # Flask-SQLAlchemy configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppresses a warning from Flask-SQLAlchemy

    # Data retention periods (from NFRs and BRD)
    OFFER_HISTORY_RETENTION_MONTHS = 6 # FR20, NFR10
    CDP_DATA_RETENTION_MONTHS = 3 # FR29, NFR11

    # Other common configurations can be added here
    # For example, pagination limits, default API versions, etc.
    # MOENGAGE_EXPORT_BATCH_SIZE = 10000

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Default database URI for local development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://cdp_user:cdp_password@localhost:5432/cdp_dev')

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Use a dedicated test database or an in-memory SQLite for faster tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'postgresql://cdp_user:cdp_password@localhost:5432/cdp_test')
    PRESERVE_CONTEXT_ON_EXCEPTION = False # Useful for testing

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # In production, DATABASE_URL must be set as an environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Add more production-specific settings like logging, error handling, etc.
    # SQLALCHEMY_ECHO = False # Don't log SQL queries in production
    # LOG_LEVEL = 'INFO'
    # SENTRY_DSN = os.environ.get('SENTRY_DSN') # Example for error tracking