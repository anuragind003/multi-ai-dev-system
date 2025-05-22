class APIError(Exception):
    """Base class for custom API errors."""
    status_code = 500
    message = "An unexpected error occurred."

    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__(self)
        if message is not None:
            self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Converts the error details to a dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class BadRequest(APIError):
    """Custom error for 400 Bad Request."""
    status_code = 400
    message = "Bad Request: The request could not be understood or was missing required parameters."

class NotFound(APIError):
    """Custom error for 404 Not Found."""
    status_code = 404
    message = "Not Found: The requested resource could not be found."

class Conflict(APIError):
    """Custom error for 409 Conflict."""
    status_code = 409
    message = "Conflict: The request could not be completed due to a conflict with the current state of the resource."