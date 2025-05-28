import functools
from flask import request, jsonify, current_app
from sqlalchemy.exc import SQLAlchemyError, IntegrityError


class APIError(Exception):
    """
    Custom exception for API errors, allowing specific messages,
    HTTP status codes, and optional payload for more context.
    """
    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Converts the exception details to a dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv


def api_response_decorator(f):
    """
    A decorator to standardize API responses and handle common exceptions.
    It wraps the decorated function, catches specific exceptions (like APIError,
    SQLAlchemyError, ValueError, KeyError), and returns a consistent JSON
    response format for both success and error cases.
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Execute the original function.
            # It's expected to return either (data, status_code) or just data.
            result = f(*args, **kwargs)

            if isinstance(result, tuple) and len(result) == 2:
                data, status_code = result
            else:
                data = result
                status_code = 200  # Default success status code

            # Standardize success response format
            return jsonify({"status": "success", "data": data}), status_code

        except APIError as e:
            # Handle custom API errors defined in the application
            current_app.logger.error(f"API Error: {e.message} (Status: {e.status_code})")
            return jsonify(e.to_dict()), e.status_code
        except IntegrityError as e:
            # Handle database integrity errors (e.g., unique constraint violations)
            current_app.logger.error(f"Database Integrity Error: {e}")
            db_error_message = "A record with this unique identifier already exists."
            # Attempt to provide more specific messages for common unique constraints
            error_str = str(e).lower()
            if "mobile_number" in error_str:
                db_error_message = "Mobile number already registered."
            elif "pan" in error_str:
                db_error_message = "PAN already registered."
            elif "aadhaar_ref_number" in error_str:
                db_error_message = "Aadhaar reference number already registered."
            elif "ucid" in error_str:
                db_error_message = "UCID already registered."
            elif "previous_loan_app_number" in error_str:
                db_error_message = "Previous loan application number already registered."
            elif "campaign_unique_identifier" in error_str:
                db_error_message = "Campaign unique identifier already exists."

            return jsonify({"status": "error", "message": db_error_message}), 409  # Conflict
        except SQLAlchemyError as e:
            # Handle other general database errors
            current_app.logger.error(f"Database Error: {e}")
            return jsonify({"status": "error", "message": "A database error occurred."}), 500
        except ValueError as e:
            # Handle data validation errors (e.g., invalid input format, type conversion issues)
            current_app.logger.error(f"Value Error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 400
        except KeyError as e:
            # Handle cases where a required key is missing from a dictionary/JSON payload
            current_app.logger.error(f"Key Error: Missing required field: {e}")
            return jsonify({"status": "error", "message": f"Missing required field: {e}"}), 400
        except Exception as e:
            # Catch any other unexpected errors to prevent server crashes and provide a generic message
            current_app.logger.exception(f"An unexpected error occurred: {e}")
            return jsonify({"status": "error", "message": "An unexpected internal server error occurred."}), 500
    return decorated_function


def validate_json_payload(required_fields=None):
    """
    A decorator to validate that the incoming request body is JSON and
    contains all specified required fields.

    Args:
        required_fields (list): A list of strings, where each string is a
                                required field name that must be present
                                in the JSON payload. Defaults to an empty list.
    """
    if required_fields is None:
        required_fields = []

    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                raise APIError("Request must be JSON", status_code=400)

            data = request.get_json()
            if not data:
                raise APIError("Request body cannot be empty", status_code=400)

            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise APIError(
                    f"Missing required fields: {', '.join(missing_fields)}",
                    status_code=400
                )

            # Pass the validated JSON data as a keyword argument to the decorated function
            kwargs['json_data'] = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator