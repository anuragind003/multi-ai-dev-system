import os
import httpx
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from database import get_db, engine
from schemas import HealthCheckResponse, ErrorResponse
from config import settings
from utils.logger import logger

router = APIRouter()

@router.get(
    "/health/status",
    response_model=HealthCheckResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Internal Server Error"}
    }
)
async def get_health_status(db: Session = Depends(get_db)):
    """
    Provides a comprehensive health check of the application and its dependencies.
    Checks database connectivity, NFS connectivity, and overall application status.
    """
    overall_status = "healthy"
    details = {}

    # 1. Database Health Check
    db_status = "healthy"
    try:
        # Perform a simple query to check DB connectivity
        db.execute("SELECT 1")
        details["database_message"] = "Database connection successful."
    except SQLAlchemyError as e:
        db_status = "unhealthy"
        overall_status = "unhealthy"
        details["database_message"] = f"Database connection failed: {e}"
        logger.error(f"Health check: Database unhealthy - {e}")
    except Exception as e:
        db_status = "unhealthy"
        overall_status = "unhealthy"
        details["database_message"] = f"Database check failed with unexpected error: {e}"
        logger.error(f"Health check: Database unhealthy - {e}")

    # 2. NFS Health Check (simulated)
    nfs_status = "healthy"
    try:
        if settings.NFS_SIMULATE_FAILURE:
            raise ConnectionError("Simulated NFS connection failure.")

        # Check if the NFS mount path exists and is writable (by attempting to create a temp file)
        test_file_path = os.path.join(settings.NFS_MOUNT_PATH, ".health_check_temp")
        with open(test_file_path, "w") as f:
            f.write("health check")
        os.remove(test_file_path)
        details["nfs_message"] = f"NFS mount path '{settings.NFS_MOUNT_PATH}' accessible and writable."
    except ConnectionError as e:
        nfs_status = "unhealthy"
        overall_status = "unhealthy"
        details["nfs_message"] = f"NFS connection failed: {e}"
        logger.error(f"Health check: NFS unhealthy - {e}")
    except OSError as e:
        nfs_status = "unhealthy"
        overall_status = "unhealthy"
        details["nfs_message"] = f"NFS path '{settings.NFS_MOUNT_PATH}' not accessible or writable: {e}"
        logger.error(f"Health check: NFS unhealthy - {e}")
    except Exception as e:
        nfs_status = "unhealthy"
        overall_status = "unhealthy"
        details["nfs_message"] = f"NFS check failed with unexpected error: {e}"
        logger.error(f"Health check: NFS unhealthy - {e}")

    # 3. External Service Check (e.g., Frontend health endpoint) - Optional, for Frontend-Backend test context
    frontend_status = "healthy"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.FRONTEND_TEST_ENDPOINT, timeout=3)
            response.raise_for_status()
            if response.status_code == 200 and response.json().get("status") == "healthy":
                details["frontend_message"] = f"Frontend endpoint '{settings.FRONTEND_TEST_ENDPOINT}' is reachable and healthy."
            else:
                frontend_status = "unhealthy"
                overall_status = "unhealthy"
                details["frontend_message"] = f"Frontend endpoint '{settings.FRONTEND_TEST_ENDPOINT}' returned non-healthy status or unexpected response: {response.status_code} - {response.text}"
                logger.warning(f"Health check: Frontend unhealthy - {details['frontend_message']}")
    except httpx.RequestError as e:
        frontend_status = "unhealthy"
        overall_status = "unhealthy"
        details["frontend_message"] = f"Could not connect to frontend endpoint '{settings.FRONTEND_TEST_ENDPOINT}': {e}"
        logger.error(f"Health check: Frontend unhealthy - {e}")
    except Exception as e:
        frontend_status = "unhealthy"
        overall_status = "unhealthy"
        details["frontend_message"] = f"Frontend check failed with unexpected error: {e}"
        logger.error(f"Health check: Frontend unhealthy - {e}")


    return HealthCheckResponse(
        status=overall_status,
        database_status=db_status,
        nfs_status=nfs_status,
        details=details
    )