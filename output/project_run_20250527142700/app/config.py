import os

class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev_or_testing')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Data retention periods as per BRD
    OFFER_HISTORY_RETENTION_MONTHS = 6
    CDP_DATA_RETENTION_MONTHS = 3

    # File upload and download paths (relative to project root or absolute)
    # These directories should be created during application startup if they don't exist.
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
    MOENGAGE_FILE_GENERATION_PATH = os.path.join(os.getcwd(), 'generated_files', 'moengage')
    DUPLICATE_DATA_FILE_PATH = os.path.join(os.getcwd(), 'generated_files', 'duplicates')
    UNIQUE_DATA_FILE_PATH = os.path.join(os.getcwd(), 'generated_files', 'unique')
    ERROR_DATA_FILE_PATH = os.path.join(os.getcwd(), 'generated_files', 'errors')

    # CORS origins - adjust as needed for frontend deployment
    # In a real application, this would typically be loaded from an environment variable
    # and parsed into a list. For development, a fixed list is common.
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
    LOG_LEVEL = 'DEBUG'
    # Development specific CORS origins
    CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]

class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    # Use a dedicated test database or in-memory SQLite for unit tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'postgresql://test_user:test_password@localhost:5433/cdp_test_db')
    LOG_LEVEL = 'INFO'
    # Override paths for testing to avoid polluting actual directories
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'test_uploads')
    MOENGAGE_FILE_GENERATION_PATH = os.path.join(os.getcwd(), 'test_generated_files', 'moengage')
    DUPLICATE_DATA_FILE_PATH = os.path.join(os.getcwd(), 'test_generated_files', 'duplicates')
    UNIQUE_DATA_FILE_PATH = os.path.join(os.getcwd(), 'test_generated_files', 'unique')
    ERROR_DATA_FILE_PATH = os.path.join(os.getcwd(), 'test_generated_files', 'errors')
    CORS_ORIGINS = [] # No CORS needed for testing usually, or specific test origins

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:password@db:5432/cdp_db') # 'db' is the service name in docker-compose
    LOG_LEVEL = 'INFO'
    # In production, CORS origins should be strictly defined via environment variables
    # Example: "https://your-frontend-domain.com,https://another-domain.com"
    _cors_origins_env = os.environ.get('CORS_ORIGINS')
    CORS_ORIGINS = [origin.strip() for origin in _cors_origins_env.split(',') if origin.strip()] if _cors_origins_env else []