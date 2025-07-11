from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from core.exceptions import (
    CustomHTTPException,
    UnauthorizedException,
    ForbiddenException,
    NotFoundException,
    ConflictException,
    UnprocessableEntityException,
    ServiceUnavailableException,
    InternalServerErrorException
)
from core.logger import logger

def register_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers for the FastAPI application.
    """

    @app.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
        """Handles all custom HTTP exceptions."""
        logger.warning(f"Custom HTTP Exception: {exc.status_code} - {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
        """Handles UnauthorizedException specifically."""
        logger.warning(f"Unauthorized Access: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_exception_handler(request: Request, exc: ForbiddenException):
        """Handles ForbiddenException specifically."""
        logger.warning(f"Forbidden Access: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(NotFoundException)
    async def not_found_exception_handler(request: Request, exc: NotFoundException):
        """Handles NotFoundException specifically."""
        logger.warning(f"Resource Not Found: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(ConflictException)
    async def conflict_exception_handler(request: Request, exc: ConflictException):
        """Handles ConflictException specifically."""
        logger.warning(f"Conflict: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(UnprocessableEntityException)
    async def unprocessable_entity_exception_handler(request: Request, exc: UnprocessableEntityException):
        """Handles UnprocessableEntityException specifically."""
        logger.warning(f"Unprocessable Entity: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(ServiceUnavailableException)
    async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableException):
        """Handles ServiceUnavailableException specifically."""
        logger.error(f"Service Unavailable: {exc.detail} for {request.url}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError):
        """Handles Pydantic validation errors."""
        logger.warning(f"Pydantic Validation Error for {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "message": "Validation Error"}
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handles SQLAlchemy database errors."""
        logger.exception(f"Database Error for {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "A database error occurred. Please try again later."}
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handles all other unhandled exceptions."""
        logger.exception(f"Unhandled Exception for {request.url}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."}
        )