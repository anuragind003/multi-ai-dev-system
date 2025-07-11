from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    """Base custom HTTP exception class."""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

class UnauthorizedException(CustomHTTPException):
    """Exception for authentication failures (401 Unauthorized)."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(CustomHTTPException):
    """Exception for authorization failures (403 Forbidden)."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(CustomHTTPException):
    """Exception for resource not found (404 Not Found)."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(CustomHTTPException):
    """Exception for resource conflict (409 Conflict)."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class ServiceUnavailableException(CustomHTTPException):
    """Exception for service unavailable (503 Service Unavailable)."""
    def __init__(self, detail: str = "Service is temporarily unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)