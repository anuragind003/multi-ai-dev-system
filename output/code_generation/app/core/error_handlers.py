import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException, RequestValidationError
from pydantic import ValidationError

from app.core.exceptions import APIException
from app.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Handles FastAPI's HTTPException.
    """
    logger.warning(f"HTTPException caught: {exc.status_code} - {exc.detail} for path: {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.status_code,
            message=exc.detail,
            details=None
        ).model_dump(exclude_none=True),
        headers=exc.headers,
    )

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handles custom APIException.
    """
    logger.error(f"APIException caught: {exc.status_code} - {exc.detail} for path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.status_code,
            message=exc.detail,
            details=None
        ).model_dump(exclude_none=True),
        headers=exc.headers,
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handles FastAPI's RequestValidationError (Pydantic validation errors for request bodies/queries).
    """
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if str(loc) not in ("body", "query", "path"))
        errors.append(f"Field '{field}': {error['msg']}")
    
    detail_message = "Validation Error"
    if errors:
        detail_message += ": " + "; ".join(errors)

    logger.warning(f"RequestValidationError caught for path: {request.url.path}. Details: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=detail_message,
            details=errors
        ).model_dump(exclude_none=True),
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handles any unhandled exceptions.
    """
    logger.critical(f"Unhandled exception caught for path: {request.url.path}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected internal server error occurred.",
            details=None
        ).model_dump(exclude_none=True),
    )