import logging
import datetime
import re

# Configure a logger for the 'utils' package.
# This logger can be imported and used by any module within the 'utils' package
# or by other parts of the application that need to log utility-related messages.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create a console handler for the logger
handler = logging.StreamHandler()
# Define a formatter for log messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger if it hasn't been added already
# This prevents adding multiple handlers if the module is reloaded or imported multiple times
if not logger.handlers:
    logger.addHandler(handler)

def get_current_utc_timestamp():
    """
    Returns the current UTC timestamp with timezone information.
    Useful for consistent timestamping across the application, especially for database entries.
    """
    return datetime.datetime.now(datetime.timezone.utc)

def is_valid_uuid(uuid_string):
    """
    Checks if a given string is a valid UUID (Universally Unique Identifier).
    This is useful for validating incoming IDs or ensuring data integrity.
    """
    if not isinstance(uuid_string, str):
        return False
    # Regex for standard UUID format (8-4-4-4-12 hexadecimal digits)
    uuid_regex = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    return bool(uuid_regex.match(uuid_string))

# Example of how to use the logger within this file (optional, for demonstration)
# logger.info("backend.src.utils package initialized.")