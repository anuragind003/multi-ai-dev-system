from fastapi import status

class APIException(Exception):
    """
    Base class for custom API exceptions.
    All custom exceptions should inherit from this.
    """
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)

class UnauthorizedException(APIException):
    """
    Exception for authentication failures (e.g., invalid credentials, missing token).
    Corresponds to HTTP 401 Unauthorized.
    """
    def __init__(self, detail: str = "Not authenticated", headers: dict = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
        self.headers = headers

class ForbiddenException(APIException):
    """
    Exception for authorization failures (e.g., insufficient permissions).
    Corresponds to HTTP 403 Forbidden.
    """
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(APIException):
    """
    Exception for resources not found.
    Corresponds to HTTP 404 Not Found.
    """
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(APIException):
    """
    Exception for resource conflicts (e.g., trying to create a resource that already exists).
    Corresponds to HTTP 409 Conflict.
    """
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class ValidationException(APIException):
    """
    Exception for invalid input data that doesn't fit Pydantic's validation.
    Corresponds to HTTP 422 Unprocessable Entity.
    """
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class ServiceUnavailableException(APIException):
    """
    Exception for when an external service is unavailable.
    Corresponds to HTTP 503 Service Unavailable.
    """
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)