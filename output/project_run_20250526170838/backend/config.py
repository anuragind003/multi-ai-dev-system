import os

class Config:
    """
    Base configuration class for the Flask application.
    Contains common settings applicable across all environments.
    """
    # Flask Secret Key: Used for session management, CSRF protection, etc.
    # It's crucial to set this via an environment variable in production.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev_only_replace_in_prod')

    # Database Configuration (PostgreSQL)
    # Reads from DATABASE_URL environment variable, falls back to a default for local development.
    # In production, ensure DATABASE_URL is properly configured.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Suppresses a warning about tracking object modifications

    # Application-specific configurations derived from BRD/NFRs
    # Data retention periods (in months)
    OFFER_HISTORY_RETENTION_MONTHS = 6  # FR19, NFR8: Maintain offer history for 6 months
    CDP_DATA_RETENTION_MONTHS = 3       # FR28, NFR9: Retain all data in CDP for 3 months before deletion

    # File Paths for Admin Portal operations (uploads, downloads, exports)
    # BASE_DIR points to the 'backend' directory where this config file resides.
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))

    # Admin Portal File Uploads (FR35)
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    ALLOWED_EXTENSIONS = {'csv', 'xlsx'}  # Allowed file extensions for uploads

    # Moengage Campaign Export (FR31, FR44)
    MOENGAGE_EXPORT_FOLDER = os.path.join(BASE_DIR, 'exports', 'moengage')
    MOENGAGE_EXPORT_FILENAME = 'moengage_campaign_data.csv'

    # Data Download Folders (FR32, FR33, FR34)
    DUPLICATE_DATA_FOLDER = os.path.join(BASE_DIR, 'downloads', 'duplicates')
    UNIQUE_DATA_FOLDER = os.path.join(BASE_DIR, 'downloads', 'unique')
    ERROR_DATA_FOLDER = os.path.join(BASE_DIR, 'downloads', 'errors')

    # Basic Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
    LOG_FILE = os.path.join(BASE_DIR, 'app.log')

    @staticmethod
    def allowed_file(filename):
        """Checks if a file's extension is allowed for upload."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

class DevelopmentConfig(Config):
    """
    Development specific configuration.
    Enables debug mode and potentially overrides other settings for development ease.
    """
    DEBUG = True
    # You might use a different, more accessible DB for development if needed
    # SQLALCHEMY_DATABASE_URI = 'postgresql://dev_user:dev_password@localhost:5432/cdp_dev_db'

class TestingConfig(Config):
    """
    Testing specific configuration.
    Enables testing mode and typically uses an in-memory or dedicated test database.
    """
    TESTING = True
    # Use an in-memory SQLite database for faster, isolated tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    LOG_LEVEL = 'CRITICAL'  # Suppress most logging during tests

class ProductionConfig(Config):
    """
    Production specific configuration.
    Disables debug mode and enforces strict environment variable usage for sensitive data.
    """
    DEBUG = False
    # In a real production environment, you might add checks here to ensure
    # SECRET_KEY and DATABASE_URL are indeed set as environment variables.
    # Example:
    # if not os.environ.get('SECRET_KEY'):
    #     raise ValueError("SECRET_KEY must be set in production environment.")
    # if not os.environ.get('DATABASE_URL'):
    #     raise ValueError("DATABASE_URL must be set in production environment.")

# Dictionary to easily select the configuration class based on an environment name.
# This allows the application factory to load the correct configuration.
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig  # Default to development if FLASK_ENV is not explicitly set
}