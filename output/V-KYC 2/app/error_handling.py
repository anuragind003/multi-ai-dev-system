from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Union

from app.schemas import HTTPError
from app.utils.logger import get_logger

logger = get_logger(__name__)

class CustomHTTPException(HTTPException):
    """
    Custom HTTP exception class for consistent error responses.
    Inherits from FastAPI's HTTPException.
    """
    def __init__(self, status_code: int, detail: str, headers: dict = None):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        logger.warning(f"CustomHTTPException: Status {status_code}, Detail: {detail}")

async def http_exception_handler(request: Request, exc: Union[HTTPException, CustomHTTPException]):
    """
    Handles FastAPI's HTTPException and our CustomHTTPException.
    Returns a standardized JSON error response.
    """
    logger.error(f"HTTP Exception caught: {exc.status_code} - {exc.detail} for URL: {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content=HTTPError(detail=exc.detail).model_dump(),
        headers=exc.headers
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles FastAPI's RequestValidationError (Pydantic validation errors for request bodies/queries).
    Returns a standardized JSON error response with validation details.
    """
    error_details = []
    for error in exc.errors():
        field = ".".join(map(str, error["loc"])) if error["loc"] else "unknown"
        error_details.append(f"Field '{field}': {error['msg']}")
    
    detail_message = "Validation Error: " + "; ".join(error_details)
    logger.error(f"Validation Error caught: {detail_message} for URL: {request.url}")
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=HTTPError(detail=detail_message).model_dump(),
    )

# You can add more specific handlers here if needed, e.g., for SQLAlchemy errors
# @app.exception_handler(SQLAlchemyError)
# async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
#     logger.exception(f"Database error occurred: {exc}")
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "A database error occurred. Please try again later."},
#     )