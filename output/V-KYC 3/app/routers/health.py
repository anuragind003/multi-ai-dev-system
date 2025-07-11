from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.schemas import MessageResponse, HTTPError
from app.utils.logger import logger

router = APIRouter()

@router.get(
    "/health",
    response_model=MessageResponse,
    summary="Application Health Check",
    responses={
        status.HTTP_200_OK: {"model": MessageResponse, "description": "Application is healthy"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HTTPError, "description": "Application is unhealthy"}
    }
)
async def health_check(db: Session = Depends(get_db)):
    """
    Performs a health check on the application and its dependencies.
    - Checks database connectivity.
    - Returns a 200 OK if healthy, 503 Service Unavailable otherwise.
    """
    try:
        # Attempt to execute a simple query to check database connectivity
        db.execute(text("SELECT 1"))
        logger.info("Health check: Database connection successful.")
        return MessageResponse(message="Application is healthy and database is connected.")
    except Exception as e:
        logger.error(f"Health check failed: Database connection error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service Unavailable: Database connection failed."
        )

@router.get(
    "/metrics",
    response_model=MessageResponse,
    summary="Application Metrics (Placeholder)",
    responses={
        status.HTTP_200_OK: {"model": MessageResponse, "description": "Metrics endpoint available"},
    }
)
async def get_metrics():
    """
    Placeholder for a metrics endpoint.
    In a real-world scenario, this would expose application metrics
    in a format consumable by monitoring systems like Prometheus.
    """
    logger.info("Metrics endpoint accessed.")
    return MessageResponse(message="Metrics endpoint is available. Implement actual metrics here.")