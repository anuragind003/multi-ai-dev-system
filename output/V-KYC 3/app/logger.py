import logging
import sys
from app.config import settings

# Define log formatters
CONSOLE_FORMATTER = logging.Formatter(
    "%(levelname)s:     %(name)s - %(message)s (%(filename)s:%(lineno)d)"
)
FILE_FORMATTER = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s (%(filename)s:%(lineno)d)"
)

def setup_logging():
    """
    Configures the application's logging system.
    Sets up console and file handlers with appropriate formatters and levels.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL)

    # Clear existing handlers to prevent duplicate logs in reloads
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(CONSOLE_FORMATTER)
    root_logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
    file_handler.setFormatter(FILE_FORMATTER)
    root_logger.addHandler(file_handler)

    # Suppress verbose loggers from libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING) # Reduce SQLAlchemy verbosity
    logging.getLogger("fastapi_limiter").setLevel(logging.WARNING)

    logger.info(f"Logging configured. Level: {settings.LOG_LEVEL}, Log File: {settings.LOG_FILE_PATH}")

# Initialize logging when the module is imported
setup_logging()

# Get a specific logger for the application
logger = logging.getLogger("app")