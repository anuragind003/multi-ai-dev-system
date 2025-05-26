from flask import jsonify
from werkzeug.exceptions import HTTPException

class APIError(HTTPException):
    """
    Custom exception class for API errors.
    Inherits from HTTPException to allow Flask's error handling mechanism
    to automatically catch and process it, returning a JSON response.
    """
    def __init__(self, message, status_code):
        # HTTPException constructor takes description and optionally response
        super().__init__(description=message)
        self.code = status_code  # Set the HTTP status code for this exception

    def get_body(self, environ=None):
        """
        Overrides get_body to return the JSON error message.
        """
        return jsonify({"message": self.description}).get_data(as_text=True)

    def get_headers(self, environ=None):
        """
        Overrides get_headers to ensure Content-Type is application/json.
        """
        return [('Content-Type', 'application/json')]

def register_error_handlers(app):
    """
    Registers custom error handlers with the Flask application.
    """

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """
        Handler for custom APIError exceptions.
        Since APIError inherits from HTTPException, Flask will automatically
        call its get_response method. We can simply return the error object.
        """
        return error

    @app.errorhandler(404)
    def handle_not_found_error(error):
        """
        Handler for 404 Not Found errors.
        Returns a JSON response for consistency.
        """
        response = jsonify({"message": "Resource not found"})
        response.status_code = 404
        return response

    @app.errorhandler(400)
    def handle_bad_request_error(error):
        """
        Handler for 400 Bad Request errors.
        This can catch errors from Flask's request parsing (e.g., malformed JSON,
        missing required fields if handled by Flask's default parsers).
        Returns a JSON response.
        """
        # Werkzeug's BadRequest (which is a 400 HTTPException) has a description.
        # Use it if available, otherwise a generic message.
        message = getattr(error, 'description', 'Bad request')
        response = jsonify({"message": message})
        response.status_code = 400
        return response

    @app.errorhandler(500)
    def handle_internal_server_error(error):
        """
        Handler for 500 Internal Server Error.
        Catches unhandled exceptions that result in a 500.
        Returns a JSON response.
        """
        response = jsonify({"message": "An unexpected error occurred."})
        response.status_code = 500
        return response

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        """
        Catch-all handler for any other unhandled exceptions.
        This ensures all errors return a consistent JSON format, even for
        unexpected server errors.
        """
        # Log the exception for debugging purposes
        app.logger.error(f"Unhandled exception: {e}", exc_info=True)
        response = jsonify({"message": "An unexpected error occurred."})
        response.status_code = 500
        return response