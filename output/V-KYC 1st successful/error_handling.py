import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger("vkyc_api")

class APIException(Exception):
    """Base class for custom API exceptions."""
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        self.status_code = status_code
        self.detail = detail
        self.headers = headers

class NotFoundException(APIException):
    """Exception for resources not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)

class UnauthorizedException(APIException):
    """Exception for authentication failures."""
    def __init__(self, detail: str = "Could not validate credentials", headers: dict = None):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers)

class ForbiddenException(APIException):
    """Exception for authorization failures."""
    def __init__(self, detail: str = "Not enough permissions"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)

class BadRequestException(APIException):
    """Exception for bad requests (e.g., invalid input)."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)

class ConflictException(APIException):
    """Exception for resource conflicts (e.g., duplicate entry)."""
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status.HTTP_409_CONFLICT, detail)

class ServiceUnavailableException(APIException):
    """Exception for external service unavailability."""
    def __init__(self, detail: str = "Service temporarily unavailable"):
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, detail)

async def api_exception_handler(request: Request, exc: APIException):
    """Handles custom APIException instances."""
    logger.error(f"API Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles FastAPI's RequestValidationError (Pydantic validation errors)."""
    error_details = exc.errors()
    logger.warning(f"Validation Error: {error_details} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": error_details},
    )

async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
    """Handles Pydantic ValidationError that might occur outside of request validation."""
    error_details = exc.errors()
    logger.warning(f"Pydantic Validation Error: {error_details} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Data Model Validation Error", "errors": error_details},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled Exception: {exc} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred."},
    )