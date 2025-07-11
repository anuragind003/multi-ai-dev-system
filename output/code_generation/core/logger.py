import logging
import sys
from logging.handlers import RotatingFileHandler
from core.config import settings

# Define log format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Create a logger instance
logger = logging.getLogger(settings.PROJECT_NAME)
logger.setLevel(logging.INFO) # Set default logging level

# Ensure handlers are not duplicated if the module is reloaded
if not logger.handlers:
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)

    # File Handler (optional, for production environments)
    # Log file will rotate after 10 MB, keeping 5 backup files
    log_file_path = "app.log"
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=10 * 1024 * 1024, # 10 MB
        backupCount=5
    )
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(file_handler)

    # Prevent logs from propagating to the root logger
    logger.propagate = False

# Example usage:
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.")
# try:
#     1 / 0
# except ZeroDivisionError:
#     logger.exception("An exception occurred!")