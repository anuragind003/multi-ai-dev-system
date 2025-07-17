import logging
import sys
from logging.handlers import RotatingFileHandler
from config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance.
    Logs to console and a rotating file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False # Prevent logs from being passed to the root logger

    # Check if handlers already exist to prevent duplicate logs
    if not logger.handlers:
        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File Handler (Rotating)
        file_handler = RotatingFileHandler(
            settings.LOG_FILE_PATH,
            maxBytes=10 * 1024 * 1024, # 10 MB
            backupCount=5 # Keep 5 backup files
        )
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger

# Initialize the root logger for general application messages
# This ensures that even before specific modules call get_logger,
# basic logging is set up.
get_logger("uvicorn") # Configure uvicorn's logger
get_logger("fastapi") # Configure fastapi's logger
get_logger("sqlalchemy") # Configure sqlalchemy's logger
get_logger("app") # General app logger