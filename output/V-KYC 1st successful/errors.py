from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from typing import Union

from logging_config import setup_logging

logger = setup_logging()

class HTTPException(StarletteHTTPException):
    """
    Custom HTTPException class for consistent error responses.
    Inherits from Starlette's HTTPException.
    """
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)
        logger.error(f"Custom HTTP Exception: Status {status_code}, Detail: {detail}")

class CredentialException(HTTPException):
    """Exception for authentication/authorization failures."""
    def __init__(self, detail: str = "Could not validate credentials."):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class ForbiddenException(HTTPException):
    """Exception for insufficient permissions."""
    def __init__(self, detail: str = "Not enough permissions."):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class NotFoundException(HTTPException):
    """Exception for resources not found."""
    def __init__(self, detail: str = "Resource not found."):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class ConflictException(HTTPException):
    """Exception for resource conflicts (e.g., duplicate entry)."""
    def __init__(self, detail: str = "Resource already exists or conflict detected."):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UnprocessableEntityException(HTTPException):
    """Exception for invalid input that cannot be processed."""
    def __init__(self, detail: str = "Unprocessable entity."):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)

# --- Exception Handlers ---

async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]):
    """
    Handles custom and Starlette HTTPExceptions.
    """
    logger.error(f"HTTP Exception caught: {exc.status_code} - {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic validation errors (RequestValidationError).
    Provides detailed error messages for invalid input.
    """
    error_details = []
    for error in exc.errors():
        loc = ".".join(map(str, error["loc"]))
        error_details.append(f"Field: {loc}, Message: {error['msg']}, Type: {error['type']}")
    
    full_detail = "Validation Error: " + "; ".join(error_details)
    logger.warning(f"Validation Error caught for URL: {request.url} - {full_detail}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": full_detail, "errors": exc.errors()}
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions and returns a generic error response.
    Logs the full traceback for debugging.
    """
    logger.critical(f"Unhandled exception caught for URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."}
    )