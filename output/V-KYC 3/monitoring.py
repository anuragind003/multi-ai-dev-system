from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from schemas import HealthCheckResponse
from config import get_settings
from logger import logger
from datetime import datetime, timezone

router = APIRouter()
settings = get_settings()

@router.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Provides the health status of the application and its dependencies.",
    tags=["Monitoring"]
)
async def health_check(db: Session = Depends(get_db)):
    """
    Performs a health check on the application and its database connection.
    Returns a 200 OK response with detailed status if healthy, otherwise an error.
    """
    db_status = "disconnected"
    try:
        # Attempt to execute a simple query to check database connection
        db.execute(text("SELECT 1"))
        db_status = "connected"
        logger.debug("Database health check successful.")
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        db_status = f"failed: {e}"
        # Optionally, return a 503 Service Unavailable if DB is critical
        # raise ServiceUnavailableException(detail="Database connection failed.")

    response = HealthCheckResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database_status=db_status,
        timestamp=datetime.now(timezone.utc),
        version=settings.APP_VERSION
    )
    return response