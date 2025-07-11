from fastapi import HTTPException, status
from typing import Any, Dict, Optional

class CustomHTTPException(HTTPException):
    """Base class for custom HTTP exceptions."""
    def __init__(
        self,
        status_code: int,
        message: str,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.message = message
        if detail is None:
            self.detail = message # Default detail to message if not provided

class UnauthorizedException(CustomHTTPException):
    """Exception for authentication failures (401 Unauthorized)."""
    def __init__(self, detail: Any = "Authentication required or invalid credentials.", message: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, message=message)

class ForbiddenException(CustomHTTPException):
    """Exception for authorization failures (403 Forbidden)."""
    def __init__(self, detail: Any = "You do not have permission to perform this action.", message: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, message=message)

class NotFoundException(CustomHTTPException):
    """Exception for resources not found (404 Not Found)."""
    def __init__(self, detail: Any = "The requested resource was not found.", message: str = "Not Found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, message=message)

class ConflictException(CustomHTTPException):
    """Exception for resource conflicts (409 Conflict), e.g., duplicate entry."""
    def __init__(self, detail: Any = "A conflict occurred with the existing resource.", message: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, message=message)

class InvalidInputException(CustomHTTPException):
    """Exception for invalid input data (400 Bad Request)."""
    def __init__(self, detail: Any = "Invalid input provided.", message: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, message=message)

class ServiceUnavailableException(CustomHTTPException):
    """Exception for external service unavailability (503 Service Unavailable)."""
    def __init__(self, detail: Any = "External service is currently unavailable.", message: str = "Service Unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail, message=message)