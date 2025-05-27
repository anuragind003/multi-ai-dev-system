import uuid
import datetime
import base64
import io
import csv
from flask import jsonify


def generate_uuid():
    """
    Generates a unique UUID (Universally Unique Identifier).

    Returns:
        str: A hexadecimal string representation of a UUID.
    """
    return uuid.uuid4().hex


def get_current_timestamp():
    """
    Returns the current UTC datetime.

    Returns:
        datetime.datetime: The current UTC datetime object.
    """
    return datetime.datetime.utcnow()


def validate_json_payload(data, required_fields):
    """
    Validates if a JSON payload contains all specified required fields.

    Args:
        data (dict): The JSON payload (dictionary) to validate.
        required_fields (list): A list of strings, where each string is a
                                required field name.

    Returns:
        tuple: A tuple containing:
               - bool: True if all required fields are present and not empty,
                       False otherwise.
               - str or None: An error message if validation fails, None otherwise.
    """
    if not isinstance(data, dict):
        return False, "Invalid payload format: expected a JSON object."

    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: '{field}'."
        # Check if the field value is empty for string types
        if isinstance(data[field], str) and not data[field].strip():
            return False, f"Required field '{field}' cannot be empty."
        # Check for None values
        if data[field] is None:
            return False, f"Required field '{field}' cannot be null."
    return True, None


def parse_csv_from_base64(base64_string):
    """
    Decodes a base64 encoded CSV string and parses it into a list of
    dictionaries. Each dictionary represents a row, with keys derived
    from the CSV header.

    Args:
        base64_string (str): The base64 encoded CSV content.

    Returns:
        tuple: A tuple containing:
               - list: A list of dictionaries, where each dictionary is a row.
                       Returns an empty list if parsing fails or no data.
               - str or None: An error message if parsing fails, None otherwise.
    """
    try:
        decoded_bytes = base64.b64decode(base64_string)
        decoded_string = decoded_bytes.decode('utf-8')
        csv_file = io.StringIO(decoded_string)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        return rows, None
    except Exception as e:
        return [], f"Failed to parse CSV from base64: {str(e)}"


def format_api_response(success, message, data=None, status_code=200):
    """
    Formats a consistent API response.

    Args:
        success (bool): True for a successful response, False for an error.
        message (str): A descriptive message for the response.
        data (dict, optional): Optional data payload to include in the response.
                               Defaults to None.
        status_code (int, optional): The HTTP status code for the response.
                                     Defaults to 200.

    Returns:
        flask.Response: A Flask JSON response object.
    """
    response_payload = {
        "status": "success" if success else "error",
        "message": message
    }
    if data is not None:
        response_payload["data"] = data
    return jsonify(response_payload), status_code