import logging
import sys
from config import settings

def setup_logging():
    """
    Configures the application's logging.
    """
    log_level = logging.INFO
    if settings.DEBUG_MODE:
        log_level = logging.DEBUG

    # Create a custom logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Clear existing handlers to prevent duplicate logs in reloaded environments
    if logger.handlers:
        for handler in logger.handlers:
            logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File Handler (optional, for production)
    if not settings.DEBUG_MODE: # Only write to file in non-debug mode
        try:
            # Ensure logs directory exists
            import os
            log_dir = "logs"
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

            file_handler = logging.FileHandler(f"{log_dir}/app.log")
            file_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.error(f"Failed to set up file logging: {e}")

    # Suppress verbose logs from libraries if not in debug mode
    if not settings.DEBUG_MODE:
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("passlib").setLevel(logging.WARNING)
        logging.getLogger("jose").setLevel(logging.WARNING)

    logger.info(f"Logging configured with level: {logging.getLevelName(log_level)}")