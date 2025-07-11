from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from utils.logger import logger
from utils.exceptions import ServiceUnavailableException
from sqlalchemy import text

router = APIRouter(
    tags=["Monitoring"]
)

@router.get(
    "/health",
    summary="Health check endpoint",
    description="Checks the health of the application and its dependencies (e.g., database).",
    responses={
        status.HTTP_200_OK: {"description": "Application is healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Application or a dependency is unhealthy"}
    }
)
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Performs a health check of the application.
    - Checks database connectivity by executing a simple query.
    """
    try:
        # Attempt to execute a simple query to check database connectivity
        await db.execute(text("SELECT 1"))
        logger.info("Health check successful: Database connection OK.")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: Database connection error: {e}", exc_info=True)
        raise ServiceUnavailableException(detail="Database connection failed.")