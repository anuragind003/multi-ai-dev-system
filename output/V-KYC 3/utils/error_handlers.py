from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from utils.exceptions import HTTPUnauthorized, HTTPForbidden, HTTPNotFound, HTTPConflict, HTTPBadRequest
from utils.logger import get_logger
from schemas import HTTPError

logger = get_logger(__name__)

def setup_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers for the FastAPI application.
    """

    @app.exception_handler(HTTPUnauthorized)
    async def unauthorized_exception_handler(request: Request, exc: HTTPUnauthorized):
        logger.warning(f"Unauthorized access attempt: {exc.detail} for path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=HTTPError(detail=exc.detail).model_dump(),
            headers=exc.headers
        )

    @app.exception_handler(HTTPForbidden)
    async def forbidden_exception_handler(request: Request, exc: HTTPForbidden):
        logger.warning(f"Forbidden access attempt: {exc.detail} for path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=HTTPError(detail=exc.detail).model_dump()
        )

    @app.exception_handler(HTTPNotFound)
    async def not_found_exception_handler(request: Request, exc: HTTPNotFound):
        logger.warning(f"Resource not found: {exc.detail} for path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=HTTPError(detail=exc.detail).model_dump()
        )

    @app.exception_handler(HTTPConflict)
    async def conflict_exception_handler(request: Request, exc: HTTPConflict):
        logger.warning(f"Resource conflict: {exc.detail} for path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=HTTPError(detail=exc.detail).model_dump()
        )

    @app.exception_handler(HTTPBadRequest)
    async def bad_request_exception_handler(request: Request, exc: HTTPBadRequest):
        logger.warning(f"Bad request: {exc.detail} for path {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=HTTPError(detail=exc.detail).model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handles FastAPI's automatic request validation errors."""
        error_details = exc.errors()
        # Log detailed validation errors for debugging
        logger.error(f"Request validation error for {request.method} {request.url.path}: {error_details}")
        # Return a more user-friendly message
        formatted_errors = [f"{err['loc'][-1]}: {err['msg']}" for err in error_details]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=HTTPError(detail=f"Validation Error: {'; '.join(formatted_errors)}").model_dump()
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_error_handler(request: Request, exc: ValidationError):
        """Handles Pydantic validation errors not caught by RequestValidationError (e.g., in dependencies)."""
        error_details = exc.errors()
        logger.error(f"Pydantic validation error for {request.method} {request.url.path}: {error_details}")
        formatted_errors = [f"{err['loc'][-1]}: {err['msg']}" for err in error_details]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=HTTPError(detail=f"Data Validation Error: {'; '.join(formatted_errors)}").model_dump()
        )

    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        """Handles generic SQLAlchemy errors."""
        logger.exception(f"Database error occurred for {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=HTTPError(detail="A database error occurred. Please try again later.").model_dump()
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handles any unhandled exceptions."""
        logger.exception(f"Unhandled exception for {request.method} {request.url.path}: {exc}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=HTTPError(detail="An unexpected error occurred. Please try again later.").model_dump()
        )