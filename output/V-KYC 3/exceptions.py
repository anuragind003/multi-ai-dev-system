from fastapi import HTTPException, status

class APIException(HTTPException):
    """Base class for custom API exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.name = self.__class__.__name__

class NotFoundException(APIException):
    """Exception raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(APIException):
    """Exception raised when a resource already exists or there's a conflict."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnauthorizedException(APIException):
    """Exception raised for authentication failures."""
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )

class ForbiddenException(APIException):
    """Exception raised for authorization failures."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class BadRequestException(APIException):
    """Exception raised for invalid client requests."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class ServiceUnavailableException(APIException):
    """Exception raised when an external service is unavailable."""
    def __init__(self, detail: str = "External service unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)

class InternalServerError(APIException):
    """Exception raised for unexpected server errors."""
    def __init__(self, detail: str = "An unexpected error occurred"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)