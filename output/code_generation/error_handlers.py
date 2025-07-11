from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from exceptions import APIException, NotFoundException, ConflictException, UnauthorizedException, ForbiddenException, BadRequestException, ServiceUnavailableException
import logging

logger = logging.getLogger("security_testing_api")

def register_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers for the FastAPI application.
    """

    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        logger.error(f"API Exception caught: {exc.status_code} - {exc.detail} for path: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Log the full validation error details
        logger.error(f"Validation error for path: {request.url.path}, errors: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation Error", "errors": exc.errors()},
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        # This handles Pydantic validation errors that might occur outside of request parsing
        logger.error(f"Pydantic validation error for path: {request.url.path}, errors: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Data Validation Error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        # Catch-all for any unhandled exceptions
        logger.exception(f"Unhandled exception caught for path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

    # Specific handlers for common HTTP exceptions (can be customized further)
    @app.exception_handler(status.HTTP_404_NOT_FOUND)
    async def not_found_handler(request: Request, exc: HTTPException):
        logger.warning(f"404 Not Found: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": "The requested resource was not found."},
        )

    @app.exception_handler(status.HTTP_401_UNAUTHORIZED)
    async def unauthorized_handler(request: Request, exc: HTTPException):
        logger.warning(f"401 Unauthorized: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Authentication required or invalid credentials."},
            headers={"WWW-Authenticate": "Bearer"}
        )

    @app.exception_handler(status.HTTP_403_FORBIDDEN)
    async def forbidden_handler(request: Request, exc: HTTPException):
        logger.warning(f"403 Forbidden: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "You do not have permission to access this resource."},
        )