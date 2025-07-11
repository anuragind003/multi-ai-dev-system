import logging
from logging.handlers import RotatingFileHandler
from config import settings
import sys

def setup_logging():
    """
    Configures the application's logging system.
    Logs to console and optionally to a rotating file.
    """
    log_level = settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {settings.LOG_LEVEL}")

    # Create a custom logger
    logger = logging.getLogger("security_testing_api")
    logger.setLevel(numeric_level)

    # Prevent duplicate handlers if called multiple times
    if not logger.handlers:
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File Handler (optional)
        if settings.LOG_FILE_PATH:
            try:
                file_handler = RotatingFileHandler(
                    settings.LOG_FILE_PATH,
                    maxBytes=10 * 1024 * 1024,  # 10 MB
                    backupCount=5
                )
                file_handler.setLevel(numeric_level)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.error(f"Failed to set up file logging: {e}")

    # Set default logger for libraries that don't use a specific logger
    logging.basicConfig(level=numeric_level, handlers=[]) # Clear default handlers
    logging.getLogger().addHandler(logger.handlers[0]) # Add console handler to root
    if settings.LOG_FILE_PATH and len(logger.handlers) > 1:
        logging.getLogger().addHandler(logger.handlers[1]) # Add file handler to root

    logger.info(f"Logging configured with level: {settings.LOG_LEVEL}")
    if settings.LOG_FILE_PATH:
        logger.info(f"Logs also being written to: {settings.LOG_FILE_PATH}")