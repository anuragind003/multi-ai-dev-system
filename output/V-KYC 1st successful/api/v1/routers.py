### FILE: health_check.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from schemas import HealthCheckResponse
from config import settings
from utils.logger import logger
import time

router = APIRouter(
    prefix="/health",
    tags=["Health Check"],
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service Unavailable"}}
)

start_time = time.time()

@router.get("/", response_model=HealthCheckResponse, summary="Application Health Check")
def health_check(db: Session = Depends(get_db)):
    """
    Provides a health check endpoint for the application.
    Checks database connectivity and returns application status, version, and uptime.
    """
    db_status = "disconnected"
    try:
        # Attempt a simple query to check database connectivity
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database connection failed during health check: {e}")
        db_status = "disconnected"

    uptime_seconds = time.time() - start_time
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

    overall_status = "healthy" if db_status == "connected" else "unhealthy"

    return HealthCheckResponse(
        status=overall_status,
        database_status=db_status,
        version=settings.APP_VERSION,
        uptime=uptime_str
    )