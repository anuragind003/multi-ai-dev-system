from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from utils.exceptions import CustomHTTPException
from utils.logger import logger

def register_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers for the FastAPI application.
    """

    @app.exception_handler(CustomHTTPException)
    async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
        """Handles custom HTTP exceptions."""
        logger.warning(f"Custom HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=exc.headers
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handles Pydantic validation errors."""
        logger.error(f"Validation Error: {exc.errors()} for path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Validation Error", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        """Handles all other unhandled exceptions."""
        logger.exception(f"Unhandled Exception: {exc} for path: {request.url.path}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )