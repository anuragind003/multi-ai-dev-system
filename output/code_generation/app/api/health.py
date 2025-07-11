from fastapi import APIRouter, Depends, status, HTTPException
from app.core.database import check_db_connection
from app.utils.logger import logger

router = APIRouter()

@router.get(
    "/",
    summary="Health Check",
    description="Checks the health and status of the API and its dependencies.",
    status_code=status.HTTP_200_OK
)
async def health_check():
    """
    Performs a health check on the API.
    Returns 200 OK if the API is running.
    """
    logger.info("Health check endpoint accessed.")
    return {"status": "ok", "message": "VKYC Recordings API is running."}

@router.get(
    "/db",
    summary="Database Health Check",
    description="Checks the connectivity to the database.",
    status_code=status.HTTP_200_OK
)
async def db_health_check():
    """
    Performs a database connectivity check.
    Returns 200 OK if the database is reachable, 503 Service Unavailable otherwise.
    """
    logger.info("Database health check endpoint accessed.")
    if await check_db_connection():
        return {"status": "ok", "message": "Database connection successful."}
    else:
        logger.error("Database connection failed during health check.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection failed."
        )