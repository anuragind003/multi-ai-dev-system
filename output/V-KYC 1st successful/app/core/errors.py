import logging
from typing import Any, Dict, Optional, Union

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.logging_config import logger

# --- Custom Exceptions ---

class CustomHTTPException(HTTPException):
    """
    Base custom HTTP exception class.
    Allows for more structured error responses.
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code or f"HTTP_{status_code}"

class NotFoundException(CustomHTTPException):
    """Exception for resources not found."""
    def __init__(self, detail: str = "Resource not found", error_code: str = "NOT_FOUND"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, error_code)

class UnauthorizedException(CustomHTTPException):
    """Exception for authentication failures."""
    def __init__(self, detail: str = "Could not validate credentials", error_code: str = "UNAUTHORIZED"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, error_code, {"WWW-Authenticate": "Bearer"})

class ForbiddenException(CustomHTTPException):
    """Exception for authorization failures."""
    def __init__(self, detail: str = "Not enough permissions", error_code: str = "FORBIDDEN"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, error_code)

class BadRequestException(CustomHTTPException):
    """Exception for bad requests (e.g., invalid input)."""
    def __init__(self, detail: str = "Bad request", error_code: str = "BAD_REQUEST"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, error_code)

class ConflictException(CustomHTTPException):
    """Exception for resource conflicts (e.g., duplicate entry)."""
    def __init__(self, detail: str = "Conflict", error_code: str = "CONFLICT"):
        super().__init__(status.HTTP_409_CONFLICT, detail, error_code)

class ServiceUnavailableException(CustomHTTPException):
    """Exception for external service unavailability."""
    def __init__(self, detail: str = "Service temporarily unavailable", error_code: str = "SERVICE_UNAVAILABLE"):
        super().__init__(status.HTTP_503_SERVICE_UNAVAILABLE, detail, error_code)

# --- Global Exception Handlers ---

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's built-in HTTPException."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    """Handles custom HTTP exceptions."""
    logger.warning(f"Custom HTTP Exception: {exc.status_code} - {exc.error_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error_code": exc.error_code, "detail": exc.detail},
        headers=exc.headers,
    )

async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handles Pydantic validation errors."""
    logger.error(f"Validation Error: {exc.errors()} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": exc.errors()},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled Exception: {type(exc).__name__} - {exc} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )

def register_error_handlers(app):
    """Registers all custom and generic error handlers with the FastAPI app."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(CustomHTTPException, custom_http_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Global error handlers registered.")