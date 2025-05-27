import logging
from flask import jsonify
from werkzeug.exceptions import HTTPException

# Configure logging for error handlers
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class APIError(Exception):
    """
    Custom exception class for API-specific errors.
    This allows us to raise errors with specific HTTP status codes and messages
    that can be caught and handled consistently by the Flask application.
    """
    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """
        Converts the error details into a dictionary suitable for JSON response.
        """
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv


def register_error_handlers(app):
    """
    Registers custom error handlers with the Flask application.
    """

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """
        Handles custom APIError exceptions.
        Returns a JSON response with the error message and status code.
        """
        logger.error(f"API Error: {error.status_code} - {error.message}",
                     exc_info=True)
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """
        Handles standard Werkzeug HTTPException (e.g., 404 Not Found,
        405 Method Not Allowed).
        Returns a JSON response with the HTTP error description and status code.
        """
        logger.warning(f"HTTP Exception: {e.code} - {e.name}: {e.description}")
        response = jsonify({
            "status": "error",
            "message": e.description,
            "code": e.code
        })
        response.status_code = e.code
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """
        Handles any unhandled exceptions (generic 500 Internal Server Error).
        Logs the full traceback and returns a generic error message to the client.
        """
        logger.exception("An unhandled exception occurred:")  # Logs the traceback
        response = jsonify({
            "status": "error",
            "message": "An unexpected error occurred. Please try again later.",
            "code": 500
        })
        response.status_code = 500
        return response

    @app.errorhandler(400)
    def handle_bad_request(e):
        """
        Handles 400 Bad Request errors.
        """
        logger.warning(f"Bad Request: {e.description}")
        response = jsonify({
            "status": "error",
            "message": e.description or "Bad Request",
            "code": 400
        })
        response.status_code = 400
        return response

    @app.errorhandler(404)
    def handle_not_found(e):
        """
        Handles 404 Not Found errors.
        """
        logger.warning(f"Not Found: {e.description}")
        response = jsonify({
            "status": "error",
            "message": e.description or "Resource not found",
            "code": 404
        })
        response.status_code = 404
        return response

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        """
        Handles 405 Method Not Allowed errors.
        """
        logger.warning(f"Method Not Allowed: {e.description}")
        response = jsonify({
            "status": "error",
            "message": e.description or "Method not allowed for this resource",
            "code": 405
        })
        response.status_code = 405
        return response

    @app.errorhandler(422)
    def handle_unprocessable_entity(e):
        """
        Handles 422 Unprocessable Entity errors, often used for validation failures.
        """
        logger.warning(f"Unprocessable Entity: {e.description}")
        response = jsonify({
            "status": "error",
            "message": e.description or "Unprocessable Entity",
            "code": 422
        })
        response.status_code = 422
        return response

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        """
        Handles 500 Internal Server Error explicitly.
        This handler catches explicit 500 errors or those converted by Flask.
        """
        logger.exception("Internal Server Error (explicit 500 handler):")
        response = jsonify({
            "status": "error",
            "message": e.description or "Internal Server Error",
            "code": 500
        })
        response.status_code = 500
        return response