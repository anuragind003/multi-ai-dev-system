import logging
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

logger = logging.getLogger(__name__)

class CustomException(HTTPException):
    """Base class for custom HTTP exceptions."""
    def __init__(self, status_code: int, detail: Any = None, headers: Optional[Dict[str, str]] = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        logger.error(f"CustomException: Status={status_code}, Detail={detail}")

class NotFoundException(CustomException):
    """Raised when a resource is not found."""
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class UnauthorizedException(CustomException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail,
                         headers={"WWW-Authenticate": "Bearer"})

class ForbiddenException(CustomException):
    """Raised when a user does not have permission to perform an action."""
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class ConflictException(CustomException):
    """Raised when a request conflicts with the current state of the server."""
    def __init__(self, detail: str = "Resource conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class BadRequestException(CustomException):
    """Raised when the request is malformed or invalid."""
    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

# --- Global Exception Handlers ---

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's HTTPException."""
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors from request bodies/queries."""
    errors = []
    for error in exc.errors():
        loc = ".".join(map(str, error["loc"]))
        errors.append({"field": loc, "message": error["msg"], "type": error["type"]})
    logger.error(f"RequestValidationException for URL: {request.url}, Errors: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": errors},
    )

async def custom_exception_handler(request: Request, exc: CustomException):
    """Handles custom exceptions defined in this module."""
    logger.error(f"CustomException: {exc.status_code} - {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles any unhandled exceptions."""
    logger.exception(f"Unhandled exception for URL: {request.url}") # Logs traceback
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )