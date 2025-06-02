import logging
from flask import jsonify, make_response, request
from werkzeug.exceptions import HTTPException

# Initialize logger for this module
logger = logging.getLogger(__name__)

def _create_json_error_response(code, name, description, status_code=None):
    """
    Helper function to create a consistent JSON-formatted error response.
    """
    if status_code is None:
        status_code = code
    return make_response(jsonify({
        "code": code,
        "name": name,
        "description": description
    }), status_code)

def register_error_handlers(app):
    """
    Registers custom error handlers for the Flask application.

    This function sets up handlers for common HTTP error codes (e.g., 400, 401, 403, 404, 405, 500)
    to return consistent JSON-formatted error responses. It also includes a generic handler
    for all Werkzeug HTTP exceptions and a catch-all for any uncaught Python exceptions.

    Args:
        app (Flask): The Flask application instance to register handlers with.
    """

    @app.errorhandler(400)
    def bad_request_error(error):
        """
        Handles 400 Bad Request errors.
        Returns a JSON response indicating a client-side syntax error.
        """
        code = getattr(error, 'code', 400)
        name = getattr(error, 'name', 'Bad Request')
        description = "The server cannot process the request due to a client error (e.g., malformed syntax or invalid parameters)."
        logger.warning("%s (%s): %s - Path: %s", name, code, error, request.path)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(401)
    def unauthorized_error(error):
        """
        Handles 401 Unauthorized errors.
        Returns a JSON response indicating that authentication is required or has failed.
        """
        code = getattr(error, 'code', 401)
        name = getattr(error, 'name', 'Unauthorized')
        description = "Authentication is required and has failed or has not yet been provided. Please log in."
        logger.warning("%s (%s): %s - Path: %s", name, code, error, request.path)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(403)
    def forbidden_error(error):
        """
        Handles 403 Forbidden errors.
        Returns a JSON response indicating that the authenticated user does not have permission.
        """
        code = getattr(error, 'code', 403)
        name = getattr(error, 'name', 'Forbidden')
        description = "You do not have permission to access the requested resource."
        logger.warning("%s (%s): %s - Path: %s", name, code, error, request.path)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(404)
    def not_found_error(error):
        """
        Handles 404 Not Found errors.
        Returns a JSON response indicating the requested resource was not found.
        """
        code = getattr(error, 'code', 404)
        name = getattr(error, 'name', 'Not Found')
        description = f"The requested URL '{request.path}' was not found on the server."
        logger.warning("%s (%s): %s - Path: %s", name, code, error, request.path)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(405)
    def method_not_allowed_error(error):
        """
        Handles 405 Method Not Allowed errors.
        Returns a JSON response indicating the HTTP method is not supported for the resource.
        """
        code = getattr(error, 'code', 405)
        name = getattr(error, 'name', 'Method Not Allowed')
        description = f"The method '{request.method}' is not allowed for the requested URL."
        logger.warning("%s (%s): %s - Path: %s, Method: %s", name, code, error, request.path, request.method)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(500)
    def internal_server_error(error):
        """
        Handles 500 Internal Server Error.
        This is a critical error handler that logs the full exception traceback
        for server-side debugging and returns a generic error message to the client.
        """
        code = getattr(error, 'code', 500)
        name = getattr(error, 'name', 'Internal Server Error')
        description = "An unexpected error occurred on the server. Please try again later."
        logger.exception("An internal server error occurred: %s", error)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """
        Handles all Werkzeug HTTP exceptions (e.g., 400, 404, 500 if not caught by specific handlers).
        This acts as a catch-all for Flask's built-in HTTP errors that are not explicitly handled
        by the more specific error codes above. It extracts information directly from the exception.
        """
        code = getattr(e, 'code', 500)
        name = getattr(e, 'name', 'HTTP Error')
        description = getattr(e, 'description', 'An HTTP error occurred.')
        logger.warning("HTTP Exception (Code: %s, Name: %s): %s - Path: %s", code, name, description, request.path)
        return _create_json_error_response(code, name, description, code)

    @app.errorhandler(Exception)
    def handle_uncaught_exception(e):
        """
        Handles any uncaught Python exceptions that occur during request processing.
        This is a final fallback for errors not covered by specific HTTP error handlers
        or Werkzeug HTTP exceptions. It logs the exception and returns a generic 500 error.
        """
        code = 500
        name = "Internal Server Error"
        description = "An unexpected error occurred on the server. Please try again later."
        logger.exception("An unhandled exception occurred: %s", e)
        return _create_json_error_response(code, name, description, code)