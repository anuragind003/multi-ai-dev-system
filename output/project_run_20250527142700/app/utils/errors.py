class APIError(Exception):
    """
    Base class for custom API exceptions.
    Allows for a custom message and HTTP status code.
    """
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

    def to_dict(self):
        """
        Converts the error to a dictionary suitable for JSON response.
        """
        return {'status': 'error', 'message': self.message}

class ResourceNotFound(APIError):
    """
    Exception for when a requested resource is not found (HTTP 404).
    """
    def __init__(self, message="Resource not found"):
        super().__init__(message, status_code=404)

class BadRequestError(APIError):
    """
    Exception for bad requests, typically due to invalid input (HTTP 400).
    """
    def __init__(self, message="Bad request"):
        super().__init__(message, status_code=400)

class UnauthorizedError(APIError):
    """
    Exception for unauthorized access (HTTP 401).
    """
    def __init__(self, message="Unauthorized access"):
        super().__init__(message, status_code=401)

class ForbiddenError(APIError):
    """
    Exception for forbidden access (HTTP 403).
    """
    def __init__(self, message="Forbidden"):
        super().__init__(message, status_code=403)

class InternalServerError(APIError):
    """
    Exception for internal server errors (HTTP 500).
    """
    def __init__(self, message="An internal server error occurred"):
        super().__init__(message, status_code=500)

class DatabaseError(APIError):
    """
    Exception for database-related errors (e.g., SQLAlchemyError, IntegrityError).
    """
    def __init__(self, message="A database error occurred", original_exception=None):
        super().__init__(message, status_code=500)
        self.original_exception = original_exception

class ValidationError(APIError):
    """
    Exception for data validation failures, often used for specific field errors (HTTP 422 Unprocessable Entity or 400 Bad Request).
    """
    def __init__(self, message="Validation failed", errors=None, status_code=400):
        super().__init__(message, status_code=status_code)
        self.errors = errors if errors is not None else {}

    def to_dict(self):
        """
        Converts the validation error to a dictionary, including specific field errors.
        """
        response = super().to_dict()
        if self.errors:
            response['errors'] = self.errors
        return response

class FileProcessingError(APIError):
    """
    Exception for errors encountered during file processing (e.g., upload, parsing).
    """
    def __init__(self, message="File processing failed", status_code=400):
        super().__init__(message, status_code=status_code)

class DataIntegrityError(APIError):
    """
    Exception for data integrity violations, e.g., unique constraint failures.
    """
    def __init__(self, message="Data integrity violation", status_code=409):
        super().__init__(message, status_code=status_code)