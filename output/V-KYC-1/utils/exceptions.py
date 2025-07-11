from fastapi import HTTPException, status

class BaseAppException(HTTPException):
    """Base class for custom application exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.name = self.__class__.__name__

class NotFoundException(BaseAppException):
    """Exception raised when a requested resource is not found."""
    def __init__(self, detail: str = "Resource not found."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(BaseAppException):
    """Exception raised when a resource already exists or a conflict occurs."""
    def __init__(self, detail: str = "Resource already exists or a conflict occurred."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnauthorizedException(BaseAppException):
    """Exception raised for authentication failures."""
    def __init__(self, detail: str = "Authentication required.", headers: dict = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)

class ForbiddenException(BaseAppException):
    """Exception raised for authorization failures (insufficient permissions)."""
    def __init__(self, detail: str = "Not enough permissions."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ValidationException(BaseAppException):
    """Exception raised for invalid input data."""
    def __init__(self, detail: str = "Invalid input data."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

class DatabaseException(BaseAppException):
    """Exception raised for database-related errors."""
    def __init__(self, detail: str = "A database error occurred."):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class ServiceUnavailableException(BaseAppException):
    """Exception raised when a service is temporarily unavailable."""
    def __init__(self, detail: str = "Service is temporarily unavailable."):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)