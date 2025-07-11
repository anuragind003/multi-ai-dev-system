import logging
from config import get_settings

settings = get_settings()

def setup_logging():
    """
    Configures the application's logging system.
    Logs to console and a file.
    """
    # Create a custom logger
    logger = logging.getLogger("vkyc_app")
    logger.setLevel(settings.LOG_LEVEL)

    # Prevent duplicate loggers if called multiple times
    if not logger.handlers:
        # Create handlers
        c_handler = logging.StreamHandler()
        f_handler = logging.FileHandler(settings.LOG_FILE_PATH)

        # Set levels for handlers
        c_handler.setLevel(settings.LOG_LEVEL)
        f_handler.setLevel(settings.LOG_LEVEL)

        # Create formatters and add it to handlers
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        c_handler.setFormatter(formatter)
        f_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(c_handler)
        logger.addHandler(f_handler)

    return logger

# Initialize logger on module import
logger = setup_logging()