from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from exceptions import (
    VKYCException, AuthenticationError, AuthorizationError,
    RecordingNotFoundError, NFSConnectionError, NFSFileNotFoundError,
    FileOperationError, InvalidInputError, BulkDownloadError
)
from logger import logger

async def vkyc_exception_handler(request: Request, exc: VKYCException):
    """Handles custom VKYCException and its subclasses."""
    logger.error(f"VKYCException caught: {exc.detail} (Status: {exc.status_code}) for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "code": exc.status_code}
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles FastAPI's HTTPException."""
    logger.error(f"HTTPException caught: {exc.detail} (Status: {exc.status_code}) for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "code": exc.status_code}
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors."""
    error_details = exc.errors()
    logger.warning(f"Validation error for path: {request.url.path}, errors: {error_details}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"message": "Validation Error", "details": error_details, "code": status.HTTP_422_UNPROCESSABLE_ENTITY}
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled exception caught for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": "An unexpected error occurred. Please try again later.", "code": status.HTTP_500_INTERNAL_SERVER_ERROR}
    )

def register_exception_handlers(app):
    """Registers all custom and generic exception handlers with the FastAPI app."""
    app.add_exception_handler(VKYCException, vkyc_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)