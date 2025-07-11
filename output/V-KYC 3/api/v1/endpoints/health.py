from fastapi import APIRouter, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Annotated

from dependencies import get_db
from core.logger import logger

router = APIRouter()

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Checks the health and status of the API and its dependencies.",
    responses={
        status.HTTP_200_OK: {
            "description": "API is healthy and connected to the database.",
            "content": {
                "application/json": {
                    "example": {"status": "ok", "database": "connected"}
                }
            }
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "API is unhealthy or database connection failed.",
            "content": {
                "application/json": {
                    "example": {"status": "unhealthy", "database": "disconnected", "error": "DB connection failed"}
                }
            }
        }
    }
)
async def health_check(db: Annotated[Session, Depends(get_db)]):
    """
    Performs a health check on the API and its database connection.
    - Returns 200 OK if the API is running and can connect to the database.
    - Returns 503 Service Unavailable if the database connection fails.
    """
    try:
        # Attempt to execute a simple query to check database connection
        db.execute(text("SELECT 1"))
        logger.info("Health check: Database connection successful.")
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ok", "database": "connected"}
        )
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "database": "disconnected", "error": str(e)}
        )