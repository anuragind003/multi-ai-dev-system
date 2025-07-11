from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from datetime import datetime

from models import HealthCheckResponse
from database import check_db_connection, get_db_session
from services.vkyc_service import VKYCService
from config import get_settings
from logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse, status_code=status.HTTP_200_OK)
async def health_check(db: Session = Depends(get_db_session)):
    """
    Provides a health check endpoint for the application.
    Checks database connectivity and mocked NFS accessibility.
    """
    db_status = "unhealthy"
    nfs_status = "unhealthy"

    # Check database connection
    if check_db_connection():
        db_status = "healthy"
    else:
        logger.error("Health check: Database connection failed.")

    # Check NFS connection (mocked)
    vkyc_service = VKYCService(db) # Pass db session to VKYCService for NFS check
    if vkyc_service.check_nfs_status():
        nfs_status = "healthy"
    else:
        logger.error("Health check: NFS connection failed.")

    overall_status = "healthy" if db_status == "healthy" and nfs_status == "healthy" else "unhealthy"

    response = HealthCheckResponse(
        status=overall_status,
        database_status=db_status,
        nfs_status=nfs_status,
        version=settings.APP_VERSION
    )

    if overall_status == "unhealthy":
        logger.warning(f"Health check reports unhealthy status: DB={db_status}, NFS={nfs_status}")
        # Optionally, return a 503 if critical services are down
        # raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=response.model_dump_json())
    
    return response