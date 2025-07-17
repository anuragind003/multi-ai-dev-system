from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.responses import JSONResponse

from db.database import get_db_session
from utils.logger import get_logger
from config import settings
import os

logger = get_logger(__name__)

router = APIRouter()

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Provides the health status of the API and its dependencies (database, NFS).",
    response_model=dict
)
async def health_check(db: Session = Depends(get_db_session)):
    """
    Performs a health check on the API and its critical dependencies.
    - Checks database connectivity.
    - Checks NFS server accessibility (simulated).
    """
    health_status = {
        "api_status": "UP",
        "database_status": "DOWN",
        "nfs_status": "DOWN",
        "version": settings.API_VERSION,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    
    # Database Health Check
    try:
        # Perform a simple query to check database connectivity
        db.execute(text("SELECT 1"))
        health_status["database_status"] = "UP"
        logger.debug("Database health check successful.")
    except Exception as e:
        health_status["database_status"] = "DOWN"
        logger.error(f"Database health check failed: {e}", exc_info=True)

    # NFS Server Health Check (Simulated)
    try:
        # Check if the NFS base path is accessible
        if os.path.exists(settings.NFS_BASE_PATH):
            health_status["nfs_status"] = "UP"
            logger.debug(f"NFS base path '{settings.NFS_BASE_PATH}' is accessible.")
        else:
            health_status["nfs_status"] = "DOWN"
            logger.error(f"NFS base path '{settings.NFS_BASE_PATH}' is not accessible.")
    except Exception as e:
        health_status["nfs_status"] = "DOWN"
        logger.error(f"NFS health check failed: {e}", exc_info=True)

    # Determine overall status code
    if health_status["database_status"] == "DOWN" or health_status["nfs_status"] == "DOWN":
        response_status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        health_status["api_status"] = "DEGRADED"
        logger.warning("Health check indicates degraded service.")
    else:
        response_status_code = status.HTTP_200_OK
        logger.info("Health check successful. All services UP.")

    return JSONResponse(content=health_status, status_code=response_status_code)

from datetime import datetime # Import datetime here to avoid circular dependency with main.py