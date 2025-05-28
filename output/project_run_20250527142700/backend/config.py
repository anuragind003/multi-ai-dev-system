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

    # File export names (for FR30-FR33)
    MOENGAGE_FILE_NAME = "moengage_campaign_data.csv"
    DUPLICATE_FILE_NAME = "duplicate_customer_data.csv"
    UNIQUE_FILE_NAME = "unique_customer_data.csv"
    ERROR_FILE_NAME = "data_ingestion_errors.xlsx"

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    # Default database URI for local development
    _db_url = os.environ.get('DATABASE_URL', 'postgresql://cdp_user:cdp_password@localhost:5432/cdp_dev')
    SQLALCHEMY_DATABASE_URI = _db_url.replace('postgres://', 'postgresql://') if _db_url else None

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Use an in-memory SQLite database for fast testing, or a dedicated test PostgreSQL DB
    _test_db_url = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_DATABASE_URI = _test_db_url.replace('postgres://', 'postgresql://') if _test_db_url else None
    WTF_CSRF_ENABLED = False # Disable CSRF for easier testing of forms/APIs

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    # In production, DATABASE_URL MUST be set in the environment.
    # If it's not set, SQLALCHEMY_DATABASE_URI will be None, and Flask-SQLAlchemy will raise an error
    # when attempting to connect, which is the desired behavior for a missing critical production variable.
    _prod_db_url = os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = _prod_db_url.replace('postgres://', 'postgresql://') if _prod_db_url else None


# Dictionary to easily select config based on environment
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig # Fallback to development if no env is specified
}