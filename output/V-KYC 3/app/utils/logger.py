import logging
import sys
from app.config import settings

# Configure the root logger
logger = logging.getLogger(__name__)
logger.setLevel(settings.LOG_LEVEL)

# Create a console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(settings.LOG_LEVEL)

# Create a formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Add formatter to console handler
console_handler.setFormatter(formatter)

# Add console handler to the logger
if not logger.handlers: # Prevent adding multiple handlers if imported multiple times
    logger.addHandler(console_handler)

# Example usage:
# from app.utils.logger import logger
# logger.info("This is an info message.")
# logger.error("This is an error message.", exc_info=True)