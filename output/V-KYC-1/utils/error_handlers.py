from fastapi import Request, status, HTTPException
from fastapi.responses import JSONResponse
from utils.exceptions import (
    NotFoundException,
    ConflictException,
    UnauthorizedException,
    ForbiddenException,
    ValidationException,
    BaseAppException,
    DatabaseException,
    ServiceUnavailableException
)
from utils.logger import get_logger

logger = get_logger(__name__)

async def not_found_exception_handler(request: Request, exc: NotFoundException):
    """Handles NotFoundException and returns a 404 JSON response."""
    logger.warning(f"NotFoundException: {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.detail},
    )

async def conflict_exception_handler(request: Request, exc: ConflictException):
    """Handles ConflictException and returns a 409 JSON response."""
    logger.warning(f"ConflictException: {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": exc.detail},
    )

async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handles UnauthorizedException and returns a 401 JSON response."""
    logger.warning(f"UnauthorizedException: {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    """Handles ForbiddenException and returns a 403 JSON response."""
    logger.warning(f"ForbiddenException: {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.detail},
    )

async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handles ValidationException and returns a 422 JSON response."""
    logger.warning(f"ValidationException: {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.detail},
    )

async def database_exception_handler(request: Request, exc: DatabaseException):
    """Handles DatabaseException and returns a 500 JSON response."""
    logger.error(f"DatabaseException: {exc.detail} for URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal database error occurred."},
    )

async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableException):
    """Handles ServiceUnavailableException and returns a 503 JSON response."""
    logger.error(f"ServiceUnavailableException: {exc.detail} for URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": exc.detail},
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles generic HTTPException and returns a JSON response."""
    logger.error(f"HTTPException ({exc.status_code}): {exc.detail} for URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles any unhandled exception and returns a 500 JSON response."""
    logger.critical(f"Unhandled exception: {exc} for URL: {request.url}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )