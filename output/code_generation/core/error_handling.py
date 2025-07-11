import logging
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional

logger = logging.getLogger(__name__)

# --- Custom Exception Classes ---
class APIException(HTTPException):
    """
    Base custom exception for API errors.
    Allows for consistent error responses.
    """
    def __init__(self, status_code: int, detail: str, error_code: Optional[str] = None):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code or self.__class__.__name__

class NotFoundException(APIException):
    """Exception for resources not found (HTTP 404)."""
    def __init__(self, detail: str = "Resource not found.", error_code: Optional[str] = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, error_code=error_code)

class UnauthorizedException(APIException):
    """Exception for authentication failures (HTTP 401)."""
    def __init__(self, detail: str = "Authentication required or invalid credentials.", error_code: Optional[str] = "UNAUTHORIZED"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, error_code=error_code)

class ForbiddenException(APIException):
    """Exception for authorization failures (HTTP 403)."""
    def __init__(self, detail: str = "You do not have permission to perform this action.", error_code: Optional[str] = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, error_code=error_code)

class BadRequestException(APIException):
    """Exception for invalid client requests (HTTP 400)."""
    def __init__(self, detail: str = "Bad request.", error_code: Optional[str] = "BAD_REQUEST"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, error_code=error_code)

class FileAccessException(APIException):
    """Exception for issues accessing files (e.g., permissions, invalid path) (HTTP 403/500)."""
    def __init__(self, detail: str = "File access error.", error_code: Optional[str] = "FILE_ACCESS_ERROR", status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail, error_code=error_code)

# --- Error Response Schema ---
class ErrorResponse(BaseModel):
    """Standardized error response schema."""
    detail: str = Field(..., description="A human-readable explanation of the error.")
    error_code: str = Field(..., description="A unique code identifying the type of error.")
    status_code: int = Field(..., description="The HTTP status code of the error.")

# --- Exception Handlers ---
async def http_exception_handler(request, exc: HTTPException):
    """Handles FastAPI's built-in HTTPException."""
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=exc.status_code, # Use status code as error_code for generic HTTP errors
            status_code=exc.status_code
        ).model_dump()
    )

async def api_exception_handler(request, exc: APIException):
    """Handles custom APIException and its subclasses."""
    logger.warning(f"API Exception: {exc.status_code} - {exc.error_code} - {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.detail,
            error_code=exc.error_code,
            status_code=exc.status_code
        ).model_dump()
    )

async def validation_exception_handler(request, exc):
    """Handles Pydantic validation errors (RequestValidationError)."""
    from fastapi.exceptions import RequestValidationError
    if isinstance(exc, RequestValidationError):
        errors = []
        for error in exc.errors():
            loc = ".".join(map(str, error["loc"]))
            errors.append(f"{loc}: {error['msg']}")
        detail = "Validation Error: " + "; ".join(errors)
        logger.warning(f"Validation Exception: {detail} for path {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                detail=detail,
                error_code="VALIDATION_ERROR",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
            ).model_dump()
        )
    # Fallback for other unhandled exceptions
    return await generic_exception_handler(request, exc)


async def generic_exception_handler(request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled Exception: {exc} for path {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            detail="An unexpected internal server error occurred.",
            error_code="INTERNAL_SERVER_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        ).model_dump()
    )

def register_exception_handlers(app: FastAPI):
    """Registers all custom and generic exception handlers with the FastAPI app."""
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Custom exception handlers registered.")