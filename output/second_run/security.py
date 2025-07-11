python
### FILE: error_handling.py
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

# Configure logging
logger = logging.getLogger(__name__)

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handles validation errors.
    """
    errors = []
    for error in exc.errors():
        errors.append({"field": ".".join(error["loc"]), "message": error["msg"]})
    logger.error(f"Validation error: {errors}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles HTTP exceptions.
    """
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

def configure_error_handlers(app: FastAPI):
    """
    Registers custom exception handlers.
    """
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)