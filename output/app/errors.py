from flask import jsonify

class APIError(Exception):
    """Base class for custom API errors."""
    status_code = 500
    message = "An unexpected error occurred."

    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__(message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Converts the error to a dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class NotFoundError(APIError):
    """Error for resource not found (HTTP 404)."""
    status_code = 404
    message = "Resource not found."

class BadRequestError(APIError):
    """Error for bad request (HTTP 400), typically due to invalid input."""
    status_code = 400
    message = "Bad request."

class ConflictError(APIError):
    """Error for conflict (HTTP 409), e.g., resource already exists."""
    status_code = 409
    message = "Conflict."

def register_error_handlers(app):
    """Registers custom error handlers with the Flask application."""

    @app.errorhandler(APIError)
    def handle_api_error(error):
        """Handles custom APIError exceptions."""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(e):
        """Handles Flask's default 404 Not Found errors."""
        return jsonify({"message": "The requested URL was not found on the server."}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        """Handles Flask's default 405 Method Not Allowed errors."""
        return jsonify({"message": "The method is not allowed for the requested URL."}), 405

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        """Handles Flask's default 500 Internal Server Error."""
        return jsonify({"message": "An internal server error occurred."}), 500