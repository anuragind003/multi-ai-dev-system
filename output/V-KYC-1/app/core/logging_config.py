import logging
from logging.handlers import RotatingFileHandler
import sys
from app.core.config import settings

def configure_logging():
    """
    Configures the application's logging system.
    Logs to console and optionally to a rotating file.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(settings.LOG_LEVEL)

    # Clear existing handlers to prevent duplicate logs in case of re-configuration
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(settings.LOG_LEVEL)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (optional)
    if settings.LOG_FILE:
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(settings.LOG_LEVEL)
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    # Set up specific loggers for libraries if needed
    logging.getLogger("uvicorn").setLevel(settings.LOG_LEVEL)
    logging.getLogger("uvicorn.access").setLevel(settings.LOG_LEVEL)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) # Reduce SQLAlchemy verbosity

    logging.info(f"Logging configured with level: {settings.LOG_LEVEL}")
    if settings.LOG_FILE:
        logging.info(f"Logs also being written to: {settings.LOG_FILE}")