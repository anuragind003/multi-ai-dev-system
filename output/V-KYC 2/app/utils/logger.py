import logging
import os
from app.config import settings

def get_logger(name: str) -> logging.Logger:
    """
    Configures and returns a logger instance.
    Logs to console and optionally to a file.
    """
    logger = logging.getLogger(name)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False # Prevent duplicate logs from root logger

    # Define a common formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console Handler
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File Handler (if LOG_FILE_PATH is set)
    if settings.LOG_FILE_PATH and not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        try:
            # Ensure the directory exists
            log_dir = os.path.dirname(settings.LOG_FILE_PATH)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback to console if file logging setup fails
            logging.error(f"Failed to set up file logging to {settings.LOG_FILE_PATH}: {e}")

    return logger

# Initialize a global logger for general application messages
# This will be used by modules that don't need a specific named logger
global_logger = get_logger("app")