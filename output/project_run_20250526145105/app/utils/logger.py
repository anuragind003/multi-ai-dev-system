import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime

# --- Logging Configuration ---
# Directory for log files
LOG_DIR = "logs"
# Full path for the main application log file
LOG_FILE = os.path.join(LOG_DIR, "app.log")
# Default log level, can be overridden by environment variable (e.g., LOG_LEVEL=DEBUG)
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
# Maximum size of a log file before rotation (10 MB)
MAX_BYTES = 10 * 1024 * 1024
# Number of backup log files to keep
BACKUP_COUNT = 5

# Ensure the log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str = "app_logger") -> logging.Logger:
    """
    Configures and returns a logger instance for the application.

    This function sets up both console and file logging with rotation.
    It prevents adding duplicate handlers if the logger has already been configured.

    Args:
        name: The name of the logger. This typically corresponds to the module
              where the logger is used (e.g., __name__). Defaults to "app_logger".

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    # Set the logging level for the logger instance
    logger.setLevel(LOG_LEVEL)

    # Prevent adding multiple handlers if the logger already has them
    # This is crucial to avoid duplicate log messages
    if not logger.handlers:
        # Define the format for log messages
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # --- Console Handler ---
        # Logs messages to the standard output (console)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # --- File Handler with Rotation ---
        # Logs messages to a file, with automatic rotation based on size
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# Example usage (for testing the logger setup)
if __name__ == "__main__":
    # Get a logger for this specific module
    test_logger = get_logger(__name__)

    test_logger.debug("This is a DEBUG message.")
    test_logger.info("This is an INFO message, indicating normal operation.")
    test_logger.warning("This is a WARNING message, something unexpected happened.")
    test_logger.error("This is an ERROR message, a serious problem occurred.")
    test_logger.critical("This is a CRITICAL message, the application might be unable to continue.")

    try:
        result = 1 / 0
    except ZeroDivisionError:
        test_logger.exception("An exception occurred during a division operation.")

    print(f"\nLog files are being written to: {LOG_DIR}")
    print(f"Current log level is: {LOG_LEVEL}")