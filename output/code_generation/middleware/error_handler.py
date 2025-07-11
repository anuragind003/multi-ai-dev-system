from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from utils.logger import get_logger
from utils.exceptions import RecordNotFoundException, UnauthorizedException, ForbiddenException, InvalidInputException, NFSConnectionError

logger = get_logger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Custom handler for FastAPI's HTTPException and custom HTTP-related exceptions.
    """
    status_code = exc.status_code
    detail = exc.detail

    # Map custom exceptions to appropriate HTTP status codes
    if isinstance(exc, RecordNotFoundException):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, UnauthorizedException):
        status_code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, ForbiddenException):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(exc, InvalidInputException):
        status_code = status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, NFSConnectionError):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE # Or 500, depending on severity
        detail = f"External service error: {detail}" # Prepend for clarity

    logger.error(f"HTTP Error {status_code} for {request.method} {request.url}: {detail}")
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
    )

async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """
    Custom handler for Pydantic ValidationError.
    """
    logger.error(f"Validation Error for {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation Error"},
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for any unhandled exceptions.
    Ensures no sensitive information is leaked in production.
    """
    logger.critical(f"Unhandled exception for {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later.", "error_type": type(exc).__name__},
    )