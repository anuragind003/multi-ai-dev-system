class APIError(Exception):
    """Base class for custom API exceptions.

    Attributes:
        message (str): A human-readable message describing the error.
        status_code (int): The HTTP status code associated with the error.
        payload (dict): Optional additional data to include in the error response.
    """
    status_code = 500
    default_message = "An unexpected error occurred."

    def __init__(self, message=None, status_code=None, payload=None):
        super().__init__(message)
        if message is not None:
            self.message = message
        else:
            self.message = self.default_message

        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        """Converts the exception to a dictionary for JSON response."""
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class ResourceNotFound(APIError):
    """Exception for when a requested resource is not found (HTTP 404)."""
    status_code = 404
    default_message = "The requested resource was not found."

class BadRequestError(APIError):
    """Exception for bad requests due to invalid input or missing parameters (HTTP 400)."""
    status_code = 400
    default_message = "Bad request. Please check your input."

class ValidationError(BadRequestError):
    """Specific exception for data validation failures (HTTP 400)."""
    default_message = "Validation failed for one or more fields."

class ConflictError(APIError):
    """Exception for resource conflicts, typically due to unique constraint violations (HTTP 409)."""
    status_code = 409
    default_message = "Resource conflict. The data you are trying to create already exists or violates a unique constraint."

class InternalServerError(APIError):
    """Exception for internal server errors (HTTP 500)."""
    status_code = 500
    default_message = "An internal server error occurred."

class FileProcessingError(APIError):
    """Exception for errors encountered during file upload and processing (HTTP 422 or 500)."""
    status_code = 422 # Unprocessable Entity, or 500 if internal
    default_message = "Error processing the uploaded file."

class DatabaseError(InternalServerError):
    """Generic exception for database-related errors (HTTP 500)."""
    default_message = "A database error occurred."