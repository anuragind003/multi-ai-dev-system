from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from pydantic import ValidationError
from exceptions import (
    APIException,
    NotFoundException,
    ConflictException,
    UnauthorizedException,
    ForbiddenException,
    BadRequestException,
    ServiceUnavailableException,
    InternalServerError
)
from logger import logger
from schemas import ErrorResponse

def register_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers for the FastAPI application.
    This centralizes error handling and ensures consistent error responses.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handles Pydantic validation errors for request bodies/query params."""
        error_detail = exc.errors()
        logger.warning(f"Validation Error: {error_detail} for request {request.url}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                message="Validation Error",
                details=error_detail,
                code="VALIDATION_ERROR"
            ).model_dump()
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
        """Handles Pydantic validation errors that might occur outside of request validation."""
        error_detail = exc.errors()
        logger.warning(f"Pydantic Validation Error: {error_detail} for request {request.url}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(
                message="Data Validation Error",
                details=error_detail,
                code="DATA_VALIDATION_ERROR"
            ).model_dump()
        )

    @app.exception_handler(NotFoundException)
    async def not_found_exception_handler(request: Request, exc: NotFoundException):
        """Handles custom NotFoundException."""
        logger.info(f"Not Found: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="NOT_FOUND"
            ).model_dump()
        )

    @app.exception_handler(ConflictException)
    async def conflict_exception_handler(request: Request, exc: ConflictException):
        """Handles custom ConflictException."""
        logger.warning(f"Conflict: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="CONFLICT"
            ).model_dump()
        )

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        """Handles custom UnauthorizedException."""
        logger.warning(f"Unauthorized: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="UNAUTHORIZED"
            ).model_dump(),
            headers=exc.headers
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        """Handles custom ForbiddenException."""
        logger.warning(f"Forbidden: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="FORBIDDEN"
            ).model_dump()
        )

    @app.exception_handler(BadRequestException)
    async def bad_request_exception_handler(request: Request, exc: BadRequestException):
        """Handles custom BadRequestException."""
        logger.warning(f"Bad Request: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="BAD_REQUEST"
            ).model_dump()
        )

    @app.exception_handler(ServiceUnavailableException)
    async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableException):
        """Handles custom ServiceUnavailableException."""
        logger.error(f"Service Unavailable: {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code="SERVICE_UNAVAILABLE"
            ).model_dump()
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handles generic FastAPI HTTPExceptions."""
        logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail} for request {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                message=exc.detail,
                code=f"HTTP_ERROR_{exc.status_code}"
            ).model_dump(),
            headers=exc.headers
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handles all unhandled exceptions, providing a generic error message."""
        logger.exception(f"Unhandled Exception: {exc} for request {request.url}") # Log full traceback
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                message="An unexpected internal server error occurred.",
                code="INTERNAL_SERVER_ERROR"
            ).model_dump()
        )