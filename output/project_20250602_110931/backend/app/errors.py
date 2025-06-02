from flask import jsonify, make_response, Flask
from werkzeug.exceptions import HTTPException, InternalServerError
import logging

logger = logging.getLogger(__name__)

def _get_error_description(error) -> str:
    """Extracts a meaningful description from an error object."""
    if hasattr(error, 'description') and error.description:
        return error.description
    return str(error)

def _json_error_response(status_code: int, message: str, details: str = None, errors: dict = None):
    """
    Helper function to create a consistent JSON error response.
    """
    response_payload = {
        "status": "error",
        "code": status_code,
        "message": message
    }
    if details:
        response_payload["details"] = details
    if errors:
        response_payload["errors"] = errors
    return make_response(jsonify(response_payload), status_code)

def register_error_handlers(app: Flask):
    """
    Registers custom error handlers for the Flask application.

    This function sets up handlers for various HTTP status codes and
    general exceptions, ensuring that API errors return consistent
    JSON responses.
    """

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handles 400 Bad Request errors."""
        description = _get_error_description(error)
        logger.warning(f"400 Bad Request: {description}")
        return _json_error_response(
            400,
            "Bad Request: The request could not be understood or was missing required parameters.",
            details=description if app.debug else None
        )

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handles 401 Unauthorized errors."""
        description = _get_error_description(error)
        logger.warning(f"401 Unauthorized: {description}")
        return _json_error_response(
            401,
            "Unauthorized: Authentication is required or has failed.",
            details=description if app.debug else None
        )

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handles 403 Forbidden errors."""
        description = _get_error_description(error)
        logger.warning(f"403 Forbidden: {description}")
        return _json_error_response(
            403,
            "Forbidden: You do not have permission to access this resource.",
            details=description if app.debug else None
        )

    @app.errorhandler(404)
    def not_found_error(error):
        """Handles 404 Not Found errors."""
        description = _get_error_description(error)
        logger.warning(f"404 Not Found: {description}")
        return _json_error_response(
            404,
            "Not Found: The requested URL was not found on the server.",
            details=description if app.debug else None
        )

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """Handles 405 Method Not Allowed errors."""
        description = _get_error_description(error)
        logger.warning(f"405 Method Not Allowed: {description}")
        return _json_error_response(
            405,
            "Method Not Allowed: The HTTP method used is not supported for this resource.",
            details=description if app.debug else None
        )

    @app.errorhandler(409)
    def conflict_error(error):
        """Handles 409 Conflict errors."""
        description = _get_error_description(error)
        logger.warning(f"409 Conflict: {description}")
        return _json_error_response(
            409,
            "Conflict: The request could not be completed due to a conflict with the current state of the resource.",
            details=description if app.debug else None
        )

    @app.errorhandler(422)
    def unprocessable_entity_error(error):
        """
        Handles 422 Unprocessable Entity errors, often for validation failures.
        """
        description = _get_error_description(error)
        logger.warning(f"422 Unprocessable Entity: {description}")

        message = "Unprocessable Entity: The request was well-formed but could not be processed due to semantic errors."
        error_details = None

        # Attempt to extract specific validation errors if available (e.g., from Flask-RESTful, Marshmallow)
        if hasattr(error, 'data') and error.data:
            validation_messages = error.data.get('messages')
            if validation_messages:
                # If 'json' key exists, it's likely a common pattern for request body validation
                if 'json' in validation_messages:
                    error_details = validation_messages['json']
                    message = "Validation failed for request data."
                else:
                    error_details = validation_messages
                    message = "Validation failed."
            elif isinstance(error.data, dict): # Fallback for other dict-like error data
                error_details = error.data
                message = "Validation failed."

        return _json_error_response(
            422,
            message,
            details=description if app.debug else None,
            errors=error_details
        )

    @app.errorhandler(InternalServerError)
    @app.errorhandler(500)
    def internal_server_error(error):
        """Handles 500 Internal Server Error."""
        logger.exception(f"500 Internal Server Error: {_get_error_description(error)}")
        
        message = "Internal Server Error: An unexpected error occurred on the server."
        details = None
        if app.debug:
            details = _get_error_description(error)
        
        return _json_error_response(500, message, details=details)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """
        Handles all other Werkzeug HTTP exceptions not explicitly caught above.
        This ensures all HTTP errors return a JSON response.
        """
        description = _get_error_description(e)
        logger.warning(f"HTTP Exception {e.code}: {description}")
        
        message = e.description if e.description else f"HTTP Error {e.code}"
        details = None
        if app.debug:
            details = description
            
        return _json_error_response(e.code, message, details=details)

    @app.errorhandler(Exception)
    def handle_general_exception(e):
        """
        Catches any unhandled Python exceptions and returns a 500 Internal Server Error.
        This is the ultimate fallback for any uncaught errors.
        """
        logger.exception(f"Unhandled Exception: {_get_error_description(e)}")
        
        message = "Internal Server Error: An unexpected error occurred."
        details = None
        if app.debug:
            details = _get_error_description(e)
            
        return _json_error_response(500, message, details=details)