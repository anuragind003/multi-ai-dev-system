import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configures the application's logging system.
    Logs to console and a rotating file.
    """
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "app.log")

    # Create logger
    logger = logging.getLogger("vkyc_api")
    logger.setLevel(logging.INFO)

    # Create formatters
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)

    # Create file handler (rotating)
    # Max 5 MB per file, keep 5 backup files
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    if not logger.handlers: # Prevent adding handlers multiple times
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    # Set default logging for SQLAlchemy to WARNING to reduce verbosity
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

    logger.info("Logging configured successfully.")

def get_logger(name: str = "vkyc_api") -> logging.Logger:
    """
    Returns a pre-configured logger instance.
    """
    return logging.getLogger(name)

# Call setup_logging once when this module is imported
setup_logging()