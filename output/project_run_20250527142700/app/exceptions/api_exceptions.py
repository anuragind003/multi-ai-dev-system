class APIError(Exception):
    """
    Base class for custom API exceptions.
    Allows setting a message, status code, and an optional payload for additional details.
    """
    def __init__(self, message: str, status_code: int = 500, payload: dict = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload if payload is not None else {}

    def to_dict(self):
        """
        Converts the exception details into a dictionary suitable for API response.
        """
        rv = {'message': self.message}
        if self.payload:
            rv['details'] = self.payload
        return rv

class BadRequestError(APIError):
    """
    Exception for bad requests (HTTP 400).
    Used for invalid input, missing parameters, etc.
    """
    def __init__(self, message: str = "Bad Request", payload: dict = None):
        super().__init__(message, 400, payload)

class UnauthorizedError(APIError):
    """
    Exception for unauthorized access (HTTP 401).
    Used when authentication is required but failed or not provided.
    """
    def __init__(self, message: str = "Unauthorized", payload: dict = None):
        super().__init__(message, 401, payload)

class ForbiddenError(APIError):
    """
    Exception for forbidden access (HTTP 403).
    Used when the user is authenticated but does not have permission to access the resource.
    """
    def __init__(self, message: str = "Forbidden", payload: dict = None):
        super().__init__(message, 403, payload)

class NotFoundError(APIError):
    """
    Exception for resources not found (HTTP 404).
    """
    def __init__(self, message: str = "Resource Not Found", payload: dict = None):
        super().__init__(message, 404, payload)

class ConflictError(APIError):
    """
    Exception for conflicts (HTTP 409).
    Typically used for unique constraint violations or conflicting state.
    """
    def __init__(self, message: str = "Conflict", payload: dict = None):
        super().__init__(message, 409, payload)

class InternalServerError(APIError):
    """
    Exception for internal server errors (HTTP 500).
    Used for unexpected errors on the server side.
    """
    def __init__(self, message: str = "Internal Server Error", payload: dict = None):
        super().__init__(message, 500, payload)

class ValidationError(BadRequestError):
    """
    Specific exception for validation failures (HTTP 400).
    Carries a dictionary of field-specific errors in its payload.
    """
    def __init__(self, message: str = "Validation failed", errors: dict = None):
        # Validation errors are a type of bad request, so inherit from BadRequestError
        # The 'errors' dictionary will be passed as the payload under the 'errors' key.
        super().__init__(message, payload={'errors': errors} if errors else None)