class APIError(Exception):
    """Base class for custom API exceptions."""
    def __init__(self, message, status_code=500, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv

class ResourceNotFound(APIError):
    """Exception raised when a requested resource is not found."""
    def __init__(self, message="Resource not found", payload=None):
        super().__init__(message, status_code=404, payload=payload)

class BadRequestError(APIError):
    """Exception raised for bad requests (e.g., invalid input)."""
    def __init__(self, message="Bad request", payload=None):
        super().__init__(message, status_code=400, payload=payload)

class ValidationError(BadRequestError):
    """
    Exception raised for validation errors, typically containing a dictionary
    of field-specific errors.
    """
    def __init__(self, message="Validation failed for one or more fields.", errors=None, payload=None):
        super().__init__(message, payload=payload)
        self.errors = errors if errors is not None else {}
        self.status_code = 400 # Explicitly set for validation errors

    def to_dict(self):
        rv = super().to_dict()
        rv['errors'] = self.errors
        return rv

class InternalServerError(APIError):
    """Exception raised for internal server errors."""
    def __init__(self, message="An internal server error occurred", payload=None):
        super().__init__(message, status_code=500, payload=payload)

class DataProcessingError(InternalServerError):
    """Exception raised for errors during data processing (e.g., deduplication, attribution)."""
    def __init__(self, message="Error during data processing", payload=None):
        super().__init__(message, status_code=500, payload=payload)

class FileUploadError(BadRequestError):
    """Exception raised for errors during file uploads."""
    def __init__(self, message="File upload failed", payload=None):
        super().__init__(message, status_code=400, payload=payload)

class DatabaseError(InternalServerError):
    """Exception raised for database-related errors."""
    def __init__(self, message="Database operation failed", payload=None):
        super().__init__(message, status_code=500, payload=payload)