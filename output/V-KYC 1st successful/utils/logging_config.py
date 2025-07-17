import logging
import os
from config import settings

def setup_logging():
    """
    Configures the application's logging.
    Logs to console and optionally to a file.
    """
    log_level = settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Ensure logs directory exists if file logging is enabled
    if settings.LOG_FILE_PATH:
        log_dir = os.path.dirname(settings.LOG_FILE_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

    # Basic configuration
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler (optional)
    if settings.LOG_FILE_PATH:
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [] # Clear existing handlers to prevent duplicates

    root_logger.addHandler(console_handler)
    if settings.LOG_FILE_PATH:
        root_logger.addHandler(file_handler)

    # Suppress verbose loggers from libraries if not in debug mode
    if not settings.DEBUG_MODE:
        logging.getLogger("uvicorn").setLevel(logging.INFO)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    logging.info(f"Logging configured at level: {log_level}")
    if settings.LOG_FILE_PATH:
        logging.info(f"Logs also being written to: {settings.LOG_FILE_PATH}")