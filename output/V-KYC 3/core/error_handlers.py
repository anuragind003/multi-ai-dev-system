import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from core.exceptions import CustomHTTPException
from schemas import ErrorResponse, HTTPValidationError

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles FastAPI's HTTPException and CustomHTTPException.
    Returns a standardized JSON error response.
    """
    error_code = None
    if isinstance(exc, CustomHTTPException):
        error_code = exc.code
        log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(log_level, f"HTTP Exception: {exc.status_code} - {exc.detail} (Code: {error_code}) for path: {request.url.path}")
    else:
        log_level = logging.WARNING if exc.status_code < 500 else logging.ERROR
        logger.log(log_level, f"HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")

    response_content = ErrorResponse(detail=exc.detail, code=error_code).model_dump_json()
    return JSONResponse(
        status_code=exc.status_code,
        content=response_content,
        headers=exc.headers
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles Pydantic's RequestValidationError (input validation errors).
    Returns a standardized JSON error response with validation details.
    """
    logger.warning(f"Validation Error for path: {request.url.path}. Details: {exc.errors()}")
    response_content = HTTPValidationError(detail=exc.errors()).model_dump_json()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_content,
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles any unhandled exceptions.
    Returns a generic 500 Internal Server Error response.
    """
    logger.critical(f"Unhandled exception for path: {request.url.path}", exc_info=True)
    response_content = ErrorResponse(
        detail="An unexpected internal server error occurred.",
        code="INTERNAL_SERVER_ERROR"
    ).model_dump_json()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_content,
    )

logger.info("Global error handlers loaded.")