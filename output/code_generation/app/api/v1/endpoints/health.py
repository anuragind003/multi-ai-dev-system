import logging
from fastapi import APIRouter, status, HTTPException
from sqlalchemy.orm import Session
from database import get_db, engine
from app.core.exceptions import CustomHTTPException
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Provides a simple health check for the API and its dependencies.",
    responses={
        status.HTTP_200_OK: {"description": "API is healthy."},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "API or a dependency is unhealthy."}
    }
)
async def health_check(db: Session = Depends(get_db)):
    """
    Performs a health check on the API and its critical dependencies.
    Checks:
    1. Database connectivity.
    2. (Placeholder) Simulated NFS connectivity check.
    """
    health_status = {"api": "healthy", "database": "healthy", "nfs_connection": "healthy"}
    errors = []

    # 1. Database Connectivity Check
    try:
        # Attempt to execute a simple query to check DB connection
        db.execute(text("SELECT 1"))
        logger.debug("Database connection successful.")
    except Exception as e:
        health_status["database"] = "unhealthy"
        errors.append(f"Database connection failed: {e}")
        logger.error(f"Health check: Database connection failed: {e}", exc_info=True)

    # 2. Simulated NFS Connection Check
    # In a real scenario, this would involve trying to list a directory
    # or check permissions on the NFS mount point.
    # For this example, we'll just check if the configured path exists.
    try:
        import os
        if not os.path.exists(settings.NFS_BASE_PATH):
            health_status["nfs_connection"] = "unhealthy"
            errors.append(f"NFS base path '{settings.NFS_BASE_PATH}' does not exist or is not accessible.")
            logger.warning(f"Health check: NFS base path '{settings.NFS_BASE_PATH}' not found.")
        else:
            # Attempt to list a directory to confirm access
            # This might be slow or fail if NFS is truly down
            # Consider a timeout for this operation
            test_dir = os.path.join(settings.NFS_BASE_PATH, "health_check_test")
            if not os.path.exists(test_dir):
                os.makedirs(test_dir, exist_ok=True) # Create if not exists
            # Try to write a dummy file
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("health check")
            os.remove(test_file) # Clean up
            os.rmdir(test_dir) # Clean up directory
            logger.debug("NFS path accessible and writable.")
    except Exception as e:
        health_status["nfs_connection"] = "unhealthy"
        errors.append(f"NFS access check failed: {e}")
        logger.error(f"Health check: NFS access check failed: {e}", exc_info=True)


    if "unhealthy" in health_status.values():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "unhealthy", "components": health_status, "errors": errors}
        )
    
    return {"status": "healthy", "components": health_status}

# Import text for db.execute
from sqlalchemy import text