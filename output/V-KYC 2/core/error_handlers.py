from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from core.exceptions import APIException
from utils.logger import setup_logging

logger = setup_logging()

async def api_exception_handler(request: Request, exc: APIException):
    """
    Handles custom APIException instances.
    Returns a standardized JSON response with the exception's status code and detail.
    """
    logger.error(f"API Exception caught: {exc.status_code} - {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None) # For UnauthorizedException
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles FastAPI's RequestValidationError (Pydantic validation errors).
    Transforms the validation errors into a more readable format.
    """
    error_details = []
    for error in exc.errors():
        field = ".".join(map(str, error["loc"])) if error["loc"] else "body"
        error_details.append(f"Field '{field}': {error['msg']}")
    
    detail_message = "Validation error: " + "; ".join(error_details)
    logger.warning(f"Validation Error: {detail_message} for URL: {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": detail_message},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """
    Handles all other uncaught exceptions.
    Returns a generic 500 Internal Server Error response.
    """
    logger.exception(f"Unhandled exception caught for URL: {request.url}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected internal server error occurred."},
    )