import logging
from fastapi import status

logger = logging.getLogger(__name__)

class CustomException(Exception):
    """Base class for custom exceptions in the application."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        logger.error(f"CustomException: {message} (Status: {status_code})")
        super().__init__(self.message)

class UnauthorizedException(CustomException):
    """Exception for authentication failures (e.g., invalid credentials, missing token)."""
    def __init__(self, message: str = "Authentication required or invalid credentials."):
        super().__init__(message, status_code=status.HTTP_401_UNAUTHORIZED)

class ForbiddenException(CustomException):
    """Exception for authorization failures (e.g., insufficient permissions)."""
    def __init__(self, message: str = "Permission denied."):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)

class NotFoundException(CustomException):
    """Exception for resources not found."""
    def __init__(self, message: str = "Resource not found."):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)

class ConflictException(CustomException):
    """Exception for resource conflicts (e.g., duplicate entry)."""
    def __init__(self, message: str = "Resource conflict."):
        super().__init__(message, status_code=status.HTTP_409_CONFLICT)

class BadRequestException(CustomException):
    """Exception for invalid client requests."""
    def __init__(self, message: str = "Bad request."):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)