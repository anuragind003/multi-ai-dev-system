from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException

from app.exceptions import (
    UserAlreadyExistsException, InvalidCredentialsException, ForbiddenException,
    NotFoundException, UnauthorizedException
)
from app.utils.logger import logger

async def user_already_exists_exception_handler(request: Request, exc: UserAlreadyExistsException):
    """Handles UserAlreadyExistsException."""
    logger.warning(f"UserAlreadyExistsException: {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def invalid_credentials_exception_handler(request: Request, exc: InvalidCredentialsException):
    """Handles InvalidCredentialsException."""
    logger.warning(f"InvalidCredentialsException: {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers # Include WWW-Authenticate header if present
    )

async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handles UnauthorizedException."""
    logger.warning(f"UnauthorizedException: {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers # Include WWW-Authenticate header
    )

async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
    """Handles ForbiddenException."""
    logger.warning(f"ForbiddenException: {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def not_found_exception_handler(request: Request, exc: NotFoundException):
    """Handles NotFoundException."""
    logger.warning(f"NotFoundException: {exc.detail} for path {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def generic_http_exception_handler(request: Request, exc: FastAPIHTTPException):
    """Handles generic FastAPI HTTPException."""
    logger.error(f"HTTPException: {exc.status_code} - {exc.detail} for path {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

# You can add a catch-all for unhandled exceptions if desired, but be careful not to expose sensitive info.
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Handles any unhandled exceptions."""
    logger.critical(f"Unhandled exception: {exc} for path {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )