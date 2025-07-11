from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Union, Dict, Any
from utils.logger import logger

class APIException(Exception):
    """
    Custom exception for API-specific errors.
    Allows for structured error responses.
    """
    def __init__(self, status_code: int, detail: str, code: str = "API_ERROR"):
        self.status_code = status_code
        self.detail = detail
        self.code = code
        super().__init__(self.detail)

class DatabaseError(APIException):
    """Specific exception for database-related errors."""
    def __init__(self, detail: str, code: str = "DATABASE_ERROR"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, code)

class NFSConnectionError(APIException):
    """Specific exception for NFS connection or operation errors."""
    def __init__(self, detail: str, code: str = "NFS_CONNECTION_ERROR"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, code)

class TestExecutionError(APIException):
    """Specific exception for errors during integration test execution."""
    def __init__(self, detail: str, code: str = "TEST_EXECUTION_ERROR"):
        super().__init__(status.HTTP_500_INTERNAL_SERVER_ERROR, detail, code)


async def http_exception_handler(request: Request, exc: APIException):
    """
    Handles custom APIException instances.
    """
    logger.error(f"API Exception caught: {exc.status_code} - {exc.code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code, "status_code": exc.status_code},
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles FastAPI's RequestValidationError (Pydantic validation errors).
    Provides a more readable error response.
    """
    errors = exc.errors()
    simplified_errors = []
    for error in errors:
        loc = ".".join(map(str, error["loc"]))
        simplified_errors.append(f"Field '{loc}': {error['msg']}")

    detail_message = "Validation Error: " + "; ".join(simplified_errors)
    logger.warning(f"Validation Error: {detail_message} for request to {request.url}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": detail_message,
            "errors": errors, # Optionally include full errors for debugging
            "code": "VALIDATION_ERROR",
            "status_code": status.HTTP_422_UNPROCESSABLE_ENTITY
        },
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled exceptions and returns a generic 500 error.
    """
    logger.exception(f"Unhandled exception caught for request to {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected internal server error occurred.",
            "code": "INTERNAL_SERVER_ERROR",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        },
    )