import re
import uuid
from flask import jsonify

def validate_required_fields(data: dict, required_fields: list) -> tuple[bool, str]:
    """
    Validates if all required fields are present and not None/empty in the given data dictionary.

    Args:
        data (dict): The dictionary to validate (e.g., request JSON payload).
        required_fields (list): A list of field names that must be present and non-empty.

    Returns:
        tuple[bool, str]: A tuple where the first element is True if all fields
                          are present and valid, False otherwise. The second element is
                          an error message if validation fails, an empty string otherwise.
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
            missing_fields.append(field)

    if missing_fields:
        return False, f"Missing or empty required fields: {', '.join(missing_fields)}"
    return True, ""

def normalize_identifier(identifier_type: str, value: str) -> str:
    """
    Normalizes common identifiers (mobile, PAN, Aadhaar, UCID) for consistent storage
    and deduplication purposes.

    Args:
        identifier_type (str): The type of identifier (e.g., 'mobile', 'pan', 'aadhaar', 'ucid').
        value (str): The raw identifier value to normalize.

    Returns:
        str: The normalized identifier value. Returns an empty string if the input
             value is not a string or cannot be normalized.
    """
    if not isinstance(value, str):
        return ""

    value = value.strip()

    if identifier_type.lower() == 'mobile':
        # Remove all non-digit characters
        return re.sub(r'\D', '', value)
    elif identifier_type.lower() == 'pan':
        # Convert to uppercase and remove any whitespace
        return value.upper().replace(" ", "")
    elif identifier_type.lower() == 'aadhaar':
        # Remove all non-digit characters
        return re.sub(r'\D', '', value)
    elif identifier_type.lower() == 'ucid':
        # Convert to uppercase and remove any whitespace
        return value.upper().replace(" ", "")
    else:
        # For other types, just strip whitespace
        return value

def is_valid_uuid(val: str) -> bool:
    """
    Checks if a given string is a valid UUID.

    Args:
        val (str): The string to check.

    Returns:
        bool: True if the string is a valid UUID, False otherwise.
    """
    try:
        uuid.UUID(val)
        return True
    except ValueError:
        return False

def generate_success_response(message: str, data: dict = None, status_code: int = 200):
    """
    Generates a standardized JSON success response for API endpoints.

    Args:
        message (str): A descriptive success message.
        data (dict, optional): Optional dictionary containing response data. Defaults to None.
        status_code (int, optional): The HTTP status code. Defaults to 200 (OK).

    Returns:
        tuple: A Flask jsonify response object and the HTTP status code.
    """
    response = {"status": "success", "message": message}
    if data is not None:
        response["data"] = data
    return jsonify(response), status_code

def generate_error_response(message: str, errors: dict = None, status_code: int = 400):
    """
    Generates a standardized JSON error response for API endpoints.

    Args:
        message (str): A descriptive error message.
        errors (dict, optional): Optional dictionary containing specific error details
                                 (e.g., field-level validation errors). Defaults to None.
        status_code (int, optional): The HTTP status code. Defaults to 400 (Bad Request).

    Returns:
        tuple: A Flask jsonify response object and the HTTP status code.
    """
    response = {"status": "error", "message": message}
    if errors is not None:
        response["errors"] = errors
    return jsonify(response), status_code