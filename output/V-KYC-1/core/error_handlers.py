from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.exceptions import CustomHTTPException, InternalServerError
import logging

logger = logging.getLogger(__name__)

async def custom_http_exception_handler(request: Request, exc: CustomHTTPException):
    """Handles custom HTTP exceptions."""
    logger.warning(f"Custom HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles Pydantic validation errors."""
    error_details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if str(loc) not in ("body", "query", "path"))
        error_details.append({
            "field": field if field else "request_body",
            "message": error["msg"],
            "type": error["type"]
        })
    logger.warning(f"Validation Error: {error_details} for path: {request.url.path}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation Error", "errors": error_details},
    )

async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles standard FastAPI/Starlette HTTP exceptions."""
    logger.warning(f"Starlette HTTP Exception: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handles all other unhandled exceptions."""
    logger.exception(f"Unhandled Exception: {exc} for path: {request.url.path}", exc_info=True)
    # Return a generic 500 error to avoid leaking sensitive information
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )

def register_exception_handlers(app: FastAPI):
    """Registers all custom exception handlers with the FastAPI application."""
    app.add_exception_handler(CustomHTTPException, custom_http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
    logger.info("Exception handlers registered.")