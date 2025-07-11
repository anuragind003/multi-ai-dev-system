from fastapi import HTTPException, status

class APIException(HTTPException):
    """Base class for custom API exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)

class NotFoundException(APIException):
    """Exception for resources not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(APIException):
    """Exception for resource conflicts (e.g., duplicate entry)."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnauthorizedException(APIException):
    """Exception for authentication failures."""
    def __init__(self, detail: str = "Could not validate credentials", headers: dict = None):
        if headers is None:
            headers = {"WWW-Authenticate": "Bearer"}
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers=headers)

class ForbiddenException(APIException):
    """Exception for authorization failures."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class BadRequestException(APIException):
    """Exception for invalid client requests."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class ServiceUnavailableException(APIException):
    """Exception for external service unavailability."""
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)