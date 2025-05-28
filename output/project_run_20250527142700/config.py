import os

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'a_very_secret_key_for_dev_or_testing_replace_in_prod')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost:5432/cdp_db')

    # Celery configuration for background tasks
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')

    # Data Retention Policies (in months)
    OFFER_HISTORY_RETENTION_MONTHS = 6  # FR18, NFR3
    CDP_DATA_RETENTION_MONTHS = 3       # FR24, NFR4

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # External API configurations (placeholders, if needed later)
    # MOENGAGE_API_KEY = os.environ.get('MOENGAGE_API_KEY')
    # MOENGAGE_BASE_URL = os.environ.get('MOENGAGE_BASE_URL', 'https://api.moengage.com')


class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    # Override DB for dev if needed, otherwise uses default from Config
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://dev_user:dev_password@localhost:5432/cdp_dev_db')


class TestingConfig(Config):
    """Testing specific configuration."""
    TESTING = True
    DEBUG = True  # Often true for testing to see errors
    FLASK_ENV = 'testing'
    # Use an in-memory SQLite for faster tests or a dedicated test DB
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
    # Celery tasks might be run synchronously in testing or mocked
    CELERY_ALWAYS_EAGER = True # Run Celery tasks immediately in testing
    CELERY_BROKER_URL = 'memory://' # No actual broker needed for eager tasks
    CELERY_RESULT_BACKEND = 'memory://'


class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    # Ensure a strong secret key is set in production environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY')
    # Ensure production database URL is set via environment variable
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    # Ensure production Celery broker/backend URLs are set
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND')
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING') # More conservative logging in prod

    @classmethod
    def init_app(cls, app):
        # Any production-specific initialization, e.g., logging setup
        import logging
        from logging.handlers import RotatingFileHandler

        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/cdp_app.log', maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('CDP App startup')

# Dictionary to easily select configuration based on environment variable
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}