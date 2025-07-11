from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.dependencies import get_db
from app.schemas import HealthStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["Health Check"]
)

@router.get(
    "/live",
    response_model=HealthStatus,
    summary="Liveness Probe",
    description="Checks if the application is running and able to respond to requests. Does not check external dependencies."
)
async def liveness_probe():
    """
    Basic liveness check. Returns OK if the FastAPI application is running.
    """
    logger.debug("Liveness probe requested.")
    return HealthStatus(status="OK", database="N/A", message="Application is running.")

@router.get(
    "/ready",
    response_model=HealthStatus,
    summary="Readiness Probe",
    description="Checks if the application is ready to serve traffic, including external dependencies like the database."
)
async def readiness_probe(db: Session = Depends(get_db)):
    """
    Readiness check. Returns OK if the FastAPI application is running and
    can connect to the database.
    """
    logger.debug("Readiness probe requested.")
    db_status = "OK"
    db_message = "Database connection successful."
    try:
        # Perform a simple query to check database connectivity
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as e:
        db_status = "Error"
        db_message = f"Database connection failed: {e}"
        logger.error(f"Readiness probe: {db_message}")
        return HealthStatus(status="Degraded", database=db_status, message=db_message)
    except Exception as e:
        db_status = "Error"
        db_message = f"An unexpected error occurred during DB check: {e}"
        logger.error(f"Readiness probe: {db_message}")
        return HealthStatus(status="Degraded", database=db_status, message=db_message)

    logger.info("Readiness probe successful: Application and database are ready.")
    return HealthStatus(status="OK", database=db_status, message=db_message)