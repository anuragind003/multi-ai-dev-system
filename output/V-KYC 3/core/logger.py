import logging
import sys
from config import settings

# Configure basic logging
# For production, consider using a more robust logging solution like Loguru or configuring
# handlers for file logging, rotating logs, and sending to a centralized logging system (ELK Stack).

# Get the root logger
logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

# Create a console handler with a formatter
console_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console_handler.setFormatter(formatter)

# Add the console handler to the logger
if not logger.handlers: # Prevent adding multiple handlers if reloaded
    logger.addHandler(console_handler)

# Optional: Add file handler if LOG_FILE_PATH is set
if settings.LOG_FILE_PATH:
    try:
        file_handler = logging.FileHandler(settings.LOG_FILE_PATH)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {settings.LOG_FILE_PATH}")
    except Exception as e:
        logger.error(f"Could not set up file logging to {settings.LOG_FILE_PATH}: {e}")

# Example usage:
# logger.debug("This is a debug message.")
# logger.info("This is an info message.")
# logger.warning("This is a warning message.")
# logger.error("This is an error message.")
# logger.critical("This is a critical message.")