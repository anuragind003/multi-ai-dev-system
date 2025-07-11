from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from schemas import ErrorResponse
from config import logger

# --- Custom Exceptions ---
class CustomHTTPException(HTTPException):
    """Base class for custom HTTP exceptions."""
    def __init__(self, status_code: int, detail: str, code: str = None):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code

class NotFoundError(CustomHTTPException):
    """Raised when a requested resource is not found."""
    def __init__(self, detail: str = "Resource not found.", code: str = "NOT_FOUND"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code=code)

class ConflictError(CustomHTTPException):
    """Raised when a resource already exists or a conflict occurs."""
    def __init__(self, detail: str = "Resource conflict.", code: str = "CONFLICT"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, code=code)

class UnauthorizedError(CustomHTTPException):
    """Raised when authentication fails."""
    def __init__(self, detail: str = "Authentication required.", code: str = "UNAUTHORIZED"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, code=code)

class ForbiddenError(CustomHTTPException):
    """Raised when a user does not have sufficient permissions."""
    def __init__(self, detail: str = "Not enough permissions.", code: str = "FORBIDDEN"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, code=code)

class DatabaseError(CustomHTTPException):
    """Raised for database-related operational errors."""
    def __init__(self, detail: str = "A database error occurred.", code: str = "DB_ERROR"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail, code=code)

class FileOperationError(CustomHTTPException):
    """Raised for errors during file system operations."""
    def __init__(self, detail: str = "A file operation error occurred.", code: str = "FILE_ERROR"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail, code=code)

class ValidationError(CustomHTTPException):
    """Raised for business logic validation errors."""
    def __init__(self, detail: str = "Validation failed.", code: str = "VALIDATION_ERROR"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=code)

# --- Exception Handlers ---
async def http_exception_handler(request, exc: HTTPException):
    """Handles FastAPI's HTTPException."""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=exc.detail).model_dump()
    )

async def custom_http_exception_handler(request, exc: CustomHTTPException):
    """Handles custom HTTP exceptions."""
    logger.error(f"Custom HTTP Exception: {exc.status_code} - {exc.code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(detail=exc.detail, code=exc.code).model_dump()
    )

async def validation_exception_handler(request, exc: RequestValidationError):
    """Handles FastAPI's RequestValidationError (Pydantic validation errors for requests)."""
    error_details = []
    for error in exc.errors():
        field = ".".join(map(str, error["loc"])) if error["loc"] else "unknown"
        error_details.append(f"Field '{field}': {error['msg']}")
    detail_message = "Validation Error: " + "; ".join(error_details)
    logger.warning(f"Request Validation Error: {detail_message} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(detail=detail_message, code="VALIDATION_FAILED").model_dump()
    )

async def pydantic_validation_error_handler(request, exc: PydanticValidationError):
    """Handles Pydantic's ValidationError (e.g., when creating Pydantic models internally)."""
    error_details = []
    for error in exc.errors():
        field = ".".join(map(str, error["loc"])) if error["loc"] else "unknown"
        error_details.append(f"Field '{field}': {error['msg']}")
    detail_message = "Internal Data Validation Error: " + "; ".join(error_details)
    logger.error(f"Internal Pydantic Validation Error: {detail_message} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, # Treat internal validation as server error
        content=ErrorResponse(detail=detail_message, code="INTERNAL_VALIDATION_ERROR").model_dump()
    )

async def generic_exception_handler(request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.critical(f"Unhandled Exception: {type(exc).__name__} - {exc} for path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(detail="An unexpected internal server error occurred.", code="INTERNAL_SERVER_ERROR").model_dump()
    )