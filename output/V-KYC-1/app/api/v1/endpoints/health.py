from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import ServiceUnavailableException
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health Check"])

@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Basic API Health Check",
    description="Checks if the API is running and responsive.",
    response_model=dict
)
async def health_check():
    """
    Returns a simple status message to indicate the API is operational.
    """
    logger.debug("Health check endpoint accessed.")
    return {"status": "ok", "message": "API is running"}

@router.get(
    "/db",
    status_code=status.HTTP_200_OK,
    summary="Database Connection Health Check",
    description="Checks if the API can connect to the database.",
    response_model=dict,
    responses={
        status.HTTP_200_OK: {"description": "Database connection successful"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Database connection failed"},
    }
)
async def db_health_check(db: AsyncSession = Depends(get_db)):
    """
    Attempts to execute a simple query to check database connectivity.
    """
    try:
        # Execute a simple query to check connection
        await db.execute("SELECT 1")
        logger.info("Database health check successful.")
        return {"status": "ok", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        raise ServiceUnavailableException(detail="Database connection failed")