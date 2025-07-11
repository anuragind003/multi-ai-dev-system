from fastapi import HTTPException, status

class CustomHTTPException(HTTPException):
    """Base custom HTTP exception class."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class UnauthorizedException(CustomHTTPException):
    """Exception for authentication failures."""
    def __init__(self, detail: str = "Could not validate credentials", headers: dict = None):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)

class ForbiddenException(CustomHTTPException):
    """Exception for authorization failures (insufficient permissions)."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(CustomHTTPException):
    """Generic exception for resource not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class UserAlreadyExistsException(CustomHTTPException):
    """Exception for when a user with the given credentials already exists."""
    def __init__(self, detail: str = "User already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class KYCRecordNotFoundException(NotFoundException):
    """Specific exception for when a KYC record is not found."""
    def __init__(self, detail: str = "KYC record not found"):
        super().__init__(detail=detail)

class DuplicateEntryException(CustomHTTPException):
    """Exception for when an attempt is made to create a duplicate entry."""
    def __init__(self, detail: str = "Duplicate entry"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class ServiceUnavailableException(CustomHTTPException):
    """Exception for when an external service is unavailable."""
    def __init__(self, detail: str = "Service currently unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

class InternalServerError(CustomHTTPException):
    """Generic exception for internal server errors."""
    def __init__(self, detail: str = "An internal server error occurred"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)