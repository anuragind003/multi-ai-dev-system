import json
import re
import html
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def get_current_utc_timestamp() -> str:
    """
    Returns the current UTC timestamp in ISO 8601 format (e.g., '2023-10-27T10:00:00.000000Z').
    This format is suitable for consistent storage and comparison across different timezones.
    The 'Z' suffix explicitly denotes UTC (Zulu time).
    """
    # datetime.isoformat() with timespec='microseconds' and timezone.utc will produce
    # 'YYYY-MM-DDTHH:MM:SS.ffffff+00:00'. Replacing '+00:00' with 'Z' is a common
    # convention for ISO 8601 UTC timestamps.
    return datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')

def load_config(config_path: str = 'config.json') -> Dict[str, Any]:
    """
    Loads configuration from a JSON file.

    Args:
        config_path (str): The path to the configuration file.

    Returns:
        Dict[str, Any]: A dictionary containing the configuration.

    Raises:
        FileNotFoundError: If the configuration file does not exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
        IOError: For other unexpected errors during file reading.
        Exception: For any other unexpected errors.
    """
    try:
        # It's generally better to let open() raise FileNotFoundError directly
        # rather than checking os.path.exists() which can lead to race conditions.
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        # Re-raise FileNotFoundError to maintain the original explicit error type
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    except json.JSONDecodeError as e:
        # Re-raise with more context for easier debugging
        raise json.JSONDecodeError(f"Error decoding JSON from {config_path}: {e}", e.doc, e.pos)
    except IOError as e:
        # Catch any other unexpected I/O errors during file reading (e.g., permissions)
        raise IOError(f"An unexpected I/O error occurred while reading {config_path}: {e}")
    except Exception as e:
        # Catch any other unexpected errors during the process
        raise Exception(f"An unexpected error occurred while loading config from {config_path}: {e}")

# Regex for email validation (more robust than simple string checks)
# This regex is a common compromise for email validation:
# It allows most valid email formats but is not exhaustive for all edge cases
# (e.g., very obscure valid characters, IP address domains).
# For strict RFC compliance, a dedicated library is recommended.
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

def validate_email(email: str) -> bool:
    """
    Performs a basic but more robust validation of an email address format using regex.
    This provides a reasonable balance for typical web application needs.
    For strict RFC compliance, consider using a dedicated email validation library.

    Args:
        email (str): The email string to validate.

    Returns:
        bool: True if the email appears valid, False otherwise.
    """
    if not isinstance(email, str):
        return False
    # Check for empty string after stripping whitespace
    stripped_email = email.strip()
    if not stripped_email:
        return False
    return bool(EMAIL_REGEX.fullmatch(stripped_email))

def is_valid_password(password: str) -> bool:
    """
    Checks if a password meets basic complexity requirements.
    This implementation enforces minimum length, and presence of
    uppercase, lowercase, and digit characters.

    Args:
        password (str): The password string to validate.

    Returns:
        bool: True if the password meets the minimum requirements, False otherwise.
    """
    if not isinstance(password, str):
        return False

    # Minimum length requirement
    MIN_PASSWORD_LENGTH = 8
    if len(password) < MIN_PASSWORD_LENGTH:
        return False

    # Check for at least one uppercase letter
    if not re.search(r"[A-Z]", password):
        return False

    # Check for at least one lowercase letter
    if not re.search(r"[a-z]", password):
        return False

    # Check for at least one digit
    if not re.search(r"\d", password):
        return False

    # Optional: Check for at least one special character (uncomment if needed)
    # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
    #     return False

    return True

def sanitize_input(input_string: Optional[str]) -> Optional[str]:
    """
    Sanitizes user input strings for general use, including stripping whitespace
    and collapsing multiple spaces. It also HTML-escapes the string to prevent
    Cross-Site Scripting (XSS) vulnerabilities when displayed in a web context.

    Args:
        input_string (Optional[str]): The string to sanitize.

    Returns:
        Optional[str]: The sanitized and HTML-escaped string, or None if input was None.
    """
    if input_string is None:
        return None

    # Remove leading/trailing whitespace
    sanitized = input_string.strip()

    # Replace multiple spaces with a single space (optional, depends on context)
    # This handles cases like "  hello   world  " -> "hello world"
    sanitized = ' '.join(sanitized.split())

    # HTML escape the string to prevent XSS when rendered in a browser.
    # This converts characters like '<' to '&lt;', '>' to '&gt;', etc.
    sanitized = html.escape(sanitized)

    return sanitized

def generate_unique_id() -> str:
    """
    Generates a universally unique identifier (UUID) using the uuid4 standard.
    UUIDs are highly recommended for generating unique IDs in distributed systems
    or where collision probability must be extremely low.

    Returns:
        str: A 32-character hexadecimal string representation of a UUID (without hyphens).
             Example: 'a1b2c3d4e5f678901234567890abcdef'
    """
    # uuid.uuid4() generates a random UUID.
    # .hex provides the UUID as a 32-character hexadecimal string without hyphens.
    # For a more standard UUID string with hyphens, use str(uuid.uuid4()).
    return uuid.uuid4().hex