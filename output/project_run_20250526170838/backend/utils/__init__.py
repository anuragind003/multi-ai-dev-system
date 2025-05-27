import uuid
import csv
from io import StringIO
from datetime import datetime

def generate_uuid():
    """Generates a unique UUID string."""
    return str(uuid.uuid4())

def json_response(data=None, status_code=200, message="Success", errors=None):
    """
    Creates a standardized dictionary for JSON responses.

    Args:
        data (dict, optional): The main data payload. Defaults to None.
        status_code (int, optional): HTTP status code. Defaults to 200.
        message (str, optional): A descriptive message. Defaults to "Success".
        errors (list, optional): A list of error messages or objects. Defaults to None.

    Returns:
        dict: A dictionary representing the JSON response structure.
    """
    response = {
        "status": "success" if status_code < 400 else "error",
        "message": message,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    if data is not None:
        response["data"] = data
    if errors is not None:
        response["errors"] = errors
        # If errors are present, explicitly set status to 'error'
        response["status"] = "error"
    return response

def parse_csv_file(file_stream):
    """
    Parses a CSV file stream and returns a list of dictionaries.

    Args:
        file_stream: A file-like object (e.g., from request.files['file']).
                     Expected to be bytes, will be decoded as utf-8.

    Returns:
        list: A list of dictionaries, where each dictionary represents a row.
              Returns an empty list if the file is empty or cannot be parsed.
    """
    content = file_stream.read().decode('utf-8')
    if not content.strip():
        return []

    # Use StringIO to treat the string content as a file
    f = StringIO(content)
    reader = csv.DictReader(f)
    return list(reader)

def generate_csv_file(data, headers=None):
    """
    Generates CSV content from a list of dictionaries.

    Args:
        data (list): A list of dictionaries, where each dictionary is a row.
        headers (list, optional): A list of column headers. If None, headers are
                                  inferred from the keys of the first dictionary.

    Returns:
        str: The CSV content as a string.
    """
    if not data:
        return ""

    if headers is None:
        # Infer headers from the keys of the first dictionary
        headers = list(data[0].keys())

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)

    writer.writeheader()
    for row in data:
        # Filter row to include only keys present in headers
        # This prevents DictWriter from raising ValueError if a key in row is not in fieldnames
        filtered_row = {k: v for k, v in row.items() if k in headers}
        writer.writerow(filtered_row)

    return output.getvalue()

def validate_data_columns(data_row, required_columns):
    """
    Performs basic column-level validation on a data row.

    Args:
        data_row (dict): A dictionary representing a row of data.
        required_columns (list): A list of column names that must be present
                                 and have non-empty values.

    Returns:
        list: A list of error messages. Empty if no errors.
    """
    errors = []
    for col in required_columns:
        if col not in data_row or not str(data_row[col]).strip():
            errors.append(f"Missing or empty required column: '{col}'")
    # Further validation (e.g., data types, regex patterns) can be added here
    return errors