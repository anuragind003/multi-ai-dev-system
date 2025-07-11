from fastapi import HTTPException, status

class UnauthorizedException(HTTPException):
    """Custom exception for unauthorized access (401)."""
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    """Custom exception for forbidden access (403)."""
    def __init__(self, detail: str = "Not authorized to perform this action"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(HTTPException):
    """Custom exception for resource not found (404)."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(HTTPException):
    """Custom exception for resource conflict (409)."""
    def __init__(self, detail: str = "Resource already exists or conflict occurred"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class BadRequestException(HTTPException):
    """Custom exception for bad request (400)."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class ServiceUnavailableException(HTTPException):
    """Custom exception for external service unavailable (503)."""
    def __init__(self, detail: str = "External service is currently unavailable"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)